#!/usr/bin/env python3
"""
Update CORS Configuration Script
Updates the backend CORS settings with your production URLs
"""

import os
import sys
import re
from pathlib import Path

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_success(text: str):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text: str):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text: str):
    print(f"{BLUE}ℹ {text}{RESET}")

def update_cors_in_main_py(vercel_url: str, additional_origins: list = None):
    """Update CORS configuration in backend/app/main.py"""

    main_py_path = Path(__file__).parent / "backend" / "app" / "main.py"

    if not main_py_path.exists():
        print_error(f"Could not find main.py at {main_py_path}")
        return False

    # Read the current content
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Prepare the new CORS origins list
    origins = [
        f'    "http://localhost:3000",  # Local development',
        f'    "http://localhost:8000",  # Local backend',
        f'    "{vercel_url}",  # Production frontend'
    ]

    if additional_origins:
        for origin in additional_origins:
            origins.append(f'    "{origin}",  # Additional origin')

    origins_str = '\n'.join(origins)

    # Create the new CORS configuration
    new_cors_config = f'''# CORS configuration
# Parse allowed origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "{vercel_url},http://localhost:3000,http://localhost:8000"
).split(",")'''

    # Try to replace the existing CORS configuration
    # Pattern to match the CORS configuration block
    pattern = r'# CORS configuration.*?ALLOWED_ORIGINS = \[.*?\]|# CORS configuration.*?\.split\("\,"\)'

    if re.search(pattern, content, re.DOTALL):
        # Replace existing configuration
        content = re.sub(pattern, new_cors_config, content, flags=re.DOTALL)
        print_success("Updated existing CORS configuration")
    else:
        print_error("Could not find CORS configuration pattern to replace")
        print_info("Please manually update the CORS_ORIGINS in main.py")
        return False

    # Write the updated content back
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print_success(f"Updated main.py with Vercel URL: {vercel_url}")
    return True

def create_env_file(railway_url: str, vercel_url: str):
    """Create or update .env files with production URLs"""

    # Update backend .env.production
    backend_env_path = Path(__file__).parent / "backend" / ".env.production"

    env_content = f"""# Production Environment Variables
# Copy these to Railway environment variables

# API Keys (REQUIRED)
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE

# CORS Configuration
CORS_ORIGINS={vercel_url},http://localhost:3000

# Application Settings
ENVIRONMENT=production
ENFORCEMENT_LEVEL=Balanced
USE_PROMPT_CACHING=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95

# File Processing
MAX_FILE_SIZE_MB=50
RETENTION_DAYS=7

# Performance
ENABLE_TELEMETRY=true
LOG_LEVEL=INFO

# Frontend URL (for email notifications, if implemented)
FRONTEND_URL={vercel_url}
"""

    with open(backend_env_path, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print_success(f"Created backend/.env.production")

    # Update frontend .env.production
    frontend_env_path = Path(__file__).parent / "frontend" / ".env.production"

    frontend_env_content = f"""# Production Environment Variables for Frontend
# This should be set in Vercel dashboard

NEXT_PUBLIC_API_URL={railway_url}
"""

    with open(frontend_env_path, 'w', encoding='utf-8') as f:
        f.write(frontend_env_content)

    print_success(f"Created frontend/.env.production")

    return True

def main():
    """Main workflow"""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{'CORS & Environment Configuration Update'.center(60)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

    # Get URLs from user
    print_info("Enter your Vercel frontend URL:")
    print_info("Example: https://nda-reviewer.vercel.app")
    vercel_url = input("> ").strip().rstrip('/')

    if not vercel_url:
        print_error("Vercel URL is required!")
        return 1

    print_info("\nEnter your Railway backend URL:")
    print_info("Example: https://nda-backend.up.railway.app")
    railway_url = input("> ").strip().rstrip('/')

    if not railway_url:
        print_error("Railway URL is required!")
        return 1

    # Validate URLs
    if not vercel_url.startswith('http'):
        vercel_url = f"https://{vercel_url}"

    if not railway_url.startswith('http'):
        railway_url = f"https://{railway_url}"

    print_info(f"\nUpdating configuration with:")
    print_info(f"  Frontend: {vercel_url}")
    print_info(f"  Backend: {railway_url}")

    # Update CORS in main.py
    if update_cors_in_main_py(vercel_url):
        print_success("CORS configuration updated in main.py")

    # Create environment files
    if create_env_file(railway_url, vercel_url):
        print_success("Environment files created")

    # Print next steps
    print(f"\n{BOLD}{BLUE}{'NEXT STEPS'.center(60)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

    print_info("1. COMMIT AND PUSH the changes:")
    print(f"   {YELLOW}git add -A")
    print(f"   git commit -m 'Update CORS and environment for production'")
    print(f"   git push{RESET}")

    print_info("\n2. UPDATE RAILWAY environment variables:")
    print(f"   {YELLOW}CORS_ORIGINS={vercel_url},http://localhost:3000{RESET}")

    print_info("\n3. UPDATE VERCEL environment variable:")
    print(f"   {YELLOW}NEXT_PUBLIC_API_URL={railway_url}{RESET}")

    print_info("\n4. REDEPLOY both services:")
    print("   - Railway: Should auto-deploy on git push")
    print("   - Vercel: Should auto-deploy on git push")

    print_info("\n5. TEST the deployment:")
    print(f"   {YELLOW}python verify_deployment.py{RESET}")

    print_success("\nConfiguration update complete!")

    return 0

if __name__ == "__main__":
    sys.exit(main())