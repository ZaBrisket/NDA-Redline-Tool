"""
Railway-optimized logging configuration
Ensures INFO logs go to stdout and WARNING+ go to stderr for proper Railway log level parsing
"""

import sys
import logging
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


class RailwayJSONFormatter(logging.Formatter):
    """
    JSON formatter optimized for Railway deployment
    Produces structured logs with proper log level attribution
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for Railway"""
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add worker information if available
        if hasattr(record, "worker_pid"):
            log_obj["worker_pid"] = record.worker_pid

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id

        # Add document ID if available
        if hasattr(record, "document_id"):
            log_obj["document_id"] = record.document_id

        # Add extra fields from the record
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_obj.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add stack info if present
        if record.stack_info:
            log_obj["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_obj)


class InfoFilter(logging.Filter):
    """Filter that only allows INFO and DEBUG level messages"""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= logging.INFO


class WarningFilter(logging.Filter):
    """Filter that only allows WARNING and above level messages"""

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= logging.WARNING


def setup_railway_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for Railway deployment with proper stream routing

    Railway interprets logs based on stream:
    - stdout: INFO and DEBUG messages (displayed as info in Railway)
    - stderr: WARNING, ERROR, CRITICAL messages (displayed as warnings/errors in Railway)

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Normalize log level
    log_level = log_level.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove all existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Determine if we're in Railway environment
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    use_json = os.getenv("LOG_FORMAT", "json" if is_railway else "text") == "json"

    # Create formatters
    if use_json:
        formatter = RailwayJSONFormatter()
    else:
        # Human-readable format for local development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # STDOUT handler for INFO and DEBUG
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(InfoFilter())
    stdout_handler.setFormatter(formatter)

    # STDERR handler for WARNING and above
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.addFilter(WarningFilter())
    stderr_handler.setFormatter(formatter)

    # Add handlers to root logger
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Log setup completion
    logger = logging.getLogger(__name__)
    logger.info(
        f"Railway logging configured: level={log_level}, format={use_json and 'json' or 'text'}, environment={os.getenv('RAILWAY_ENVIRONMENT', 'local')}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Convenience function for adding context to log records
def add_log_context(**kwargs: Any) -> Dict[str, Any]:
    """
    Create a dict of extra context to pass to logger calls

    Example:
        logger.info("Processing document", extra=add_log_context(doc_id="123", worker_pid=os.getpid()))

    Args:
        **kwargs: Key-value pairs to add to log context

    Returns:
        Dict formatted for logger's 'extra' parameter
    """
    return {"extra_fields": kwargs}
