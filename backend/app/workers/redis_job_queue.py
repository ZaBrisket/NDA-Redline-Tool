"""
Redis-based Job Queue for Distributed Document Processing
Implements persistent job queue with retry logic, priority handling, and horizontal scaling
"""

import os
import json
import time
import uuid
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import redis.asyncio as redis
import pickle
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 0
    STANDARD = 1
    EXPEDITED = 2
    CRITICAL = 3


class JobStatus(Enum):
    """Job processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class RedisJobQueue:
    """
    Distributed job queue using Redis Streams and data structures.
    Supports horizontal scaling, job retry, and priority processing.
    """

    def __init__(
        self,
        redis_url: str = None,
        stream_key: str = "nda_job_stream",
        consumer_group: str = "nda_processors",
        consumer_name: str = None,
        max_retries: int = 3,
        retry_delay_base: int = 60,
        job_ttl: int = 86400  # 24 hours
    ):
        """
        Initialize Redis job queue.

        Args:
            redis_url: Redis connection URL
            stream_key: Redis stream key for job queue
            consumer_group: Consumer group name for distributed processing
            consumer_name: Unique consumer name (auto-generated if None)
            max_retries: Maximum retry attempts for failed jobs
            retry_delay_base: Base delay in seconds for exponential backoff
            job_ttl: Time-to-live for job data in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.stream_key = stream_key
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name or f"consumer_{uuid.uuid4().hex[:8]}"

        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.job_ttl = job_ttl

        self.redis_client: Optional[redis.Redis] = None
        self._lock_prefix = "lock:"
        self._job_prefix = "job:"
        self._priority_set = "job_priority"
        self._processing_set = f"processing:{self.consumer_name}"

        # Performance metrics
        self.stats = {
            "jobs_submitted": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "jobs_retried": 0,
            "total_processing_time": 0.0
        }

    async def connect(self):
        """Establish Redis connection and initialize data structures."""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                decode_responses=False  # Handle binary data
            )
            await self.redis_client.ping()

            # Create consumer group if it doesn't exist
            try:
                await self.redis_client.xgroup_create(
                    self.stream_key,
                    self.consumer_group,
                    id="0",
                    mkstream=True
                )
                logger.info(f"Created consumer group: {self.consumer_group}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

            logger.info(f"Redis job queue connected: {self.consumer_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Clean up Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis job queue disconnected")

    async def submit_job(
        self,
        job_data: Dict[str, Any],
        priority: JobPriority = JobPriority.STANDARD,
        job_id: Optional[str] = None
    ) -> str:
        """
        Submit a new job to the queue.

        Args:
            job_data: Job payload data
            priority: Job priority level
            job_id: Optional job ID (auto-generated if None)

        Returns:
            Job ID
        """
        if not self.redis_client:
            await self.connect()

        job_id = job_id or str(uuid.uuid4())

        # Prepare job metadata
        job_info = {
            "job_id": job_id,
            "status": JobStatus.QUEUED.value,
            "priority": priority.value,
            "data": json.dumps(job_data),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "retry_count": 0,
            "consumer": None,
            "error": None,
            "result": None
        }

        # Add to Redis stream
        stream_id = await self.redis_client.xadd(
            self.stream_key,
            {"job_id": job_id, "priority": str(priority.value)}
        )

        # Store job data in hash
        job_key = f"{self._job_prefix}{job_id}"
        await self.redis_client.hset(
            job_key,
            mapping={k: str(v) if v is not None else "" for k, v in job_info.items()}
        )
        await self.redis_client.expire(job_key, self.job_ttl)

        # Add to priority sorted set
        await self.redis_client.zadd(
            self._priority_set,
            {job_id: -priority.value}  # Negative for descending sort
        )

        self.stats["jobs_submitted"] += 1

        logger.info(f"Job submitted: {job_id} with priority {priority.name}")

        return job_id

    async def consume_jobs(
        self,
        process_callback,
        batch_size: int = 1,
        block_timeout: int = 5000
    ):
        """
        Consume and process jobs from the queue.

        Args:
            process_callback: Async function to process job data
            batch_size: Number of jobs to read at once
            block_timeout: Timeout for blocking read in milliseconds
        """
        if not self.redis_client:
            await self.connect()

        logger.info(f"Starting job consumer: {self.consumer_name}")

        while True:
            try:
                # Read from stream with consumer group
                messages = await self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_key: ">"},
                    count=batch_size,
                    block=block_timeout
                )

                if not messages:
                    continue

                for stream, stream_messages in messages:
                    for message_id, data in stream_messages:
                        job_id = data.get(b"job_id", b"").decode()

                        if job_id:
                            # Process job with distributed lock
                            await self._process_job_with_lock(
                                job_id,
                                message_id,
                                process_callback
                            )

            except Exception as e:
                logger.error(f"Consumer error: {e}")
                await asyncio.sleep(5)

    async def _process_job_with_lock(
        self,
        job_id: str,
        message_id: bytes,
        process_callback
    ):
        """
        Process a job with distributed lock.

        Args:
            job_id: Job identifier
            message_id: Stream message ID
            process_callback: Processing function
        """
        lock_key = f"{self._lock_prefix}{job_id}"
        lock_acquired = False

        try:
            # Try to acquire distributed lock
            lock_acquired = await self.redis_client.set(
                lock_key,
                self.consumer_name,
                nx=True,
                ex=300  # 5-minute lock timeout
            )

            if not lock_acquired:
                logger.debug(f"Job {job_id} already being processed")
                return

            # Get job data
            job_key = f"{self._job_prefix}{job_id}"
            job_info = await self.redis_client.hgetall(job_key)

            if not job_info:
                logger.warning(f"Job {job_id} not found")
                await self._acknowledge_message(message_id)
                return

            # Update job status
            await self._update_job_status(
                job_id,
                JobStatus.PROCESSING,
                {"consumer": self.consumer_name}
            )

            # Parse job data
            job_data = json.loads(job_info[b"data"].decode())

            # Process job with retry logic
            start_time = time.time()

            try:
                result = await process_callback(job_id, job_data)

                # Job completed successfully
                processing_time = time.time() - start_time

                await self._update_job_status(
                    job_id,
                    JobStatus.COMPLETED,
                    {
                        "result": json.dumps(result) if result else None,
                        "processing_time": str(processing_time)
                    }
                )

                self.stats["jobs_completed"] += 1
                self.stats["total_processing_time"] += processing_time

                logger.info(f"Job {job_id} completed in {processing_time:.2f}s")

            except Exception as e:
                # Job failed - handle retry
                await self._handle_job_failure(job_id, message_id, str(e))

            # Acknowledge message
            await self._acknowledge_message(message_id)

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")

        finally:
            # Release lock
            if lock_acquired:
                await self.redis_client.delete(lock_key)

    async def _handle_job_failure(
        self,
        job_id: str,
        message_id: bytes,
        error: str
    ):
        """
        Handle job failure with retry logic.

        Args:
            job_id: Job identifier
            message_id: Stream message ID
            error: Error message
        """
        job_key = f"{self._job_prefix}{job_id}"
        job_info = await self.redis_client.hgetall(job_key)

        retry_count = int(job_info.get(b"retry_count", b"0"))

        if retry_count < self.max_retries:
            # Schedule retry with exponential backoff
            retry_delay = self.retry_delay_base * (2 ** retry_count)
            retry_count += 1

            await self._update_job_status(
                job_id,
                JobStatus.RETRYING,
                {
                    "error": error,
                    "retry_count": str(retry_count),
                    "next_retry": (
                        datetime.now() + timedelta(seconds=retry_delay)
                    ).isoformat()
                }
            )

            # Re-add to stream after delay
            asyncio.create_task(self._retry_job(job_id, retry_delay))

            self.stats["jobs_retried"] += 1
            logger.warning(
                f"Job {job_id} failed, retrying {retry_count}/{self.max_retries} "
                f"in {retry_delay}s: {error}"
            )

        else:
            # Max retries exceeded
            await self._update_job_status(
                job_id,
                JobStatus.FAILED,
                {"error": error, "final": "true"}
            )

            self.stats["jobs_failed"] += 1
            logger.error(f"Job {job_id} failed permanently: {error}")

    async def _retry_job(self, job_id: str, delay: int):
        """
        Re-add job to stream after delay.

        Args:
            job_id: Job to retry
            delay: Delay in seconds
        """
        await asyncio.sleep(delay)

        # Get job priority
        job_key = f"{self._job_prefix}{job_id}"
        job_info = await self.redis_client.hgetall(job_key)

        if job_info:
            priority = job_info.get(b"priority", b"1").decode()

            # Re-add to stream
            await self.redis_client.xadd(
                self.stream_key,
                {"job_id": job_id, "priority": priority, "retry": "true"}
            )

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        updates: Dict[str, Any] = None
    ):
        """
        Update job status and metadata.

        Args:
            job_id: Job identifier
            status: New status
            updates: Additional field updates
        """
        job_key = f"{self._job_prefix}{job_id}"

        update_data = {
            "status": status.value,
            "updated_at": datetime.now().isoformat()
        }

        if updates:
            update_data.update(updates)

        await self.redis_client.hset(
            job_key,
            mapping={k: str(v) if v is not None else "" for k, v in update_data.items()}
        )

        # Update TTL
        await self.redis_client.expire(job_key, self.job_ttl)

    async def _acknowledge_message(self, message_id: bytes):
        """Acknowledge message in stream."""
        await self.redis_client.xack(
            self.stream_key,
            self.consumer_group,
            message_id
        )

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current job status and metadata.

        Args:
            job_id: Job identifier

        Returns:
            Job information dictionary
        """
        if not self.redis_client:
            await self.connect()

        job_key = f"{self._job_prefix}{job_id}"
        job_info = await self.redis_client.hgetall(job_key)

        if not job_info:
            return None

        # Decode binary data
        result = {}
        for key, value in job_info.items():
            key_str = key.decode()
            value_str = value.decode()

            # Parse JSON fields
            if key_str in ["data", "result"] and value_str:
                try:
                    result[key_str] = json.loads(value_str)
                except:
                    result[key_str] = value_str
            else:
                result[key_str] = value_str

        return result

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: Job to cancel

        Returns:
            True if cancelled, False if not found or already processing
        """
        if not self.redis_client:
            await self.connect()

        job_status = await self.get_job_status(job_id)

        if not job_status:
            return False

        if job_status["status"] in [JobStatus.QUEUED.value, JobStatus.RETRYING.value]:
            await self._update_job_status(
                job_id,
                JobStatus.CANCELLED,
                {"cancelled_by": self.consumer_name}
            )

            # Remove from priority set
            await self.redis_client.zrem(self._priority_set, job_id)

            return True

        return False

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get queue statistics and metrics.

        Returns:
            Statistics dictionary
        """
        if not self.redis_client:
            await self.connect()

        # Get stream length
        stream_info = await self.redis_client.xinfo_stream(self.stream_key)
        pending_count = stream_info.get("length", 0)

        # Get priority queue size
        priority_count = await self.redis_client.zcard(self._priority_set)

        # Combine with instance stats
        return {
            "pending_jobs": pending_count,
            "priority_queue_size": priority_count,
            "consumer_name": self.consumer_name,
            **self.stats
        }

    async def cleanup_old_jobs(self, days: int = 7):
        """
        Clean up old completed/failed jobs.

        Args:
            days: Age threshold in days
        """
        if not self.redis_client:
            await self.connect()

        cutoff = datetime.now() - timedelta(days=days)
        cleaned = 0

        # Scan for old job keys
        async for key in self.redis_client.scan_iter(f"{self._job_prefix}*"):
            job_info = await self.redis_client.hgetall(key)

            if job_info:
                status = job_info.get(b"status", b"").decode()
                updated_at = job_info.get(b"updated_at", b"").decode()

                if status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
                    if updated_at:
                        try:
                            job_date = datetime.fromisoformat(updated_at)
                            if job_date < cutoff:
                                await self.redis_client.delete(key)
                                cleaned += 1
                        except:
                            pass

        logger.info(f"Cleaned up {cleaned} old jobs")

        return cleaned