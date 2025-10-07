"""
Quick start script for NDA Reviewer backend
"""
import sys
import os
from pathlib import Path

# Check Python version
if sys.version_info < (3, 10):
    print("ERROR: Python 3.10+ required")
    print(f"Current version: {sys.version}")
    sys.exit(1)

# Check if we're in the right directory
backend_dir = Path(__file__).parent / "backend"
if not backend_dir.exists():
    print("ERROR: backend directory not found")
    sys.exit(1)

# Check if dependencies are installed
try:
    import fastapi
    import uvicorn
    import docx
    from lxml import etree
    print("✓ Core dependencies installed")
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    print("\nPlease install dependencies:")
    print("  cd backend")
    print("  pip install -r requirements.txt")
    sys.exit(1)

# Check for .env file
env_file = backend_dir / ".env"
if not env_file.exists():
    print("WARNING: .env file not found")
    print(f"\nCreate {env_file} with your API keys:")
    print("  OPENAI_API_KEY=sk-...")
    print("  ANTHROPIC_API_KEY=sk-ant-...")
    print("\nYou can still test rule-based redlines without API keys.")
    print("\nPress Enter to continue anyway, or Ctrl+C to exit...")
    try:
        input()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

# Load environment
from dotenv import load_dotenv
if env_file.exists():
    load_dotenv(env_file)
    print("✓ Loaded environment variables")

# Create storage directories
storage_dirs = [
    backend_dir.parent / "storage" / "uploads",
    backend_dir.parent / "storage" / "working",
    backend_dir.parent / "storage" / "exports"
]

for dir_path in storage_dirs:
    dir_path.mkdir(parents=True, exist_ok=True)

print("✓ Storage directories ready")

# Change to backend directory
os.chdir(backend_dir)

print("\n" + "="*60)
print("NDA AUTOMATED REDLINING SERVER")
print("="*60)
print("\nStarting FastAPI server...")
print("  API:  http://localhost:8000")
print("  Docs: http://localhost:8000/docs")
print("\nPress Ctrl+C to stop")
print("="*60 + "\n")

# Start server
import uvicorn
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=8000,
    reload=True,
    log_level="info"
)
