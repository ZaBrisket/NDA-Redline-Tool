"""
Application settings with validation and type safety
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional
import os

class Settings(BaseSettings):
    """
    Validated configuration settings for production deployment
    All settings can be overridden via environment variables
    """

    # ANTHROPIC CONFIGURATION (REQUIRED)
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude access",
        min_length=1
    )

    claude_opus_model: str = Field(
        default="claude-3-opus-20240229",
        description="Claude Opus model identifier"
    )

    claude_sonnet_model: str = Field(
        default="claude-3-5-sonnet-20240620",
        description="Claude Sonnet model identifier"
    )

    # PROCESSING CONFIGURATION
    max_retries: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls"
    )

    validation_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Percentage of documents to validate with Sonnet"
    )

    circuit_breaker_threshold: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Consecutive failures before circuit opens"
    )

    circuit_breaker_reset_time: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Seconds before circuit breaker reset attempt"
    )

    # DATABASE CONFIGURATION (OPTIONAL)
    database_url: Optional[str] = Field(
        default=None,
        description="PostgreSQL connection string"
    )

    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection string for caching/queuing"
    )

    # MONITORING CONFIGURATION
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )

    environment: str = Field(
        default="production",
        description="Deployment environment (development/staging/production)"
    )

    # LOGGING CONFIGURATION
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG/INFO/WARNING/ERROR)"
    )

    log_format: str = Field(
        default="json",
        description="Log format (json/text)"
    )

    # VALIDATION
    @validator("anthropic_api_key")
    def validate_anthropic_key(cls, v):
        """Ensure Anthropic API key has correct format"""
        if not v:
            raise ValueError("ANTHROPIC_API_KEY is required")
        if not v.startswith("sk-ant-"):
            raise ValueError(
                "Invalid Anthropic API key format. "
                "Must start with 'sk-ant-'. "
                "Please check your API key at console.anthropic.com"
            )
        return v

    @validator("environment")
    def validate_environment(cls, v):
        """Ensure valid environment name"""
        valid_environments = {"development", "staging", "production", "test"}
        if v not in valid_environments:
            raise ValueError(f"Environment must be one of: {valid_environments}")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        """Ensure valid log level"""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        # Allow extra fields for forward compatibility
        extra = "ignore"
