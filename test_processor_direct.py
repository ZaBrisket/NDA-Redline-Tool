"""Direct test of document processor"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.workers.document_worker import DocumentProcessor

async def test_processor():
    processor = DocumentProcessor(storage_path="./storage")

    print("Starting direct processor test...")
    print("=" * 60)

    job_id = "test_direct_123"
    file_path = "./test_comprehensive_nda.docx"

    if not Path(file_path).exists():
        print(f"ERROR: Test file {file_path} not found")
        return

    print(f"Processing file: {file_path}")
    print(f"Job ID: {job_id}")
    print()

    result = await processor.process_document(
        job_id=job_id,
        file_path=file_path,
        status_callback=None
    )

    print("=" * 60)
    print("RESULT:")
    print(f"Status: {result.get('status')}")
    print(f"Total redlines: {result.get('total_redlines', 0)}")
    print(f"Rule redlines: {result.get('rule_redlines', 0)}")
    print(f"LLM redlines: {result.get('llm_redlines', 0)}")

    if result.get('error'):
        print(f"ERROR: {result['error']}")

    if result.get('output_path'):
        output_path = Path(result['output_path'])
        print(f"Output path: {output_path}")
        print(f"Output exists: {output_path.exists()}")
        if output_path.exists():
            print(f"Output size: {output_path.stat().st_size} bytes")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_processor())
