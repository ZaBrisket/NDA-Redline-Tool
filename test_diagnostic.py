"""
Diagnostic Test Script - Run NDA processing with detailed logging
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.workers.document_worker import DocumentProcessor
from docx import Document

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('diagnostic_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def run_diagnostic_test():
    """Run comprehensive diagnostic test"""
    print("\n" + "="*80)
    print("NDA REDLINE TOOL - DIAGNOSTIC TEST")
    print("="*80)

    test_file = Path("test_comprehensive_nda.docx")

    if not test_file.exists():
        print(f"ERROR: Test file {test_file} not found")
        print("Please run create_test_nda.py first")
        return

    print(f"\nTest file: {test_file}")
    print(f"File size: {test_file.stat().st_size} bytes")

    # Initialize processor
    print("\n--- Initializing DocumentProcessor ---")
    processor = DocumentProcessor()

    # Check LLM orchestrator configuration
    print("\n--- LLM Configuration ---")
    print(f"OpenAI Client: {processor.llm_orchestrator.openai_client}")
    print(f"Anthropic Client: {processor.llm_orchestrator.anthropic_client}")
    print(f"Validation Rate: {processor.llm_orchestrator.validation_rate}")
    print(f"Confidence Threshold: {processor.llm_orchestrator.confidence_threshold}")
    print(f"Use Prompt Caching: {processor.llm_orchestrator.use_prompt_caching}")

    # Process document
    job_id = f"diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n--- Processing Document (Job ID: {job_id}) ---")
    start_time = datetime.now()

    result = await processor.process_document(
        job_id=job_id,
        file_path=str(test_file),
        status_callback=None
    )

    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()

    print("\n" + "="*80)
    print("PROCESSING RESULTS")
    print("="*80)

    print(f"\nProcessing Time: {processing_time:.2f} seconds")
    print(f"Status: {result.get('status')}")

    if result.get('status') == 'error':
        print(f"ERROR: {result.get('error')}")
        return

    print(f"\nRedline Counts:")
    print(f"  Total Redlines: {result.get('total_redlines', 0)}")
    print(f"  Rule-based: {result.get('rule_redlines', 0)}")
    print(f"  LLM-based: {result.get('llm_redlines', 0)}")

    # LLM Statistics
    llm_stats = result.get('llm_stats', {})
    print(f"\nLLM Statistics:")
    print(f"  GPT Calls: {llm_stats.get('gpt_calls', 0)}")
    print(f"  GPT Input Tokens: {llm_stats.get('gpt_tokens_input', 0)}")
    print(f"  GPT Output Tokens: {llm_stats.get('gpt_tokens_output', 0)}")
    print(f"  Claude Calls: {llm_stats.get('claude_calls', 0)}")
    print(f"  Claude Input Tokens: {llm_stats.get('claude_tokens_input', 0)}")
    print(f"  Claude Output Tokens: {llm_stats.get('claude_tokens_output', 0)}")
    print(f"  Validations: {llm_stats.get('validations', 0)}")
    print(f"  Conflicts: {llm_stats.get('conflicts', 0)}")
    print(f"  Total Cost: ${llm_stats.get('total_cost_usd', 0):.4f}")

    # Show all redlines
    redlines = result.get('redlines', [])
    print(f"\n--- REDLINES FOUND ({len(redlines)}) ---")

    if len(redlines) == 0:
        print("WARNING: No redlines were found!")
        print("This is unexpected for the test document which contains known violations:")
        print("  - Perpetual term")
        print("  - Wrong governing law (Cayman Islands)")
        print("  - Indemnification clause")
        print("  - Overly broad non-compete")
    else:
        for i, redline in enumerate(redlines):
            print(f"\nRedline #{i+1}:")
            print(f"  Clause Type: {redline.get('clause_type')}")
            print(f"  Severity: {redline.get('severity')}")
            print(f"  Confidence: {redline.get('confidence')}%")
            print(f"  Source: {redline.get('source')}")
            print(f"  Position: {redline.get('start')}-{redline.get('end')}")
            print(f"  Original: {redline.get('original_text', '')[:100]}...")
            print(f"  Revised: {redline.get('revised_text', '')[:100]}...")
            print(f"  Explanation: {redline.get('explanation', 'N/A')}")

    # Analyze working text
    working_text_file = Path(f"backend/storage/working/{job_id}.txt")
    if working_text_file.exists():
        working_text = working_text_file.read_text(encoding='utf-8')
        print(f"\n--- WORKING TEXT ANALYSIS ---")
        print(f"Length: {len(working_text)} characters")
        print(f"First 500 chars: {working_text[:500]}")

        # Check for key phrases that should trigger redlines
        checks = {
            "perpetual": "perpetuity" in working_text.lower() or "indefinitely" in working_text.lower(),
            "cayman": "cayman" in working_text.lower(),
            "indemnify": "indemnify" in working_text.lower(),
            "10 years": "10 years" in working_text.lower()
        }

        print(f"\nKey phrase checks:")
        for phrase, found in checks.items():
            status = "✓ FOUND" if found else "✗ NOT FOUND"
            print(f"  {phrase}: {status}")

    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    print(f"\nLog file: diagnostic_test.log")
    print(f"Working text: {working_text_file}")
    print(f"Result JSON: backend/storage/working/{job_id}_result.json")


if __name__ == "__main__":
    asyncio.run(run_diagnostic_test())
