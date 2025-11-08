"""
Worker state management for Gunicorn multi-worker deployments
Ensures efficient resource initialization and prevents redundant orchestrator creation
"""

import os
import logging
import asyncio
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WorkerState:
    """
    Manages per-worker application state for Gunicorn deployments

    Each Gunicorn worker process gets its own instance of this state.
    This prevents redundant initialization and resource contention.
    """

    worker_id: Optional[int] = None
    orchestrator: Optional[any] = None
    initialized: bool = False
    initialization_time: Optional[datetime] = None
    request_count: int = 0
    error_count: int = 0

    def __post_init__(self):
        """Initialize worker ID from environment"""
        if self.worker_id is None:
            self.worker_id = os.getpid()

    async def initialize(self, api_key: Optional[str] = None, retry_count: int = 3) -> bool:
        """
        Initialize worker-specific resources with retry logic

        Args:
            api_key: Anthropic API key (optional, will use env var if not provided)
            retry_count: Number of retry attempts on transient failures

        Returns:
            True if initialization succeeded, False otherwise
        """
        if self.initialized:
            logger.info(
                f"Worker {self.worker_id} already initialized, skipping",
                extra={"worker_pid": self.worker_id}
            )
            return True

        # Get API key from parameter or environment
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            logger.error(
                f"Worker {self.worker_id}: ANTHROPIC_API_KEY not configured",
                extra={"worker_pid": self.worker_id}
            )
            return False

        # Check for placeholder keys
        if api_key.startswith("sk-ant-your-") or api_key.startswith("sk-ant-api03-YOUR") or api_key == "your-api-key-here":
            logger.error(
                f"Worker {self.worker_id}: ANTHROPIC_API_KEY contains placeholder value",
                extra={"worker_pid": self.worker_id}
            )
            return False

        # Retry loop for transient failures
        for attempt in range(retry_count):
            try:
                logger.info(
                    f"Initializing worker {self.worker_id} (attempt {attempt + 1}/{retry_count})",
                    extra={"worker_pid": self.worker_id, "attempt": attempt + 1}
                )

                # Import here to avoid circular dependencies
                from .llm_orchestrator import AllClaudeLLMOrchestrator

                # Initialize orchestrator
                self.orchestrator = AllClaudeLLMOrchestrator(api_key=api_key)
                self.initialized = True
                self.initialization_time = datetime.utcnow()

                logger.info(
                    f"Worker {self.worker_id} initialized successfully",
                    extra={
                        "worker_pid": self.worker_id,
                        "initialization_time": self.initialization_time.isoformat(),
                        "attempts": attempt + 1
                    }
                )

                return True

            except ValueError as e:
                # API key format errors are not retryable
                logger.error(
                    f"Worker {self.worker_id}: Invalid API key format - {e}",
                    extra={"worker_pid": self.worker_id}
                )
                return False

            except Exception as e:
                logger.error(
                    f"Worker {self.worker_id}: Initialization failed (attempt {attempt + 1}/{retry_count}) - {e}",
                    extra={"worker_pid": self.worker_id, "attempt": attempt + 1},
                    exc_info=True
                )

                # Exponential backoff before retry
                if attempt < retry_count - 1:
                    backoff_seconds = 2 ** attempt
                    logger.info(
                        f"Worker {self.worker_id}: Retrying in {backoff_seconds}s",
                        extra={"worker_pid": self.worker_id, "backoff_seconds": backoff_seconds}
                    )
                    await asyncio.sleep(backoff_seconds)
                else:
                    logger.error(
                        f"Worker {self.worker_id}: Failed after {retry_count} attempts",
                        extra={"worker_pid": self.worker_id}
                    )
                    return False

        return False

    async def cleanup(self) -> None:
        """
        Cleanup worker resources on shutdown

        Ensures proper cleanup of Anthropic AsyncAnthropic client and other resources
        Uses aclose() for async client cleanup
        """
        if not self.initialized:
            return

        try:
            logger.info(
                f"Cleaning up worker {self.worker_id}",
                extra={
                    "worker_pid": self.worker_id,
                    "requests_processed": self.request_count,
                    "errors_encountered": self.error_count
                }
            )

            # Close Anthropic AsyncAnthropic client if available
            # AsyncAnthropic uses aclose() not close()
            if self.orchestrator and hasattr(self.orchestrator, 'client'):
                if hasattr(self.orchestrator.client, 'aclose'):
                    try:
                        await self.orchestrator.client.aclose()
                        logger.info(
                            f"Worker {self.worker_id}: Anthropic client closed",
                            extra={"worker_pid": self.worker_id}
                        )
                    except Exception as e:
                        logger.warning(
                            f"Worker {self.worker_id}: Error closing Anthropic client - {e}",
                            extra={"worker_pid": self.worker_id}
                        )

            # Clear references
            self.orchestrator = None
            self.initialized = False

            logger.info(
                f"Worker {self.worker_id} cleanup complete",
                extra={"worker_pid": self.worker_id}
            )

        except Exception as e:
            logger.error(
                f"Worker {self.worker_id}: Error during cleanup - {e}",
                extra={"worker_pid": self.worker_id},
                exc_info=True
            )

    def increment_request_count(self) -> None:
        """Track successful request"""
        self.request_count += 1

    def increment_error_count(self) -> None:
        """Track failed request"""
        self.error_count += 1

    def get_stats(self) -> dict:
        """
        Get worker statistics

        Returns:
            Dict with worker statistics
        """
        uptime = None
        if self.initialization_time:
            uptime = (datetime.utcnow() - self.initialization_time).total_seconds()

        return {
            "worker_id": self.worker_id,
            "initialized": self.initialized,
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "uptime_seconds": uptime,
            "requests_processed": self.request_count,
            "errors_encountered": self.error_count,
            "orchestrator_ready": self.orchestrator is not None
        }


# Global worker state instance
# Each worker process will have its own instance of this object
worker_state = WorkerState()
