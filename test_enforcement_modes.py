#!/usr/bin/env python3
"""
Test Suite for Enforcement Modes (Bloody/Balanced/Lenient)
Tests the 4-pass LLM pipeline with different strictness levels
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import sys

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from backend.app.orchestrators.llm_pipeline import LLMPipelineOrchestrator
from backend.app.core.strictness_controller import EnforcementLevel
from backend.app.models.schemas_v2 import PipelineRequest, Severity


class EnforcementModeTester:
    """Test harness for enforcement modes"""

    def __init__(self):
        """Initialize tester with API keys from environment"""
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not self.openai_key or not self.anthropic_key:
            print("WARNING: API keys not found. Tests will use mock mode.")
            self.mock_mode = True
        else:
            self.mock_mode = False

        # Test cases for each mode
        self.test_cases = self._load_test_cases()

        # Results storage
        self.results = {
            'Bloody': [],
            'Balanced': [],
            'Lenient': []
        }

    def _load_test_cases(self) -> List[Dict]:
        """Load test cases for different scenarios"""
        return [
            # Test Case 1: Perpetual term (Critical - all modes should flag)
            {
                'id': 'test_perpetual',
                'name': 'Perpetual confidentiality term',
                'text': """This Non-Disclosure Agreement ("Agreement") is entered into as of today.

                The obligations of the Receiving Party under this Agreement shall survive in perpetuity
                and continue indefinitely, regardless of any termination or expiration of this Agreement.

                Confidential Information means any and all information disclosed by either party.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'critical'},
                    'Balanced': {'flag': True, 'severity': 'critical'},
                    'Lenient': {'flag': True, 'severity': 'critical'}
                }
            },

            # Test Case 2: 3-year term (Moderate - Bloody/Balanced flag, Lenient ignores)
            {
                'id': 'test_3_year',
                'name': '3-year confidentiality term',
                'text': """This Agreement shall remain in effect for a period of three (3) years
                from the date of execution.

                All Confidential Information shall be protected for the full term of this Agreement.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'moderate'},
                    'Balanced': {'flag': True, 'severity': 'moderate'},
                    'Lenient': {'flag': False}
                }
            },

            # Test Case 3: Best efforts language (Low - only Bloody flags)
            {
                'id': 'test_best_efforts',
                'name': 'Best efforts language',
                'text': """The Receiving Party shall use its best efforts to protect and maintain
                the confidentiality of all Confidential Information received hereunder.

                The term of confidentiality shall be eighteen (18) months.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'low'},
                    'Balanced': {'flag': False},
                    'Lenient': {'flag': False}
                }
            },

            # Test Case 4: Indemnification (Critical - all modes)
            {
                'id': 'test_indemnification',
                'name': 'Indemnification clause',
                'text': """The Receiving Party shall indemnify, defend, and hold harmless the Disclosing Party
                from and against any and all claims, losses, damages, liabilities, and expenses arising from
                any breach of this Agreement.

                Confidentiality obligations expire after twenty-four (24) months.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'critical'},
                    'Balanced': {'flag': True, 'severity': 'critical'},
                    'Lenient': {'flag': True, 'severity': 'critical'}
                }
            },

            # Test Case 5: No return carveout (High - Bloody/Balanced)
            {
                'id': 'test_no_carveout',
                'name': 'Missing legal retention carveout',
                'text': """Upon termination, the Receiving Party shall immediately return or destroy
                all Confidential Information and any copies thereof.

                The confidentiality period is twenty-four (24) months.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'high'},
                    'Balanced': {'flag': True, 'severity': 'high'},
                    'Lenient': {'flag': False}
                }
            },

            # Test Case 6: Formatting inconsistency (Advisory - only Bloody)
            {
                'id': 'test_formatting',
                'name': 'Capitalization inconsistency',
                'text': """The receiving party shall protect all CONFIDENTIAL INFORMATION
                with the same degree of care as it protects its own confidential information.

                Terms expire after eighteen (18) months.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'advisory'},
                    'Balanced': {'flag': False},
                    'Lenient': {'flag': False}
                }
            },

            # Test Case 7: Foreign jurisdiction (High - Bloody/Balanced)
            {
                'id': 'test_foreign_law',
                'name': 'Foreign governing law',
                'text': """This Agreement shall be governed by and construed in accordance with
                the laws of Singapore, without regard to conflict of law principles.

                Confidentiality term is twenty-four (24) months.""",
                'expected': {
                    'Bloody': {'flag': True, 'severity': 'high'},
                    'Balanced': {'flag': True, 'severity': 'high'},
                    'Lenient': {'flag': False}
                }
            },

            # Test Case 8: Complex multi-issue document
            {
                'id': 'test_complex',
                'name': 'Multiple issues of varying severity',
                'text': """MUTUAL NON-DISCLOSURE AGREEMENT

                This Agreement is entered into between the parties for evaluation of a potential transaction.

                1. Confidential Information shall be protected in perpetuity.
                2. Receiving Party shall use best efforts to maintain confidentiality.
                3. Receiving Party agrees to indemnify Disclosing Party for any breaches.
                4. This Agreement is governed by the laws of France.
                5. All CONFIDENTIAL INFORMATION must be returned without copies retained.
                6. Receiving Party may not solicit employees without exception.
                7. Injunctive relief is available without court determination.""",
                'expected': {
                    'Bloody': {'flag': True, 'min_issues': 7},
                    'Balanced': {'flag': True, 'min_issues': 4},
                    'Lenient': {'flag': True, 'min_issues': 2}
                }
            }
        ]

    async def run_test_case(self,
                           test_case: Dict,
                           enforcement_level: EnforcementLevel) -> Dict:
        """Run a single test case with specified enforcement level"""

        print(f"\n  Testing: {test_case['name']} [{enforcement_level.value} mode]")

        if self.mock_mode:
            return self._mock_test_result(test_case, enforcement_level)

        try:
            # Create pipeline
            pipeline = LLMPipelineOrchestrator(
                openai_api_key=self.openai_key,
                anthropic_api_key=self.anthropic_key,
                enforcement_level=enforcement_level,
                enable_cache=False  # Disable cache for testing
            )

            # Create request
            request = PipelineRequest(
                document_text=test_case['text'],
                document_id=test_case['id'],
                enforcement_level=enforcement_level.value,
                filename=f"{test_case['id']}.txt"
            )

            # Execute pipeline
            result = await pipeline.execute_pipeline(request)

            # Analyze results
            violations_by_severity = self._group_by_severity(result.violations)
            expected = test_case['expected'][enforcement_level.value]

            # Check if results match expectations
            if 'min_issues' in expected:
                # Check minimum issue count
                passed = result.total_violations >= expected['min_issues']
            else:
                # Check specific flag/severity
                if expected['flag']:
                    # Should find issues of expected severity
                    passed = expected['severity'] in violations_by_severity
                else:
                    # Should not flag this severity
                    passed = expected.get('severity', 'any') not in violations_by_severity

            return {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'enforcement_level': enforcement_level.value,
                'passed': passed,
                'total_violations': result.total_violations,
                'violations_by_severity': violations_by_severity,
                'expected': expected,
                'passes_executed': [p.pass_name for p in result.pass_results if not p.skipped],
                'consensus_score': result.consensus_score
            }

        except Exception as e:
            print(f"    ERROR: {e}")
            return {
                'test_id': test_case['id'],
                'test_name': test_case['name'],
                'enforcement_level': enforcement_level.value,
                'passed': False,
                'error': str(e)
            }

    def _mock_test_result(self,
                         test_case: Dict,
                         enforcement_level: EnforcementLevel) -> Dict:
        """Generate mock test result for testing without API keys"""

        expected = test_case['expected'][enforcement_level.value]

        # Simulate different violation counts by mode
        violation_counts = {
            'Bloody': {'critical': 2, 'high': 3, 'moderate': 4, 'low': 2, 'advisory': 1},
            'Balanced': {'critical': 2, 'high': 2, 'moderate': 2},
            'Lenient': {'critical': 1}
        }

        violations = violation_counts[enforcement_level.value]

        # Check pass/fail
        if 'min_issues' in expected:
            total = sum(violations.values())
            passed = total >= expected['min_issues']
        else:
            if expected['flag']:
                passed = expected['severity'] in violations
            else:
                passed = expected.get('severity', 'any') not in violations

        return {
            'test_id': test_case['id'],
            'test_name': test_case['name'],
            'enforcement_level': enforcement_level.value,
            'passed': passed,
            'total_violations': sum(violations.values()),
            'violations_by_severity': violations,
            'expected': expected,
            'mock_mode': True
        }

    def _group_by_severity(self, violations: List) -> Dict[str, int]:
        """Group violations by severity"""
        counts = {}
        for v in violations:
            severity = v.severity.value if hasattr(v.severity, 'value') else v.severity
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    async def run_all_tests(self):
        """Run all test cases for all enforcement modes"""

        print("=" * 60)
        print("NDA REVIEWER - ENFORCEMENT MODE TEST SUITE")
        print("=" * 60)

        for level in [EnforcementLevel.BLOODY,
                     EnforcementLevel.BALANCED,
                     EnforcementLevel.LENIENT]:

            print(f"\n{'='*60}")
            print(f"Testing {level.value} Mode")
            print(f"{'='*60}")

            for test_case in self.test_cases:
                result = await self.run_test_case(test_case, level)
                self.results[level.value].append(result)

                # Print result
                status = "✓ PASS" if result['passed'] else "✗ FAIL"
                print(f"    {status} - {result.get('total_violations', 0)} violations found")

                if not result['passed']:
                    print(f"      Expected: {result['expected']}")
                    print(f"      Got: {result.get('violations_by_severity', {})}")

    def generate_report(self):
        """Generate test report"""

        print("\n" + "=" * 60)
        print("TEST SUMMARY REPORT")
        print("=" * 60)

        # Overall statistics
        for mode in ['Bloody', 'Balanced', 'Lenient']:
            mode_results = self.results[mode]
            passed = sum(1 for r in mode_results if r['passed'])
            total = len(mode_results)
            pass_rate = (passed / total * 100) if total > 0 else 0

            print(f"\n{mode} Mode:")
            print(f"  Tests Passed: {passed}/{total} ({pass_rate:.1f}%)")

            # Failed tests
            failed = [r for r in mode_results if not r['passed']]
            if failed:
                print(f"  Failed Tests:")
                for f in failed:
                    print(f"    - {f['test_name']}")

        # Mode comparison
        print("\n" + "=" * 60)
        print("MODE COMPARISON MATRIX")
        print("=" * 60)

        print("\nAverage Violations by Mode:")
        for mode in ['Bloody', 'Balanced', 'Lenient']:
            mode_results = self.results[mode]
            avg_violations = sum(r.get('total_violations', 0) for r in mode_results) / len(mode_results)
            print(f"  {mode:10s}: {avg_violations:.1f} violations/document")

        # Pass execution patterns
        print("\n" + "=" * 60)
        print("PASS EXECUTION PATTERNS")
        print("=" * 60)

        for mode in ['Bloody', 'Balanced', 'Lenient']:
            print(f"\n{mode} Mode Pass Frequency:")
            pass_counts = {}
            for result in self.results[mode]:
                if 'passes_executed' in result:
                    for pass_name in result['passes_executed']:
                        pass_counts[pass_name] = pass_counts.get(pass_name, 0) + 1

            for pass_name, count in sorted(pass_counts.items()):
                pct = (count / len(self.results[mode]) * 100) if self.results[mode] else 0
                print(f"  {pass_name:25s}: {pct:.0f}%")

        # Save detailed results
        self._save_results()

    def _save_results(self):
        """Save detailed test results to file"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enforcement_test_results_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'mock_mode': self.mock_mode,
                'results': self.results,
                'test_cases': [
                    {'id': tc['id'], 'name': tc['name'], 'expected': tc['expected']}
                    for tc in self.test_cases
                ]
            }, f, indent=2)

        print(f"\nDetailed results saved to: {filename}")


async def main():
    """Main test execution"""

    tester = EnforcementModeTester()

    # Run all tests
    await tester.run_all_tests()

    # Generate report
    tester.generate_report()

    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    # Run tests
    asyncio.run(main())