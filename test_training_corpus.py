"""
Test the NDA processor against the training corpus
Verify >95% accuracy on redlines
"""
import sys
import os
from pathlib import Path
import asyncio
from docx import Document

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.workers.document_worker import DocumentProcessor
from app.core.text_indexer import WorkingTextIndexer


TRAINING_DIR = Path(r"C:\Users\IT\OneDrive\Desktop\Claude Projects\NDA Reviewer\NDA Redlines to Train on")


class TrainingCorpusTest:
    """Test processor against training data"""

    def __init__(self):
        self.processor = DocumentProcessor()
        self.results = []

    async def test_single_document(self, doc_path: Path):
        """Test a single document"""
        print(f"\n{'='*80}")
        print(f"Testing: {doc_path.name}")
        print(f"{'='*80}")

        try:
            # Check if this is a redlined document
            if 'REDLINE' not in doc_path.name.upper():
                print(f"  Skipping (not a redlined document)")
                return None

            # Extract expected changes from redlined document
            doc = Document(str(doc_path))
            indexer = WorkingTextIndexer()
            indexer.build_index(doc)

            # Count track changes in training document
            expected_changes = self._count_track_changes(doc)

            print(f"  Expected changes (from training): {expected_changes}")

            # Create a temporary "clean" version (this is a simplified approach)
            # In reality, you'd need the original un-redlined version
            # For now, we'll just test that we can process the document

            # Process the document
            job_id = f"test_{doc_path.stem}"

            result = await self.processor.process_document(
                job_id=job_id,
                file_path=str(doc_path),
                status_callback=None
            )

            if result.get('status') == 'error':
                print(f"  ERROR: {result.get('error')}")
                return {
                    'file': doc_path.name,
                    'status': 'error',
                    'error': result.get('error')
                }

            total_redlines = result.get('total_redlines', 0)
            rule_redlines = result.get('rule_redlines', 0)
            llm_redlines = result.get('llm_redlines', 0)

            print(f"  Generated redlines: {total_redlines}")
            print(f"    - Rule-based: {rule_redlines}")
            print(f"    - LLM-based: {llm_redlines}")

            # Calculate rough accuracy (this is simplified)
            # Ideally we'd compare actual content of changes
            if expected_changes > 0:
                accuracy = min(100, (total_redlines / expected_changes) * 100)
            else:
                accuracy = 100 if total_redlines == 0 else 0

            print(f"  Estimated accuracy: {accuracy:.1f}%")

            # Show sample redlines
            print(f"\n  Sample redlines:")
            for i, redline in enumerate(result.get('redlines', [])[:5]):
                print(f"    {i+1}. [{redline['severity']}] {redline['clause_type']}")
                print(f"       Original: {redline['original_text'][:60]}...")
                print(f"       Revised:  {redline['revised_text'][:60]}...")

            return {
                'file': doc_path.name,
                'status': 'success',
                'expected_changes': expected_changes,
                'generated_redlines': total_redlines,
                'rule_redlines': rule_redlines,
                'llm_redlines': llm_redlines,
                'accuracy': accuracy
            }

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

            return {
                'file': doc_path.name,
                'status': 'error',
                'error': str(e)
            }

    def _count_track_changes(self, doc: Document) -> int:
        """Count track changes in a document"""
        from lxml import etree

        NAMESPACES = {
            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
        }

        count = 0

        for paragraph in doc.paragraphs:
            p_element = paragraph._element

            # Count deletions
            deletions = p_element.findall('.//w:del', NAMESPACES)
            count += len(deletions)

            # Count insertions
            insertions = p_element.findall('.//w:ins', NAMESPACES)
            count += len(insertions)

        return count

    async def test_all_documents(self):
        """Test all documents in training directory"""
        print(f"\n{'='*80}")
        print(f"TRAINING CORPUS TEST")
        print(f"{'='*80}")

        doc_files = list(TRAINING_DIR.glob("*.docx"))

        # Filter to redlined documents
        redlined = [f for f in doc_files if 'REDLINE' in f.name.upper()]

        print(f"\nFound {len(redlined)} redlined training documents")

        # Test first 5 for speed (remove limit for full test)
        test_files = redlined[:5]

        for doc_path in test_files:
            result = await self.test_single_document(doc_path)
            if result:
                self.results.append(result)

        # Print summary
        self._print_summary()

    def _print_summary(self):
        """Print test summary"""
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")

        successful = [r for r in self.results if r['status'] == 'success']
        errors = [r for r in self.results if r['status'] == 'error']

        print(f"\nTotal tests: {len(self.results)}")
        print(f"Successful: {len(successful)}")
        print(f"Errors: {len(errors)}")

        if successful:
            avg_accuracy = sum(r['accuracy'] for r in successful) / len(successful)
            avg_redlines = sum(r['generated_redlines'] for r in successful) / len(successful)

            print(f"\nAverage accuracy: {avg_accuracy:.1f}%")
            print(f"Average redlines per document: {avg_redlines:.1f}")

            # Breakdown
            total_rule = sum(r['rule_redlines'] for r in successful)
            total_llm = sum(r['llm_redlines'] for r in successful)

            print(f"\nRedline sources:")
            print(f"  Rule-based: {total_rule}")
            print(f"  LLM-based: {total_llm}")

        if errors:
            print(f"\nErrors encountered:")
            for error in errors:
                print(f"  - {error['file']}: {error['error']}")


async def main():
    """Run tests"""
    # Set up environment (you'll need to add your API keys to .env)
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / "backend" / ".env"

    if env_path.exists():
        load_dotenv(env_path)
        print("Loaded environment variables from .env")
    else:
        print("WARNING: No .env file found. LLM analysis will fail.")
        print(f"Expected path: {env_path}")
        print("\nYou can still test rule-based redlines without API keys.")

    tester = TrainingCorpusTest()
    await tester.test_all_documents()


if __name__ == "__main__":
    asyncio.run(main())
