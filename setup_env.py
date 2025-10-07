"""
Automated .env setup script
Reads API keys from your saved files and creates backend/.env
"""
import os
from pathlib import Path

# Paths to your API key files
ANTHROPIC_KEY_FILE = r"C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - Anthropic.txt"
OPENAI_KEY_FILE = r"C:\Users\IT\OneDrive\Desktop\Claude Projects\API Keys\NDA Reviewer - OpenAI.txt"

# Project paths
PROJECT_DIR = Path(__file__).parent
BACKEND_DIR = PROJECT_DIR / "backend"
ENV_FILE = BACKEND_DIR / ".env"

def read_key_file(file_path):
    """Read API key from file and strip whitespace"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            key = f.read().strip()
            return key
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        return None
    except Exception as e:
        print(f"[ERROR] Error reading {file_path}: {e}")
        return None

def create_env_file():
    """Create .env file with API keys"""
    print("=" * 60)
    print("NDA Reviewer - Environment Setup")
    print("=" * 60)

    # Read API keys
    print("\nReading API keys from files...")

    anthropic_key = read_key_file(ANTHROPIC_KEY_FILE)
    if anthropic_key:
        print(f"[OK] Anthropic API key loaded ({len(anthropic_key)} characters)")
    else:
        print("[ERROR] Failed to load Anthropic API key")
        return False

    openai_key = read_key_file(OPENAI_KEY_FILE)
    if openai_key:
        print(f"[OK] OpenAI API key loaded ({len(openai_key)} characters)")
    else:
        print("[ERROR] Failed to load OpenAI API key")
        return False

    # Create .env content
    env_content = f"""# LLM API Keys
OPENAI_API_KEY={openai_key}
ANTHROPIC_API_KEY={anthropic_key}

# LLM Configuration
USE_PROMPT_CACHING=true
VALIDATION_RATE=0.15
CONFIDENCE_THRESHOLD=95

# Processing
MAX_PROCESSING_TIME=60
WORKER_CONCURRENCY=2

# Storage
STORAGE_PATH=./storage
RETENTION_DAYS=7

# Security
API_KEY=your-api-key-here
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
"""

    # Create backend directory if it doesn't exist
    BACKEND_DIR.mkdir(exist_ok=True)

    # Check if .env already exists
    if ENV_FILE.exists():
        print(f"\n[WARNING] {ENV_FILE} already exists")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("[CANCELLED] Existing .env file preserved.")
            return False

    # Write .env file
    try:
        with open(ENV_FILE, 'w', encoding='utf-8') as f:
            f.write(env_content)
        print(f"\n[SUCCESS] Created: {ENV_FILE}")
        print("\nEnvironment file contents:")
        print("-" * 60)
        print(f"OPENAI_API_KEY={openai_key[:20]}...")
        print(f"ANTHROPIC_API_KEY={anthropic_key[:20]}...")
        print("USE_PROMPT_CACHING=true")
        print("VALIDATION_RATE=0.15")
        print("CONFIDENCE_THRESHOLD=95")
        print("-" * 60)

        return True

    except Exception as e:
        print(f"[ERROR] Error writing .env file: {e}")
        return False

def verify_keys():
    """Quick verification that keys look valid"""
    print("\nVerifying API key formats...")

    anthropic_key = read_key_file(ANTHROPIC_KEY_FILE)
    openai_key = read_key_file(OPENAI_KEY_FILE)

    issues = []

    # Check Anthropic key format
    if anthropic_key:
        if not anthropic_key.startswith('sk-ant-'):
            issues.append("[WARNING] Anthropic key doesn't start with 'sk-ant-'")
        if len(anthropic_key) < 50:
            issues.append("[WARNING] Anthropic key seems too short")

    # Check OpenAI key format
    if openai_key:
        if not (openai_key.startswith('sk-') or openai_key.startswith('sk-proj-')):
            issues.append("[WARNING] OpenAI key doesn't start with 'sk-' or 'sk-proj-'")
        if len(openai_key) < 40:
            issues.append("[WARNING] OpenAI key seems too short")

    if issues:
        print("\nPotential issues found:")
        for issue in issues:
            print(f"   {issue}")
        print("\nKeys have been saved, but please verify they are correct.")
    else:
        print("[OK] API key formats look correct!")

def main():
    success = create_env_file()

    if success:
        verify_keys()

        print("\n" + "=" * 60)
        print("[SUCCESS] Setup Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start the backend:")
        print("   cd backend")
        print("   python -m app.main")
        print("\n2. Or use the quick start script:")
        print("   python start_server.py")
        print("\n3. For deployment, your .env is ready for local testing.")
        print("   For Railway/Render, you'll add these keys manually")
        print("   in their dashboard (see GITHUB_VERCEL_DEPLOYMENT.md)")
        print("=" * 60)
    else:
        print("\n[ERROR] Setup failed. Please check the errors above.")
        print("\nManual setup:")
        print(f"1. Copy: backend/.env.template -> backend/.env")
        print(f"2. Edit backend/.env and paste your API keys")

if __name__ == "__main__":
    main()
