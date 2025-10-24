#!/usr/bin/env python3
"""
Test script to verify pattern matching fixes
"""
import requests
import json

# Test with common NDA phrases that should trigger redlines
TEST_TEXTS = [
    {
        "name": "Term Limit Test",
        "text": "This Agreement shall remain in effect for a period of two (2) years from the date hereof.",
        "expected_matches": ["term_limit_specific_years_to_18mo"]
    },
    {
        "name": "Governing Law Test",
        "text": "This Agreement shall be governed by the laws of the State of Texas.",
        "expected_matches": ["governing_law_change_delaware", "governing_law_any_state"]
    },
    {
        "name": "Duration Test",
        "text": "The confidentiality obligations shall survive for 24 months after termination.",
        "expected_matches": ["term_limit_specific_years_to_18mo"]
    },
    {
        "name": "Complex Term Test",
        "text": "This Agreement shall continue for a period of three years from the effective date.",
        "expected_matches": ["term_limit_any_years_to_18mo"]
    },
    {
        "name": "Entity Test",
        "text": "The Funds agrees to maintain the confidentiality of all information.",
        "expected_matches": ["entity_name_generic_to_edgewater"]
    }
]

def test_local_patterns():
    """Test patterns locally without API"""
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from app.core.rule_engine import RuleEngine

    print("=" * 60)
    print("LOCAL PATTERN TESTING")
    print("=" * 60)

    # Initialize rule engine
    rule_engine = RuleEngine()
    print(f"Loaded {len(rule_engine.rules)} rules\n")

    # Test each sample text
    for test_case in TEST_TEXTS:
        print(f"Test: {test_case['name']}")
        print(f"Text: {test_case['text']}")

        # Apply rules
        redlines = rule_engine.apply_rules(test_case['text'])

        print(f"Found {len(redlines)} redlines:")
        for redline in redlines:
            print(f"  - {redline['rule_id']}: '{redline['original_text']}' -> '{redline['revised_text']}'")

        # Check if expected matches were found
        found_rules = [r['rule_id'] for r in redlines]
        for expected in test_case['expected_matches']:
            if expected in found_rules:
                print(f"  [FOUND] Expected rule: {expected}")
            else:
                print(f"  [MISSING] Expected rule: {expected}")

        print("-" * 40)

    print("\n" + "=" * 60)
    print("PATTERN COVERAGE SUMMARY")
    print("=" * 60)

    # Check which patterns matched at least once
    all_matched_rules = set()
    for test_case in TEST_TEXTS:
        redlines = rule_engine.apply_rules(test_case['text'])
        all_matched_rules.update(r['rule_id'] for r in redlines)

    print(f"Total rules: {len(rule_engine.rules)}")
    print(f"Rules that matched: {len(all_matched_rules)}")
    print(f"Coverage: {len(all_matched_rules) / len(rule_engine.rules) * 100:.1f}%")

    print("\nCritical patterns status:")
    critical_patterns = [
        "term_limit_specific_years_to_18mo",
        "term_limit_any_years_to_18mo",
        "governing_law_change_delaware",
        "governing_law_any_state",
        "entity_name_generic_to_edgewater"
    ]

    for pattern in critical_patterns:
        status = "[WORKING]" if pattern in all_matched_rules else "[NOT MATCHING]"
        print(f"  {pattern}: {status}")

def test_api_patterns():
    """Test patterns via API endpoint"""
    print("\n" + "=" * 60)
    print("API PATTERN TESTING")
    print("=" * 60)

    base_url = "http://localhost:8000"

    try:
        # Test the pattern endpoint
        for test_case in TEST_TEXTS[:2]:  # Test first 2 cases via API
            response = requests.post(
                f"{base_url}/api/test/patterns",
                json={"sample_text": test_case['text']}
            )

            if response.status_code == 200:
                result = response.json()
                print(f"\nTest: {test_case['name']}")
                print(f"Redlines found: {result['redlines_found']}")
                print(f"Total rules tested: {result['total_rules']}")
            else:
                print(f"API error: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("API not running - skipping API tests")

if __name__ == "__main__":
    # Test locally
    test_local_patterns()

    # Optionally test via API
    # test_api_patterns()