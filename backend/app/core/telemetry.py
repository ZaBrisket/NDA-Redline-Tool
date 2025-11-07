"""
Performance Monitoring and Telemetry Module
Tracks LLM costs, processing times, and exports metrics for Prometheus
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
import asyncio
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    generate_latest,
    CONTENT_TYPE_LATEST
)
from fastapi import Response
import redis.asyncio as redis

logger = logging.getLogger(__name__)


# Prometheus metrics
job_counter = Counter(
    'nda_jobs_total',
    'Total number of NDA processing jobs',
    ['status', 'priority']
)

processing_time = Histogram(
    'nda_processing_duration_seconds',
    'Time spent processing NDA documents',
    ['stage'],
    buckets=(0.5, 1, 2, 5, 10, 30, 60, 120, 300)
)

llm_cost_counter = Counter(
    'nda_llm_cost_dollars',
    'Total LLM API costs in dollars',
    ['model', 'api_key_id']
)

cache_hit_rate = Gauge(
    'nda_cache_hit_rate',
    'Semantic cache hit rate'
)

active_jobs = Gauge(
    'nda_active_jobs',
    'Number of currently processing jobs'
)

queue_size = Gauge(
    'nda_queue_size',
    'Number of jobs in queue',
    ['priority']
)

redlines_per_document = Summary(
    'nda_redlines_per_document',
    'Number of redlines per document',
    ['source']
)

error_rate = Counter(
    'nda_errors_total',
    'Total number of processing errors',
    ['stage', 'error_type']
)


class PerformanceMonitor:
    """
    Comprehensive performance monitoring for NDA processing.
    Tracks costs, times, and system metrics.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        metrics_ttl: int = 86400,  # 24 hours
        cost_per_token: Dict[str, float] = None
    ):
        """
        Initialize performance monitor.

        Args:
            redis_url: Redis URL for distributed metrics
            metrics_ttl: TTL for metrics in seconds
            cost_per_token: Cost mapping per token for different models
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.metrics_ttl = metrics_ttl

        # Cost calculation parameters (August 2025 pricing)
        self.cost_per_token = cost_per_token or {
            'claude-3-opus-20240229': 0.00000125,  # $1.25 per 1M input tokens
            'claude-3-opus-20240229': 0.00001,  # $10 per 1M output tokens
            'claude-sonnet-4': 0.000003,  # $3 per 1M tokens
            'claude-sonnet-4-output': 0.000015  # $15 per 1M output tokens
        }

        # Redis client for distributed metrics
        self.redis_client: Optional[redis.Redis] = None
        if self.redis_url:
            asyncio.create_task(self._init_redis())

        # Local metrics storage
        self.metrics = {
            'jobs_processed': 0,
            'total_processing_time': 0.0,
            'total_llm_cost': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': defaultdict(int),
            'api_key_usage': defaultdict(lambda: defaultdict(float))
        }

        # Time series data for trends (last 24 hours)
        self.time_series = {
            'processing_times': deque(maxlen=1000),
            'costs': deque(maxlen=1000),
            'error_rates': deque(maxlen=100)
        }

        # Stage timing
        self.stage_timers = {}

    async def _init_redis(self):
        """Initialize Redis connection for distributed metrics."""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Telemetry Redis connection established")
        except Exception as e:
            logger.warning(f"Telemetry Redis connection failed: {e}")
            self.redis_client = None

    def track_job_start(self, job_id: str, priority: str = "standard"):
        """Track job start."""
        self.stage_timers[job_id] = {
            'start_time': time.time(),
            'stages': {}
        }
        active_jobs.inc()
        job_counter.labels(status='started', priority=priority).inc()

    def track_job_complete(
        self,
        job_id: str,
        redlines_count: int,
        priority: str = "standard"
    ):
        """Track job completion."""
        if job_id in self.stage_timers:
            duration = time.time() - self.stage_timers[job_id]['start_time']
            processing_time.labels(stage='total').observe(duration)
            self.metrics['total_processing_time'] += duration
            self.metrics['jobs_processed'] += 1

            # Record time series
            self.time_series['processing_times'].append({
                'timestamp': datetime.now().isoformat(),
                'duration': duration,
                'job_id': job_id
            })

            del self.stage_timers[job_id]

        active_jobs.dec()
        job_counter.labels(status='completed', priority=priority).inc()
        redlines_per_document.labels(source='all').observe(redlines_count)

    def track_job_error(
        self,
        job_id: str,
        error: str,
        stage: str,
        priority: str = "standard"
    ):
        """Track job failure."""
        if job_id in self.stage_timers:
            del self.stage_timers[job_id]

        active_jobs.dec()
        job_counter.labels(status='failed', priority=priority).inc()
        error_rate.labels(stage=stage, error_type=type(error).__name__).inc()

        self.metrics['errors'][f"{stage}_{type(error).__name__}"] += 1

        # Record error in time series
        self.time_series['error_rates'].append({
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'error': str(error)
        })

    def track_stage_start(self, job_id: str, stage: str):
        """Track processing stage start."""
        if job_id in self.stage_timers:
            self.stage_timers[job_id]['stages'][stage] = time.time()

    def track_stage_complete(self, job_id: str, stage: str):
        """Track processing stage completion."""
        if job_id in self.stage_timers and stage in self.stage_timers[job_id]['stages']:
            duration = time.time() - self.stage_timers[job_id]['stages'][stage]
            processing_time.labels(stage=stage).observe(duration)
            del self.stage_timers[job_id]['stages'][stage]

    def track_llm_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        api_key_id: Optional[str] = None
    ):
        """
        Track LLM API costs.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            api_key_id: Optional API key identifier for attribution
        """
        # Calculate cost
        input_cost = input_tokens * self.cost_per_token.get(model, 0.000005)
        output_cost = output_tokens * self.cost_per_token.get(f"{model}-output", 0.000015)
        total_cost = input_cost + output_cost

        # Update metrics
        self.metrics['total_llm_cost'] += total_cost
        llm_cost_counter.labels(model=model, api_key_id=api_key_id or 'default').inc(total_cost)

        # Track per API key
        if api_key_id:
            self.metrics['api_key_usage'][api_key_id]['cost'] += total_cost
            self.metrics['api_key_usage'][api_key_id]['requests'] += 1
            self.metrics['api_key_usage'][api_key_id]['tokens'] += input_tokens + output_tokens

        # Record in time series
        self.time_series['costs'].append({
            'timestamp': datetime.now().isoformat(),
            'model': model,
            'cost': total_cost,
            'api_key': api_key_id
        })

        logger.debug(f"LLM cost tracked: ${total_cost:.4f} for {model}")

    def track_cache_hit(self):
        """Track cache hit."""
        self.metrics['cache_hits'] += 1
        self._update_cache_hit_rate()

    def track_cache_miss(self):
        """Track cache miss."""
        self.metrics['cache_misses'] += 1
        self._update_cache_hit_rate()

    def _update_cache_hit_rate(self):
        """Update cache hit rate gauge."""
        total = self.metrics['cache_hits'] + self.metrics['cache_misses']
        if total > 0:
            hit_rate = self.metrics['cache_hits'] / total
            cache_hit_rate.set(hit_rate)

    def update_queue_size(self, priority: str, size: int):
        """Update queue size metric."""
        queue_size.labels(priority=priority).set(size)

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary with all metrics
        """
        # Calculate averages
        avg_processing_time = (
            self.metrics['total_processing_time'] / self.metrics['jobs_processed']
            if self.metrics['jobs_processed'] > 0 else 0
        )

        cache_hit_rate_val = (
            self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses'])
            if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
        )

        # Get recent trends
        recent_times = [
            t['duration'] for t in self.time_series['processing_times']
            if datetime.fromisoformat(t['timestamp']) > datetime.now() - timedelta(hours=1)
        ]

        recent_costs = [
            c['cost'] for c in self.time_series['costs']
            if datetime.fromisoformat(c['timestamp']) > datetime.now() - timedelta(hours=1)
        ]

        summary = {
            'total_jobs': self.metrics['jobs_processed'],
            'avg_processing_time': f"{avg_processing_time:.2f}s",
            'total_llm_cost': f"${self.metrics['total_llm_cost']:.2f}",
            'cache_hit_rate': f"{cache_hit_rate_val:.1%}",
            'total_errors': sum(self.metrics['errors'].values()),
            'error_breakdown': dict(self.metrics['errors']),
            'api_key_usage': dict(self.metrics['api_key_usage']),
            'recent_trends': {
                'avg_time_last_hour': f"{sum(recent_times) / len(recent_times):.2f}s" if recent_times else "N/A",
                'total_cost_last_hour': f"${sum(recent_costs):.2f}",
                'jobs_last_hour': len(recent_times)
            }
        }

        # Store in Redis if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    "telemetry:summary",
                    self.metrics_ttl,
                    json.dumps(summary)
                )
            except Exception as e:
                logger.debug(f"Failed to store metrics in Redis: {e}")

        return summary

    async def get_cost_attribution(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get cost attribution by API key and time period.

        Args:
            start_date: Start of period (default: 24h ago)
            end_date: End of period (default: now)

        Returns:
            Cost attribution report
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=1)
        if not end_date:
            end_date = datetime.now()

        # Filter costs by time period
        period_costs = [
            c for c in self.time_series['costs']
            if start_date <= datetime.fromisoformat(c['timestamp']) <= end_date
        ]

        # Aggregate by API key
        attribution = defaultdict(lambda: {
            'total_cost': 0.0,
            'request_count': 0,
            'models_used': set()
        })

        for cost_entry in period_costs:
            api_key = cost_entry.get('api_key', 'default')
            attribution[api_key]['total_cost'] += cost_entry['cost']
            attribution[api_key]['request_count'] += 1
            attribution[api_key]['models_used'].add(cost_entry['model'])

        # Convert sets to lists for JSON serialization
        for key in attribution:
            attribution[key]['models_used'] = list(attribution[key]['models_used'])

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_cost': sum(a['total_cost'] for a in attribution.values()),
            'attribution': dict(attribution)
        }

    def export_prometheus_metrics(self) -> bytes:
        """
        Export metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest()

    async def cleanup_old_metrics(self, days: int = 7):
        """
        Clean up old metrics data.

        Args:
            days: Age threshold in days
        """
        cutoff = datetime.now() - timedelta(days=days)

        # Clean time series data
        for series_name in ['processing_times', 'costs', 'error_rates']:
            series = self.time_series[series_name]
            self.time_series[series_name] = deque(
                [
                    entry for entry in series
                    if datetime.fromisoformat(entry['timestamp']) > cutoff
                ],
                maxlen=series.maxlen
            )

        logger.info(f"Cleaned up metrics older than {days} days")


# Performance monitoring decorator
def monitor_performance(stage: str):
    """
    Decorator to monitor function performance.

    Args:
        stage: Processing stage name
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                processing_time.labels(stage=stage).observe(time.time() - start_time)
                return result
            except Exception as e:
                error_rate.labels(stage=stage, error_type=type(e).__name__).inc()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                processing_time.labels(stage=stage).observe(time.time() - start_time)
                return result
            except Exception as e:
                error_rate.labels(stage=stage, error_type=type(e).__name__).inc()
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Global monitor instance
_monitor_instance: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get or create singleton performance monitor."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()
    return _monitor_instance


# FastAPI endpoint for metrics
async def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Returns:
        Metrics in Prometheus format
    """
    monitor = get_performance_monitor()
    metrics_data = monitor.export_prometheus_metrics()

    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST
    )