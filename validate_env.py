#!/usr/bin/env python
"""
Environment validation script for NDA Redline Tool
Checks that all required environment variables are properly configured
"""

import os
import sys

def validate_environment():
    """Validate environment variables and configuration."""

    print("=" * 50)
    print("NDA Redline Tool - Environment Validation")
    print("=" * 50)

    errors = []
    warnings = []

    # Required variables
    if not os.getenv("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY is not set")
    else:
        print("✓ OpenAI API Key configured")

    if not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY is not set")
    else:
        print("✓ Anthropic API Key configured")

    # Optional but recommended
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        warnings.append("REDIS_URL not set - caching features will be disabled")
        print("○ Redis not configured (caching disabled)")
        # Auto-disable Redis features
        os.environ["USE_REDIS_QUEUE"] = "false"
        os.environ["ENABLE_SEMANTIC_CACHE"] = "false"
    else:
        print(f"✓ Redis configured: {redis_url[:20]}...")

    # Performance settings
    print("\nPerformance Configuration:")
    print(f"- Prompt Caching: {os.getenv('USE_PROMPT_CACHING', 'true')}")
    print(f"- Validation Rate: {os.getenv('VALIDATION_RATE', '0.15')}")
    print(f"- Confidence Threshold: {os.getenv('CONFIDENCE_THRESHOLD', '95')}")
    print(f"- Max Processing Time: {os.getenv('MAX_PROCESSING_TIME', '60')}s")
    print(f"- Worker Concurrency: {os.getenv('WORKER_CONCURRENCY', '2')}")

    # Caching settings
    print("\nCaching Configuration:")
    print(f"- Semantic Cache: {os.getenv('ENABLE_SEMANTIC_CACHE', 'true' if redis_url else 'false')}")
    print(f"- Similarity Threshold: {os.getenv('SIMILARITY_THRESHOLD', '0.92')}")
    print(f"- Redis Queue: {os.getenv('USE_REDIS_QUEUE', 'true' if redis_url else 'false')}")

    # Limits
    print("\nLimits Configuration:")
    print(f"- Max File Size: {os.getenv('MAX_FILE_SIZE_MB', '50')}MB")
    print(f"- Max Batch Size: {os.getenv('MAX_BATCH_SIZE', '100')} files")
    print(f"- Max Batch Size MB: {os.getenv('MAX_BATCH_SIZE_MB', '500')}MB")

    # Railway info
    if os.getenv("RAILWAY_PROJECT_NAME"):
        print("\nRailway Deployment:")
        print(f"- Project: {os.getenv('RAILWAY_PROJECT_NAME')}")
        print(f"- Environment: {os.getenv('RAILWAY_ENVIRONMENT_NAME')}")
        print(f"- Service: {os.getenv('RAILWAY_SERVICE_NAME')}")

    print("\n" + "=" * 50)

    # Report results
    if errors:
        print("❌ ERRORS FOUND:")
        for error in errors:
            print(f"   - {error}")
        print("\nDeployment cannot proceed. Please fix the errors above.")
        return False

    if warnings:
        print("⚠️  WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")

    print("✅ Environment validation successful!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    if not validate_environment():
        sys.exit(1)