"""
Tests for All-Claude LLM Orchestrator
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import os


@pytest.mark.asyncio
async def test_all_claude_orchestrator_initialization():
    """Test that AllClaudeLLMOrchestrator initializes correctly"""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'}):
        from backend.app.core.llm_orchestrator import AllClaudeLLMOrchestrator

        orchestrator = AllClaudeLLMOrchestrator()

        # Verify configuration
        assert orchestrator.validation_rate == 1.0, "Should validate 100% of suggestions"
        assert orchestrator.enable_validation == True
        assert 'opus' in orchestrator.opus_model.lower() and 'claude' in orchestrator.opus_model.lower()
        assert 'sonnet' in orchestrator.sonnet_model.lower() and 'claude' in orchestrator.sonnet_model.lower()


@pytest.mark.asyncio
async def test_all_claude_orchestrator_analyze():
    """Test All-Claude orchestrator analyze method"""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'}):
        from backend.app.core.llm_orchestrator import AllClaudeLLMOrchestrator

        orchestrator = AllClaudeLLMOrchestrator()

        # Mock Claude client
        orchestrator.client = Mock()
        orchestrator.client.messages.create = AsyncMock()

        # Test data
        test_text = "This agreement shall remain in effect in perpetuity."
        test_rules = []

        # Mock Opus response
        opus_response = Mock()
        opus_response.content = [Mock(
            text='{"redlines": [{"start": 0, "end": 50, "original_text": "in perpetuity", "revised_text": "for eighteen (18) months", "confidence": 85, "clause_type": "term_limit", "severity": "critical", "explanation": "Term must be limited to 18 months"}]}'
        )]
        opus_response.usage = Mock(input_tokens=100, output_tokens=50)

        # Mock Sonnet validation response
        sonnet_response = Mock()
        sonnet_response.content = [Mock(
            text='{"is_valid": true, "adjusted_confidence": 95, "revised_text": "for eighteen (18) months", "reasoning": "Correct term limit"}'
        )]
        sonnet_response.usage = Mock(input_tokens=50, output_tokens=30)

        # Set side effects for both calls (Opus then Sonnet)
        orchestrator.client.messages.create.side_effect = [opus_response, sonnet_response]

        # Run analysis
        result = await orchestrator.analyze(test_text, test_rules)

        # Verify Claude was called twice (Opus + Sonnet)
        assert orchestrator.client.messages.create.call_count == 2

        # Verify Opus was called with correct model
        opus_call = orchestrator.client.messages.create.call_args_list[0]
        assert orchestrator.opus_model in str(opus_call)

        # Verify Sonnet was called with correct model
        sonnet_call = orchestrator.client.messages.create.call_args_list[1]
        assert orchestrator.sonnet_model in str(sonnet_call)

        # Verify result contains validated redline
        assert len(result) == 1
        assert result[0]['source'] == 'llm'
        # Verify validation was done by the configured Sonnet model
        assert 'claude-sonnet' in result[0].get('validated_by', '').lower()
        assert result[0]['confidence'] == 95


@pytest.mark.asyncio
async def test_all_claude_orchestrator_stats():
    """Test that orchestrator tracks stats correctly"""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'}):
        from backend.app.core.llm_orchestrator import AllClaudeLLMOrchestrator

        orchestrator = AllClaudeLLMOrchestrator()

        # Mock Claude client
        orchestrator.client = Mock()
        orchestrator.client.messages.create = AsyncMock()

        # Mock responses
        opus_response = Mock()
        opus_response.content = [Mock(text='{"redlines": []}')]
        opus_response.usage = Mock(input_tokens=100, output_tokens=50)

        orchestrator.client.messages.create.return_value = opus_response

        # Run analysis
        await orchestrator.analyze("test text", [])

        # Verify stats
        stats = orchestrator.get_stats()
        assert stats['opus_calls'] == 1
        assert stats['validation_rate'] == 1.0
        assert 'opus_model' in stats
        assert 'sonnet_model' in stats
        assert stats['total_llm_calls'] >= 1


@pytest.mark.asyncio
async def test_all_claude_orchestrator_merge_redlines():
    """Test that orchestrator merges LLM and rule redlines correctly"""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'}):
        from backend.app.core.llm_orchestrator import AllClaudeLLMOrchestrator

        orchestrator = AllClaudeLLMOrchestrator()

        # Mock Claude client to return empty redlines
        orchestrator.client = Mock()
        orchestrator.client.messages.create = AsyncMock()

        opus_response = Mock()
        opus_response.content = [Mock(text='{"redlines": []}')]
        opus_response.usage = Mock(input_tokens=100, output_tokens=50)

        orchestrator.client.messages.create.return_value = opus_response

        # Test data with rule redlines
        rule_redlines = [
            {
                'start': 0,
                'end': 10,
                'original_text': 'test',
                'revised_text': 'changed',
                'clause_type': 'test_rule'
            }
        ]

        # Run analysis
        result = await orchestrator.analyze("test text here", rule_redlines)

        # Verify rule redlines are included
        assert len(result) >= 1

        # Find the rule redline in results
        rule_result = next((r for r in result if r.get('clause_type') == 'test_rule'), None)
        assert rule_result is not None
        assert rule_result['source'] == 'rule'
        assert rule_result['confidence'] == 100


@pytest.mark.asyncio
async def test_all_claude_orchestrator_100_percent_validation():
    """Test that orchestrator validates 100% of suggestions"""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'}):
        from backend.app.core.llm_orchestrator import AllClaudeLLMOrchestrator

        orchestrator = AllClaudeLLMOrchestrator()

        # Mock Claude client
        orchestrator.client = Mock()
        orchestrator.client.messages.create = AsyncMock()

        # Mock Opus to return 5 redlines
        opus_response = Mock()
        opus_response.content = [Mock(text='''{
            "redlines": [
                {"start": 0, "end": 10, "original_text": "test1", "revised_text": "change1", "confidence": 90, "clause_type": "type1", "severity": "high", "explanation": "reason1"},
                {"start": 11, "end": 20, "original_text": "test2", "revised_text": "change2", "confidence": 85, "clause_type": "type2", "severity": "high", "explanation": "reason2"},
                {"start": 21, "end": 30, "original_text": "test3", "revised_text": "change3", "confidence": 88, "clause_type": "type3", "severity": "high", "explanation": "reason3"},
                {"start": 31, "end": 40, "original_text": "test4", "revised_text": "change4", "confidence": 92, "clause_type": "type4", "severity": "high", "explanation": "reason4"},
                {"start": 41, "end": 50, "original_text": "test5", "revised_text": "change5", "confidence": 87, "clause_type": "type5", "severity": "high", "explanation": "reason5"}
            ]
        }''')]
        opus_response.usage = Mock(input_tokens=200, output_tokens=150)

        # Mock Sonnet to validate all 5
        sonnet_response = Mock()
        sonnet_response.content = [Mock(text='{"is_valid": true, "adjusted_confidence": 95, "revised_text": "validated", "reasoning": "looks good"}')]
        sonnet_response.usage = Mock(input_tokens=50, output_tokens=30)

        # Set up responses: 1 Opus call + 5 Sonnet validation calls
        orchestrator.client.messages.create.side_effect = [
            opus_response,
            sonnet_response,
            sonnet_response,
            sonnet_response,
            sonnet_response,
            sonnet_response
        ]

        # Run analysis
        result = await orchestrator.analyze("test text with many violations", [])

        # Verify all calls were made (1 Opus + 5 Sonnet)
        assert orchestrator.client.messages.create.call_count == 6

        # Verify stats show 100% validation
        stats = orchestrator.get_stats()
        assert stats['validated_redlines'] == 5  # All 5 redlines were validated
        assert stats['sonnet_calls'] == 5  # One Sonnet call per redline


def test_legacy_compatibility():
    """Test that LLMOrchestrator alias works for backward compatibility"""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key-123'}):
        from backend.app.core.llm_orchestrator import LLMOrchestrator, AllClaudeLLMOrchestrator

        # Verify the alias exists and points to the right class
        assert LLMOrchestrator is AllClaudeLLMOrchestrator


def test_missing_api_key():
    """Test that orchestrator raises error when API key is missing"""
    with patch.dict('os.environ', {}, clear=True):
        from backend.app.core.llm_orchestrator import AllClaudeLLMOrchestrator

        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            AllClaudeLLMOrchestrator()
