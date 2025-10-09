"""
Security Hardening Middleware for NDA Processing API
Implements rate limiting, file validation, request size limits, API key management, and audit logging
"""

import os
import time
import hashlib
import logging
import json
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False
import uuid
from typing import Dict, Optional, List, Any, Set
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import redis.asyncio as redis
from fastapi import Request, Response, HTTPException, status
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel
import aiofiles

logger = logging.getLogger(__name__)


# Rate limiter configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=os.getenv("REDIS_URL", "memory://")
)


class APIKey(BaseModel):
    """API Key model."""
    key_id: str
    key_hash: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    rate_limit: int = 10  # requests per minute
    max_file_size_mb: int = 50
    allowed_endpoints: List[str] = []
    metadata: Dict[str, Any] = {}


class SecurityConfig:
    """Security configuration."""

    # File upload limits
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    MAX_BATCH_SIZE_MB = int(os.getenv("MAX_BATCH_SIZE_MB", "500"))

    # Rate limiting
    DEFAULT_RATE_LIMIT = "10 per minute"
    BATCH_RATE_LIMIT = "2 per minute"

    # Allowed file types (magic numbers)
    ALLOWED_MIME_TYPES = {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
        "application/msword"  # .doc (legacy)
    }

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {".docx", ".doc"}

    # API key rotation
    KEY_ROTATION_DAYS = int(os.getenv("KEY_ROTATION_DAYS", "90"))

    # Audit log settings
    AUDIT_LOG_PATH = Path("./logs/audit")
    AUDIT_LOG_RETENTION_DAYS = 90


class FileValidator:
    """Validates uploaded files for security."""

    def __init__(self):
        self.magic = magic.Magic(mime=True) if HAS_MAGIC else None

    def validate_file(self, file_content: bytes, filename: str) -> Tuple[bool, str]:
        """
        Validate file content and type.

        Args:
            file_content: File binary content
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > SecurityConfig.MAX_FILE_SIZE_MB:
            return False, f"File size {file_size_mb:.1f}MB exceeds limit of {SecurityConfig.MAX_FILE_SIZE_MB}MB"

        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in SecurityConfig.ALLOWED_EXTENSIONS:
            return False, f"File extension {file_ext} not allowed"

        # Verify magic number (file content type)
        if self.magic:
            try:
                mime_type = self.magic.from_buffer(file_content[:8192])  # Check first 8KB
                if mime_type not in SecurityConfig.ALLOWED_MIME_TYPES:
                    return False, f"File type {mime_type} not allowed"
            except Exception as e:
                logger.error(f"Magic number verification failed: {e}")
                return False, "File type verification failed"

        # Check for embedded macros or scripts (basic check for DOCX)
        if file_ext == ".docx":
            # DOCX is a ZIP file, check for suspicious content
            if b"macroEnabled" in file_content or b"vbaProject" in file_content:
                return False, "File contains macros which are not allowed"

        return True, ""


class APIKeyManager:
    """Manages API keys with rotation support."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.redis_client: Optional[redis.Redis] = None
        self.keys_cache: Dict[str, APIKey] = {}

        if self.redis_url:
            asyncio.create_task(self._init_redis())

    async def _init_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("API key manager Redis connection established")
        except Exception as e:
            logger.warning(f"API key manager Redis connection failed: {e}")
            self.redis_client = None

    def generate_api_key(self, name: str, metadata: Dict = None) -> Tuple[str, str]:
        """
        Generate new API key.

        Args:
            name: Key name/description
            metadata: Additional metadata

        Returns:
            Tuple of (key_id, raw_key)
        """
        key_id = str(uuid.uuid4())
        raw_key = f"nda_{uuid.uuid4().hex}_{int(time.time())}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=datetime.now(),
            metadata=metadata or {}
        )

        # Store in cache
        self.keys_cache[key_id] = api_key

        # Store in Redis if available
        if self.redis_client:
            asyncio.create_task(self._store_key_redis(api_key))

        return key_id, raw_key

    async def _store_key_redis(self, api_key: APIKey):
        """Store API key in Redis."""
        try:
            await self.redis_client.hset(
                f"api_key:{api_key.key_id}",
                mapping={
                    "data": api_key.json(),
                    "created": api_key.created_at.isoformat()
                }
            )
            await self.redis_client.expire(
                f"api_key:{api_key.key_id}",
                SecurityConfig.KEY_ROTATION_DAYS * 86400
            )
        except Exception as e:
            logger.error(f"Failed to store API key in Redis: {e}")

    async def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate API key.

        Args:
            raw_key: Raw API key string

        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Check cache first
        for api_key in self.keys_cache.values():
            if api_key.key_hash == key_hash and api_key.is_active:
                # Check if key needs rotation
                age = datetime.now() - api_key.created_at
                if age.days > SecurityConfig.KEY_ROTATION_DAYS:
                    logger.warning(f"API key {api_key.key_id} needs rotation")

                # Update last used
                api_key.last_used = datetime.now()
                return api_key

        # Check Redis if available
        if self.redis_client:
            # This would need implementation to scan Redis keys
            pass

        return None

    async def revoke_api_key(self, key_id: str):
        """Revoke an API key."""
        if key_id in self.keys_cache:
            self.keys_cache[key_id].is_active = False

        if self.redis_client:
            await self.redis_client.delete(f"api_key:{key_id}")


class AuditLogger:
    """Handles audit logging for security events."""

    def __init__(self):
        self.log_path = SecurityConfig.AUDIT_LOG_PATH
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.current_log_file = self._get_log_file()

    def _get_log_file(self) -> Path:
        """Get current log file path."""
        date_str = datetime.now().strftime("%Y%m%d")
        return self.log_path / f"audit_{date_str}.jsonl"

    async def log_event(
        self,
        event_type: str,
        request: Request,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None
    ):
        """
        Log security event.

        Args:
            event_type: Type of event (upload, auth_fail, rate_limit, etc.)
            request: FastAPI request object
            details: Event details
            user_id: Optional user identifier
            api_key_id: Optional API key identifier
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "ip_address": get_remote_address(request),
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("user-agent"),
            "user_id": user_id,
            "api_key_id": api_key_id,
            "details": details
        }

        try:
            async with aiofiles.open(self.current_log_file, "a") as f:
                await f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    async def cleanup_old_logs(self):
        """Remove old audit logs."""
        cutoff = datetime.now() - timedelta(days=SecurityConfig.AUDIT_LOG_RETENTION_DAYS)

        for log_file in self.log_path.glob("audit_*.jsonl"):
            try:
                # Parse date from filename
                date_str = log_file.stem.replace("audit_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")

                if file_date < cutoff:
                    log_file.unlink()
                    logger.info(f"Removed old audit log: {log_file}")
            except Exception as e:
                logger.error(f"Failed to clean up log {log_file}: {e}")


class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware."""

    def __init__(self, app, enable_api_keys: bool = False):
        super().__init__(app)
        self.file_validator = FileValidator()
        self.api_key_manager = APIKeyManager() if enable_api_keys else None
        self.audit_logger = AuditLogger()
        self.enable_api_keys = enable_api_keys

    async def dispatch(self, request: Request, call_next):
        """Process request through security checks."""
        start_time = time.time()

        try:
            # Skip security for health check
            if request.url.path == "/":
                return await call_next(request)

            # API key validation (if enabled)
            api_key_id = None
            if self.enable_api_keys and request.url.path.startswith("/api/"):
                api_key = request.headers.get("X-API-Key")
                if not api_key:
                    await self.audit_logger.log_event(
                        "auth_fail",
                        request,
                        {"reason": "missing_api_key"}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="API key required"
                    )

                key_obj = await self.api_key_manager.validate_api_key(api_key)
                if not key_obj:
                    await self.audit_logger.log_event(
                        "auth_fail",
                        request,
                        {"reason": "invalid_api_key"}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid API key"
                    )

                api_key_id = key_obj.key_id

                # Check endpoint permissions
                if key_obj.allowed_endpoints and request.url.path not in key_obj.allowed_endpoints:
                    await self.audit_logger.log_event(
                        "auth_fail",
                        request,
                        {"reason": "endpoint_not_allowed", "api_key": api_key_id}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Endpoint not allowed for this API key"
                    )

            # Process request
            response = await call_next(request)

            # Log successful request
            processing_time = time.time() - start_time
            if request.url.path.startswith("/api/"):
                await self.audit_logger.log_event(
                    "request_success",
                    request,
                    {
                        "status_code": response.status_code,
                        "processing_time": processing_time
                    },
                    api_key_id=api_key_id
                )

            # Add security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            await self.audit_logger.log_event(
                "error",
                request,
                {"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal security error"
            )


def apply_rate_limit(rate: str = SecurityConfig.DEFAULT_RATE_LIMIT):
    """
    Decorator to apply rate limiting to endpoints.

    Args:
        rate: Rate limit string (e.g., "10 per minute")
    """
    def decorator(func):
        @wraps(func)
        @limiter.limit(rate)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate_file_upload(max_size_mb: int = SecurityConfig.MAX_FILE_SIZE_MB):
    """
    Decorator to validate file uploads.

    Args:
        max_size_mb: Maximum file size in MB
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract file from arguments
            file = kwargs.get('file') or (args[1] if len(args) > 1 else None)

            if file:
                content = await file.read()
                await file.seek(0)  # Reset file pointer

                validator = FileValidator()
                is_valid, error = validator.validate_file(content, file.filename)

                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File validation failed: {error}"
                    )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Global instances
file_validator = FileValidator()
api_key_manager = APIKeyManager()
audit_logger = AuditLogger()