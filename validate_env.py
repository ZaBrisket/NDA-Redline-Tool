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
        print("[OK] OpenAI API Key configured")

    if not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("ANTHROPIC_API_KEY is not set")
    else:
        print("[OK] Anthropic API Key configured")

    # Optional but recommended
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        warnings.append("REDIS_URL not set - caching features will be disabled")
        print("[ ] Redis not configured (caching disabled)")
        # Auto-disable Redis features
        os.environ["USE_REDIS_QUEUE"] = "false"
        os.environ["ENABLE_SEMANTIC_CACHE"] = "false"
    else:
        print(f"[OK] Redis configured: {redis_url[:20]}...")

    # V2 Pipeline Configuration
    print("\n=== V2 Pipeline Configuration ===")
    enforcement = os.getenv('ENFORCEMENT_LEVEL', 'Balanced')
    print(f"- Enforcement Level: {enforcement}")
    if enforcement not in ['Bloody', 'Balanced', 'Lenient']:
        warnings.append(f"Invalid ENFORCEMENT_LEVEL: {enforcement}. Using default: Balanced")

    # Pass Configuration
    print("\n4-Pass Pipeline:")
    print(f"- Pass 0 (Rules): {os.getenv('ENABLE_PASS_0', 'true')}")
    print(f"- Pass 1 (GPT-5): {os.getenv('ENABLE_PASS_1', 'true')}")
    print(f"- Pass 2 (Sonnet): {os.getenv('ENABLE_PASS_2', 'true')}")
    print(f"- Pass 3 (Opus): {os.getenv('ENABLE_PASS_3', 'true')}")
    print(f"- Pass 4 (Consistency): {os.getenv('ENABLE_PASS_4', 'true')}")

    # Model Configuration
    print("\nModel Configuration:")
    print(f"- GPT Model: {os.getenv('GPT_MODEL', 'gpt-5')}")
    print(f"- Sonnet Model: {os.getenv('SONNET_MODEL', 'claude-3-5-sonnet-20241022')}")
    print(f"- Opus Model: {os.getenv('OPUS_MODEL', 'claude-3-opus-20240229')}")

    # Performance settings
    print("\nPerformance Configuration:")
    print(f"- Prompt Caching: {os.getenv('USE_PROMPT_CACHING', 'true')}")
    print(f"- Validation Rate: {os.getenv('VALIDATION_RATE', '0.15')}")
    print(f"- Confidence Threshold: {os.getenv('CONFIDENCE_THRESHOLD', '95')}")
    print(f"- Skip GPT Threshold: {os.getenv('SKIP_GPT_CONFIDENCE_THRESHOLD', '98')}%")
    print(f"- Opus Threshold: {os.getenv('OPUS_CONFIDENCE_THRESHOLD', '85')}%")
    print(f"- Max Concurrent Docs: {os.getenv('MAX_CONCURRENT_DOCUMENTS', '3')}")
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
        print("[ERROR] ERRORS FOUND:")
        for error in errors:
            print(f"   - {error}")
        print("\nDeployment cannot proceed. Please fix the errors above.")
        return False

    if warnings:
        print("[WARNING] WARNINGS:")
        for warning in warnings:
            print(f"   - {warning}")

    print("[SUCCESS] Environment validation successful!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    if not validate_environment():
        sys.exit(1)