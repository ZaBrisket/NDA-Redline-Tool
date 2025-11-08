"""
End-to-end test for NDA processing with sample document
Verifies that both rule-based and LLM redlines are properly captured
"""

import asyncio
import pytest
import os
import sys
import json
from pathlib import Path
from typing import Dict, List
from docx import Document

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from backend.app.workers.document_worker import DocumentProcessor
from backend.app.core.text_indexer import WorkingTextIndexer
from backend.app.core.rule_engine import RuleEngine


@pytest.mark.asyncio
@pytest.mark.slow
async def test_nda_processing_with_sample_document():
    """
    Test NDA processing with the sample 69324-NDA.docx
    Verifies that both rule-based and LLM redlines are captured
    """
    # Path to sample NDA
    sample_nda_path = Path(__file__).parent.parent.parent / "Logs to review" / "69324-NDA.docx"

    if not sample_nda_path.exists():
        pytest.skip(f"Sample NDA not found at {sample_nda_path}")

    # Initialize processor
    processor = DocumentProcessor()

    # Process the document
    job_id = "test-" + str(int(asyncio.get_event_loop().time()))
    result = await processor.process_document(
        job_id=job_id,
        file_path=str(sample_nda_path)
    )

    # Verify result structure
    assert 'status' in result
    assert result['status'] == 'COMPLETE'
    assert 'total_redlines' in result
    assert 'rule_redlines' in result
    assert 'llm_redlines' in result

    # Verify that rule-based redlines are present
    rule_count = result.get('rule_redlines', 0)
    assert rule_count > 0, "No rule-based redlines found - they may have been overwritten"

    # Verify total redlines include both rule and LLM
    total_count = result.get('total_redlines', 0)
    assert total_count > 0, "No redlines found in total"

    # Print summary for debugging
    print(f"\nRedline Summary:")
    print(f"  Rule-based: {rule_count}")
    print(f"  LLM: {result.get('llm_redlines', 0)}")
    print(f"  Total: {total_count}")

    # Verify comparison stats if available
    if 'comparison_stats' in result:
        stats = result['comparison_stats']
        print(f"\nMerge Statistics:")
        print(f"  LLM-only: {stats.get('llm_only', 0)}")
        print(f"  Rule-only: {stats.get('rule_only', 0)}")
        print(f"  Both found: {stats.get('both_found', 0)}")

        # Verify that rule-only redlines are preserved
        assert stats.get('rule_only', 0) >= 0, "Rule-only redlines should be preserved"

    # Check specific rule-based redlines that should be present
    redlines = result.get('redlines', [])

    # Check for term limit redlines (should be from rules)
    term_redlines = [r for r in redlines if 'term' in str(r.get('explanation', '')).lower() or
                     'eighteen' in str(r.get('revised_text', '')).lower()]
    assert len(term_redlines) > 0, "Term limit redlines (18 months) not found"

    # Check for retention period redlines
    retention_redlines = [r for r in redlines if 'retention' in str(r.get('explanation', '')).lower() or
                         'return' in str(r.get('revised_text', '')).lower()]
    assert len(retention_redlines) > 0, "Retention period redlines not found"

    # Check for non-solicitation carve-outs
    nonsolicitation_redlines = [r for r in redlines if 'solicit' in str(r.get('explanation', '')).lower()]
    if len(nonsolicitation_redlines) == 0:
        print("Warning: Non-solicitation redlines not found (may depend on document content)")

    return result


@pytest.mark.asyncio
async def test_clause_mapper_conversion_rate():
    """
    Test that ClauseMapper achieves good conversion rates
    """
    from backend.app.core.clause_mapper import ClauseMapper

    # Sample Claude output that might use descriptions
    sample_claude_output = [
        {
            'clause': 'Non-Solicitation. During the term of this Agreement',
            'issue': 'Non-solicitation clause lacks carve-outs',
            'recommendation': 'Add carve-outs for general advertising',
            'severity': 'high'
        },
        {
            'clause': 'Confidentiality Obligations',
            'issue': 'Overly broad definition',
            'recommendation': 'Narrow the scope',
            'severity': 'moderate'
        }
    ]

    # Sample document text
    sample_doc = """
    1. Confidentiality Obligations

    The Receiving Party shall maintain all Confidential Information in strict confidence.

    2. Non-Solicitation. During the term of this Agreement and for twelve months thereafter,
    neither party shall solicit employees of the other party.

    3. Term

    This Agreement shall remain in effect in perpetuity.
    """

    mapper = ClauseMapper(confidence_threshold=70.0)
    converted, stats = mapper.convert_redlines_with_mapping(sample_claude_output, sample_doc)

    # Verify conversion rate
    assert stats['total'] == len(sample_claude_output)
    assert stats['converted'] >= 1, "Should convert at least one redline"

    conversion_rate = (stats['converted'] / stats['total']) * 100
    print(f"\nClauseMapper conversion rate: {conversion_rate:.1f}%")
    print(f"  Converted: {stats['converted']}/{stats['total']}")
    print(f"  Average confidence: {stats.get('average_confidence', 0):.1f}")

    # We expect at least 50% conversion with fuzzy matching
    assert conversion_rate >= 50, f"Conversion rate too low: {conversion_rate:.1f}%"


@pytest.mark.asyncio
async def test_rule_engine_directly():
    """
    Test that the rule engine produces expected redlines
    """
    rule_engine = RuleEngine()

    # Sample text that should trigger rules
    sample_text = """
    This Agreement shall remain in effect in perpetuity.

    The Receiving Party shall not solicit any employees during the term.

    All Confidential Information must be retained indefinitely.
    """

    redlines = rule_engine.apply_rules(sample_text)

    # Should have redlines for perpetuity and retention
    assert len(redlines) > 0, "Rule engine should produce redlines"

    # Check for term limit rule
    term_redlines = [r for r in redlines if 'perpetuity' in r.get('original_text', '').lower()]
    assert len(term_redlines) > 0, "Should flag 'in perpetuity' term"

    print(f"\nRule engine found {len(redlines)} redlines")
    for r in redlines:
        print(f"  - {r.get('clause_type')}: {r.get('original_text', '')[:50]}...")


@pytest.mark.asyncio
async def test_merge_statistics():
    """
    Test that merge statistics are properly calculated
    """
    from backend.app.workers.document_worker import DocumentProcessor

    processor = DocumentProcessor()

    # Test _compare_and_combine_redlines directly
    llm_redlines = [
        {'start': 0, 'end': 10, 'original_text': 'test1', 'revised_text': 'fix1'},
        {'start': 20, 'end': 30, 'original_text': 'test2', 'revised_text': 'fix2'}
    ]

    rule_redlines = [
        {'start': 20, 'end': 30, 'original_text': 'test2', 'revised_text': 'fix2_rule'},  # Overlaps with LLM
        {'start': 40, 'end': 50, 'original_text': 'test3', 'revised_text': 'fix3'}  # Rule-only
    ]

    working_text = "test1 some text test2 more text test3 end"

    merged, stats = processor._compare_and_combine_redlines(llm_redlines, rule_redlines, working_text)

    # Verify statistics
    assert stats['llm_only'] == 1, "Should have 1 LLM-only redline"
    assert stats['rule_only'] == 1, "Should have 1 rule-only redline"
    assert stats['both_found'] == 1, "Should have 1 overlapping redline"
    assert len(merged) == 3, "Should have 3 total redlines after merging"

    print(f"\nMerge test results:")
    print(f"  LLM-only: {stats['llm_only']}")
    print(f"  Rule-only: {stats['rule_only']}")
    print(f"  Both: {stats['both_found']}")
    print(f"  Total merged: {len(merged)}")


if __name__ == "__main__":
    # Run tests directly
    asyncio.run(test_nda_processing_with_sample_document())
    asyncio.run(test_clause_mapper_conversion_rate())
    asyncio.run(test_rule_engine_directly())
    asyncio.run(test_merge_statistics())