#!/usr/bin/env python3
"""Verify Railway deployment is working correctly."""

import requests
import sys
from typing import Dict, Any

def check_endpoint(url: str, endpoint: str = "") -> Dict[str, Any]:
    """Check if an endpoint is responding correctly."""
    full_url = f"{url.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(full_url, timeout=10)
        return {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }

def main():
    """Run deployment verification tests."""
    base_url = input("Enter your Railway deployment URL (e.g., https://your-app.up.railway.app): ").strip()

    print("\n🔍 Checking deployment health...\n")

    # Test health endpoint
    print("1. Health Check:")
    health = check_endpoint(base_url, "/")
    if health["success"]:
        print("   ✅ Service is healthy")
        print(f"   Response: {health['response']}")
    else:
        print(f"   ❌ Health check failed: {health.get('error', f'Status {health.get('status_code')}')}")
        sys.exit(1)

    # Test API stats endpoint
    print("\n2. API Stats Endpoint:")
    stats = check_endpoint(base_url, "/api/stats")
    if stats["success"]:
        print("   ✅ API is responding correctly")
        print(f"   Stats: {stats['response']}")
    else:
        print(f"   ⚠️  Stats endpoint not available: {stats.get('error', f'Status {stats.get('status_code')}')}")

    print("\n✨ Deployment verification complete!")
    if health["success"]:
        print("Your Railway deployment is working correctly!")
    else:
        print("There are issues with your deployment. Please check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
