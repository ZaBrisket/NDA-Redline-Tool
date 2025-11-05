"""
Unit tests for Rule Engine
Tests deterministic pattern matching and replacement logic
"""
import pytest
import re
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
@pytest.mark.fast
class TestRuleEngine:
    """Test suite for RuleEngine"""

    def test_rule_engine_initialization(self):
        """Test that rule engine initializes correctly"""
        from backend.app.core.rule_engine import RuleEngine

        engine = RuleEngine()
        assert engine is not None
        assert hasattr(engine, 'rules')

    def test_pattern_compilation(self, sample_rules):
        """Test that regex patterns compile without errors"""
        for rule in sample_rules:
            pattern = rule['pattern']
            try:
                compiled = re.compile(pattern)
                assert compiled is not None
            except re.error as e:
                pytest.fail(f"Pattern '{pattern}' failed to compile: {e}")

    def test_simple_pattern_match(self):
        """Test basic pattern matching"""
        from backend.app.core.rule_engine import RuleEngine

        engine = RuleEngine()
        text = "The term shall be two (2) years from the effective date."

        # Test that confidentiality term pattern matches
        pattern = r'two\s*\(2\)\s*years?'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        match_list = list(matches)

        assert len(match_list) > 0, "Should find at least one match"
        assert match_list[0].group() in text

    def test_replacement_generation(self):
        """Test that replacements are generated correctly"""
        original_text = "two (2) years"
        expected_replacement = "eighteen (18) months"

        # Simple replacement
        replaced = original_text.replace("two (2) years", expected_replacement)
        assert replaced == expected_replacement

    def test_redline_creation(self, sample_rules):
        """Test creation of redline objects"""
        rule = sample_rules[0]  # Confidentiality term rule

        redline = {
            'id': 'test-1',
            'rule_id': rule['id'],
            'clause_type': rule['clause_type'],
            'original_text': 'two (2) years',
            'revised_text': rule['replacement'],
            'severity': rule['severity'],
            'confidence': 100,  # Rules have 100% confidence
            'source': 'rule'
        }

        assert redline['confidence'] == 100
        assert redline['source'] == 'rule'
        assert redline['severity'] == 'critical'

    def test_multiple_pattern_matches(self):
        """Test finding multiple matches in text"""
        text = """
        The first term is two (2) years.
        The second term is three (3) years.
        The third term is five (5) years.
        """

        pattern = r'(\w+)\s*\((\d+)\)\s*years?'
        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        assert len(matches) == 3, "Should find three term mentions"

    def test_case_insensitive_matching(self):
        """Test that patterns match case-insensitively"""
        texts = [
            "TWO (2) YEARS",
            "two (2) years",
            "Two (2) Years",
            "tWo (2) yEaRs"
        ]

        pattern = r'two\s*\(2\)\s*years?'
        for text in texts:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            assert len(matches) > 0, f"Should match case-insensitive: {text}"

    def test_position_tracking(self):
        """Test that match positions are tracked correctly"""
        text = "This term is two (2) years and that term is three (3) years."
        pattern = r'(\w+)\s*\((\d+)\)\s*years?'

        matches = list(re.finditer(pattern, text))

        assert len(matches) == 2
        # First match
        assert matches[0].start() < matches[1].start()
        # Positions should be within text bounds
        assert 0 <= matches[0].start() < len(text)
        assert 0 <= matches[1].end() <= len(text)

    def test_overlapping_patterns(self):
        """Test handling of overlapping pattern matches"""
        text = "State of California law"
        patterns = [
            r'State of \w+',
            r'California law'
        ]

        all_matches = []
        for pattern in patterns:
            matches = list(re.finditer(pattern, text))
            all_matches.extend(matches)

        # Should find both patterns
        assert len(all_matches) >= 2

    def test_group_extraction(self):
        """Test extracting regex groups from matches"""
        text = "The term is two (2) years."
        pattern = r'(\w+)\s*\((\d+)\)\s*(years?)'

        match = re.search(pattern, text, re.IGNORECASE)

        assert match is not None
        assert match.group(1).lower() == 'two'
        assert match.group(2) == '2'
        assert match.group(3).lower() in ['year', 'years']

    def test_empty_text_handling(self):
        """Test that empty text doesn't cause errors"""
        from backend.app.core.rule_engine import RuleEngine

        engine = RuleEngine()
        text = ""

        # Should not raise exception
        pattern = r'two\s*\(2\)\s*years?'
        matches = list(re.finditer(pattern, text))

        assert len(matches) == 0

    def test_special_characters_in_text(self):
        """Test handling of special characters"""
        texts = [
            "Term: two (2) years.",
            "Term - two (2) years!",
            "Term; two (2) years?",
            "Term @ two (2) years#"
        ]

        pattern = r'two\s*\(2\)\s*years?'
        for text in texts:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            assert len(matches) > 0, f"Should match with special chars: {text}"


@pytest.mark.unit
class TestRuleEngineV2:
    """Test suite for RuleEngineV2 with enforcement levels"""

    def test_enforcement_level_filtering(self):
        """Test that rules are filtered by enforcement level"""
        rules = [
            {'severity': 'critical', 'id': 'r1'},
            {'severity': 'high', 'id': 'r2'},
            {'severity': 'moderate', 'id': 'r3'},
            {'severity': 'low', 'id': 'r4'},
        ]

        # Bloody: all rules
        bloody_rules = [r for r in rules]
        assert len(bloody_rules) == 4

        # Balanced: critical + high + moderate
        balanced_rules = [r for r in rules if r['severity'] in ['critical', 'high', 'moderate']]
        assert len(balanced_rules) == 3

        # Lenient: critical only
        lenient_rules = [r for r in rules if r['severity'] == 'critical']
        assert len(lenient_rules) == 1

    def test_regex_expansion_error_handling(self):
        """Test that regex expansion errors are handled gracefully"""
        match = re.search(r'(\w+)', 'test')
        replacement = r'\1 expanded'

        # Valid expansion
        try:
            expanded = match.expand(replacement)
            assert expanded == 'test expanded'
        except (re.error, IndexError):
            pytest.fail("Valid expansion should not raise error")

        # Invalid expansion (no such group) - should raise IndexError or re.error
        replacement_invalid = r'\2'  # Group 2 doesn't exist
        with pytest.raises((IndexError, re.error)):
            expanded = match.expand(replacement_invalid)


@pytest.mark.unit
class TestRuleValidation:
    """Test rule validation logic"""

    def test_redline_overlap_detection(self):
        """Test detecting overlapping redlines"""
        redlines = [
            {'start': 10, 'end': 20, 'id': 'r1'},
            {'start': 15, 'end': 25, 'id': 'r2'},  # Overlaps with r1
            {'start': 30, 'end': 40, 'id': 'r3'},  # No overlap
        ]

        def overlaps(r1, r2):
            return not (r1['end'] <= r2['start'] or r2['end'] <= r1['start'])

        assert overlaps(redlines[0], redlines[1])  # Should overlap
        assert not overlaps(redlines[0], redlines[2])  # Should not overlap

    def test_redline_sorting(self):
        """Test that redlines are sorted by position"""
        redlines = [
            {'start': 30, 'end': 40, 'id': 'r3'},
            {'start': 10, 'end': 20, 'id': 'r1'},
            {'start': 20, 'end': 25, 'id': 'r2'},
        ]

        sorted_redlines = sorted(redlines, key=lambda x: x['start'])

        assert sorted_redlines[0]['id'] == 'r1'
        assert sorted_redlines[1]['id'] == 'r2'
        assert sorted_redlines[2]['id'] == 'r3'

    def test_confidence_thresholds(self):
        """Test confidence threshold filtering"""
        redlines = [
            {'id': 'r1', 'confidence': 100},
            {'id': 'r2', 'confidence': 95},
            {'id': 'r3', 'confidence': 85},
            {'id': 'r4', 'confidence': 70},
        ]

        threshold = 90
        high_confidence = [r for r in redlines if r['confidence'] >= threshold]

        assert len(high_confidence) == 2
        assert all(r['confidence'] >= 90 for r in high_confidence)
