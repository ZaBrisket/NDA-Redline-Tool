"""
Comprehensive tests for Document Processor with new LLM-first processing order
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.workers.document_worker import DocumentProcessor
from app.models.schemas import JobStatus


class TestDocumentProcessorOrdering:
    """Test the new processing order: LLM first, then rules"""

    @pytest.fixture
    def processor(self):
        """Create a processor with mocked dependencies"""
        with patch('app.workers.document_worker.RuleEngine'):
            with patch('app.workers.document_worker.LLMOrchestrator'):
                processor = DocumentProcessor(storage_path="./test_storage")

                # Mock the rule engine
                processor.rule_engine = Mock()
                processor.rule_engine.apply_rules = Mock(return_value=[
                    {
                        'rule_id': 'rule1',
                        'clause_type': 'term_limit',
                        'start': 10,
                        'end': 20,
                        'original_text': 'two years',
                        'revised_text': 'eighteen months',
                        'severity': 'high',
                        'confidence': 100,
                        'source': 'rule',
                        'explanation': 'Term must be 18 months'
                    }
                ])

                # Mock the LLM orchestrator
                processor.llm_orchestrator = Mock()
                processor.llm_orchestrator.analyze = Mock(return_value=[
                    {
                        'rule_id': 'llm1',
                        'clause_type': 'governing_law',
                        'start': 30,
                        'end': 40,
                        'original_text': 'Texas law',
                        'revised_text': 'Delaware law',
                        'severity': 'high',
                        'confidence': 95,
                        'source': 'llm',
                        'explanation': 'Must use Delaware law'
                    }
                ])
                processor.llm_orchestrator.get_stats = Mock(return_value={
                    'gpt_calls': 1,
                    'total_cost_usd': 0.05
                })

                return processor

    def test_llm_called_before_rules(self, processor):
        """Test that LLM analysis happens BEFORE rule engine"""
        # Track call order
        call_order = []

        def track_llm_call(*args, **kwargs):
            call_order.append('llm')
            return []

        def track_rule_call(*args, **kwargs):
            call_order.append('rule')
            return []

        processor.llm_orchestrator.analyze = Mock(side_effect=track_llm_call)
        processor.rule_engine.apply_rules = Mock(side_effect=track_rule_call)

        # Mock document parsing
        mock_doc = Mock()
        mock_indexer = Mock()
        mock_indexer.working_text = "sample text for testing"

        with patch('app.workers.document_worker.Document', return_value=mock_doc):
            with patch('app.workers.document_worker.WorkingTextIndexer', return_value=mock_indexer):
                with patch('app.workers.document_worker.RedlineValidator.validate_all', return_value=[]):
                    with patch('app.workers.document_worker.TrackChangesEngine'):
                        async def mock_generate(*args, **kwargs):
                            return Path("/fake/path.docx")

                        with patch.object(processor, '_generate_redlined_doc', side_effect=mock_generate):
                            # Run the processor
                            asyncio.run(processor.process_document(
                                job_id='test_job',
                                file_path='test.docx',
                                status_callback=None
                            ))

        # Verify order: LLM should be called BEFORE rules
        assert call_order == ['llm', 'rule'], f"Expected ['llm', 'rule'], got {call_order}"

    def test_llm_receives_empty_handled_spans(self, processor):
        """Test that LLM receives empty handled_spans list (no pre-filtering)"""
        processor.llm_orchestrator.analyze = Mock(return_value=[])
        processor.rule_engine.apply_rules = Mock(return_value=[])

        mock_doc = Mock()
        mock_indexer = Mock()
        mock_indexer.working_text = "sample text for testing"

        with patch('app.workers.document_worker.Document', return_value=mock_doc):
            with patch('app.workers.document_worker.WorkingTextIndexer', return_value=mock_indexer):
                with patch('app.workers.document_worker.RedlineValidator.validate_all', return_value=[]):
                    with patch('app.workers.document_worker.TrackChangesEngine'):
                        async def mock_generate(*args, **kwargs):
                            return Path("/fake/path.docx")

                        with patch.object(processor, '_generate_redlined_doc', side_effect=mock_generate):
                            asyncio.run(processor.process_document(
                                job_id='test_job',
                                file_path='test.docx',
                                status_callback=None
                            ))

        # Verify LLM was called with empty handled_spans
        call_args = processor.llm_orchestrator.analyze.call_args
        assert call_args is not None
        assert call_args[0][1] == [], f"Expected empty handled_spans, got {call_args[0][1]}"


class TestRedlineComparison:
    """Test redline comparison and merging logic"""

    @pytest.fixture
    def processor(self):
        """Create processor instance"""
        with patch('app.workers.document_worker.RuleEngine'):
            with patch('app.workers.document_worker.LLMOrchestrator'):
                return DocumentProcessor()

    def test_both_found_same_position(self, processor):
        """Test when both LLM and rules find the same issue"""
        llm_redlines = [
            {
                'start': 10,
                'end': 20,
                'original_text': 'two years',
                'revised_text': 'eighteen months',
                'source': 'llm',
                'explanation': 'LLM suggests 18 months'
            }
        ]

        rule_redlines = [
            {
                'start': 10,
                'end': 20,
                'original_text': 'two years',
                'revised_text': 'eighteen months',
                'source': 'rule',
                'explanation': 'Rule requires 18 months'
            }
        ]

        combined, stats = processor._compare_and_combine_redlines(
            llm_redlines, rule_redlines, "sample text"
        )

        # Should have 1 merged redline
        assert len(combined) == 1
        assert stats['both_found'] == 1
        assert stats['llm_only'] == 0
        assert stats['rule_only'] == 0

        # Check merged redline properties
        merged = combined[0]
        assert merged['source'] == 'both'
        assert merged['agreement'] == True
        assert merged['confidence'] == 100
        assert 'VERIFIED BY BOTH LLM AND RULES' in merged['explanation']

    def test_llm_only_redline(self, processor):
        """Test redline found only by LLM"""
        llm_redlines = [
            {
                'start': 10,
                'end': 20,
                'original_text': 'unusual clause',
                'revised_text': 'better clause',
                'source': 'llm',
                'explanation': 'LLM found this'
            }
        ]

        rule_redlines = []

        combined, stats = processor._compare_and_combine_redlines(
            llm_redlines, rule_redlines, "sample text"
        )

        assert len(combined) == 1
        assert stats['llm_only'] == 1
        assert stats['both_found'] == 0
        assert stats['rule_only'] == 0

        redline = combined[0]
        assert redline['source'] == 'llm'
        assert redline['agreement'] == False

    def test_rule_only_redline(self, processor):
        """Test redline found only by rules"""
        llm_redlines = []

        rule_redlines = [
            {
                'start': 10,
                'end': 20,
                'original_text': 'pattern match',
                'revised_text': 'fixed pattern',
                'source': 'rule',
                'explanation': 'Rule caught this'
            }
        ]

        combined, stats = processor._compare_and_combine_redlines(
            llm_redlines, rule_redlines, "sample text"
        )

        assert len(combined) == 1
        assert stats['rule_only'] == 1
        assert stats['both_found'] == 0
        assert stats['llm_only'] == 0

        redline = combined[0]
        assert redline['source'] == 'rule'
        assert redline['agreement'] == False

    def test_multiple_redlines_mixed(self, processor):
        """Test mix of LLM-only, rule-only, and both"""
        llm_redlines = [
            {'start': 10, 'end': 20, 'original_text': 'a', 'revised_text': 'b', 'source': 'llm', 'explanation': '1'},
            {'start': 30, 'end': 40, 'original_text': 'c', 'revised_text': 'd', 'source': 'llm', 'explanation': '2'},
        ]

        rule_redlines = [
            {'start': 10, 'end': 20, 'original_text': 'a', 'revised_text': 'b', 'source': 'rule', 'explanation': '1'},
            {'start': 50, 'end': 60, 'original_text': 'e', 'revised_text': 'f', 'source': 'rule', 'explanation': '3'},
        ]

        combined, stats = processor._compare_and_combine_redlines(
            llm_redlines, rule_redlines, "sample text"
        )

        # Should have 3 total: 1 both, 1 llm-only, 1 rule-only
        assert len(combined) == 3
        assert stats['both_found'] == 1
        assert stats['llm_only'] == 1
        assert stats['rule_only'] == 1

        # Verify sorting by position
        assert combined[0]['start'] == 10  # Both found
        assert combined[1]['start'] == 30  # LLM only
        assert combined[2]['start'] == 50  # Rule only

    def test_agreement_rate_calculation(self, processor):
        """Test agreement rate percentage calculation"""
        llm_redlines = [
            {'start': 10, 'end': 20, 'original_text': 'a', 'revised_text': 'b', 'source': 'llm', 'explanation': '1'},
            {'start': 30, 'end': 40, 'original_text': 'c', 'revised_text': 'd', 'source': 'llm', 'explanation': '2'},
        ]

        rule_redlines = [
            {'start': 10, 'end': 20, 'original_text': 'a', 'revised_text': 'b', 'source': 'rule', 'explanation': '1'},
        ]

        combined, stats = processor._compare_and_combine_redlines(
            llm_redlines, rule_redlines, "sample text"
        )

        # 1 both out of 2 total = 50%
        expected_rate = (1 / 2) * 100

        # Check in result structure (simulating what process_document does)
        agreement_rate = (stats['both_found'] / stats['total'] * 100 if stats['total'] > 0 else 0)
        assert agreement_rate == expected_rate


class TestFileSanitization:
    """Test enhanced filename sanitization"""

    def test_windows_reserved_names(self):
        """Test that Windows reserved names are handled"""
        from app.main import sanitize_filename

        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'LPT1']

        for name in reserved_names:
            # Test with and without extension
            result1 = sanitize_filename(f"{name}.docx")
            result2 = sanitize_filename(f"{name}")

            # Should be prefixed with "safe_"
            assert result1.startswith("safe_"), f"Expected {name}.docx to be prefixed, got {result1}"
            assert result2.startswith("safe_"), f"Expected {name} to be prefixed, got {result2}"

    def test_normal_filenames_unchanged(self):
        """Test that normal filenames are not modified unnecessarily"""
        from app.main import sanitize_filename

        normal_names = ['document.docx', 'NDA_2024.docx', 'contract-final.docx']

        for name in normal_names:
            result = sanitize_filename(name)
            # Should be unchanged (just cleaned)
            assert result == name, f"Expected {name} unchanged, got {result}"

    def test_unsafe_characters_removed(self):
        """Test that unsafe characters are replaced"""
        from app.main import sanitize_filename

        unsafe = 'file<>:"|?*\\.docx'
        result = sanitize_filename(unsafe)

        # All unsafe chars should be replaced with underscore
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '"' not in result
        assert '|' not in result
        assert '?' not in result
        assert '*' not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
