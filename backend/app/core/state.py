"""
Worker state management for Gunicorn multi-worker deployments
Ensures efficient resource initialization and prevents redundant orchestrator creation
"""

import os
import logging
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

    async def initialize(self, api_key: Optional[str] = None) -> bool:
        """
        Initialize worker-specific resources

        Args:
            api_key: Anthropic API key (optional, will use env var if not provided)

        Returns:
            True if initialization succeeded, False otherwise
        """
        if self.initialized:
            logger.info(
                f"Worker {self.worker_id} already initialized, skipping",
                extra={"worker_pid": self.worker_id}
            )
            return True

        try:
            logger.info(
                f"Initializing worker {self.worker_id}",
                extra={"worker_pid": self.worker_id}
            )

            # Import here to avoid circular dependencies
            from .llm_orchestrator import AllClaudeLLMOrchestrator

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

            # Initialize orchestrator
            self.orchestrator = AllClaudeLLMOrchestrator(api_key=api_key)
            self.initialized = True
            self.initialization_time = datetime.utcnow()

            logger.info(
                f"Worker {self.worker_id} initialized successfully",
                extra={
                    "worker_pid": self.worker_id,
                    "initialization_time": self.initialization_time.isoformat()
                }
            )

            return True

        except ValueError as e:
            logger.error(
                f"Worker {self.worker_id}: Invalid API key format - {e}",
                extra={"worker_pid": self.worker_id}
            )
            return False

        except Exception as e:
            logger.error(
                f"Worker {self.worker_id}: Initialization failed - {e}",
                extra={"worker_pid": self.worker_id},
                exc_info=True
            )
            return False

    async def cleanup(self) -> None:
        """
        Cleanup worker resources on shutdown

        Ensures proper cleanup of Anthropic client and other resources
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

            # Close Anthropic client if available
            if self.orchestrator and hasattr(self.orchestrator, 'client'):
                if hasattr(self.orchestrator.client, 'close'):
                    await self.orchestrator.client.close()
                    logger.info(
                        f"Worker {self.worker_id}: Anthropic client closed",
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
