#!/usr/bin/env python3
"""
Test Redline Quality with Different Settings
Run this to test your NDA redline quality with various configurations
"""

import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, List

# Configuration
BACKEND_URL = "https://nda-redline-tool-production.up.railway.app"  # Update with your URL
TEST_NDA_PATH = "test_nda.docx"  # Path to your test NDA

class RedlineQualityTester:
    """Test redline quality with different settings"""

    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip('/')
        self.results = []

    def upload_document(self, file_path: str) -> str:
        """Upload a document and return job_id"""
        with open(file_path, 'rb') as f:
            files = {'file': ('test_nda.docx', f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
            response = requests.post(f"{self.backend_url}/api/upload", files=files)

        if response.status_code == 200:
            return response.json()['job_id']
        else:
            raise Exception(f"Upload failed: {response.text}")

    def wait_for_completion(self, job_id: str, timeout: int = 60) -> Dict:
        """Wait for job to complete and return results"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = requests.get(f"{self.backend_url}/api/jobs/{job_id}/status")

            if response.status_code == 200:
                data = response.json()

                if data['status'] == 'COMPLETE':
                    return data
                elif data['status'] == 'ERROR':
                    raise Exception(f"Job failed: {data.get('error_message', 'Unknown error')}")

            time.time.sleep(2)

        raise Exception(f"Job timeout after {timeout} seconds")

    def analyze_results(self, results: Dict) -> Dict:
        """Analyze redline results for quality metrics"""
        redlines = results.get('redlines', [])

        # Categorize redlines
        critical = [r for r in redlines if r.get('severity') == 'critical']
        high = [r for r in redlines if r.get('severity') == 'high']
        moderate = [r for r in redlines if r.get('severity') == 'moderate']
        low = [r for r in redlines if r.get('severity') == 'low']

        # Calculate metrics
        metrics = {
            'total_redlines': len(redlines),
            'critical_count': len(critical),
            'high_count': len(high),
            'moderate_count': len(moderate),
            'low_count': len(low),
            'rule_based': results.get('rule_redlines', 0),
            'llm_suggested': results.get('llm_redlines', 0),
            'categories': {}
        }

        # Count by category
        for redline in redlines:
            category = redline.get('clause_type', 'unknown')
            metrics['categories'][category] = metrics['categories'].get(category, 0) + 1

        return metrics

    def print_analysis(self, metrics: Dict, test_name: str):
        """Print analysis results"""
        print(f"\n{'='*60}")
        print(f"Test: {test_name}")
        print(f"{'='*60}")
        print(f"Total Redlines: {metrics['total_redlines']}")
        print(f"  - Critical: {metrics['critical_count']}")
        print(f"  - High: {metrics['high_count']}")
        print(f"  - Moderate: {metrics['moderate_count']}")
        print(f"  - Low: {metrics['low_count']}")
        print(f"\nSource:")
        print(f"  - Rule-based: {metrics['rule_based']}")
        print(f"  - LLM suggested: {metrics['llm_suggested']}")
        print(f"\nCategories:")
        for category, count in sorted(metrics['categories'].items()):
            print(f"  - {category}: {count}")

    def generate_recommendations(self, metrics_list: List[Dict]):
        """Generate recommendations based on test results"""
        print(f"\n{'='*60}")
        print("RECOMMENDATIONS")
        print(f"{'='*60}")

        avg_total = sum(m['total_redlines'] for m in metrics_list) / len(metrics_list)

        if avg_total > 20:
            print("⚠️ OVER-REDLINING DETECTED")
            print("   - Too many redlines will slow down deals")
            print("   - Recommendation: Set ENFORCEMENT_LEVEL=Lenient in Railway")
            print("   - Consider increasing CONFIDENCE_THRESHOLD to 98")

        elif avg_total < 5:
            print("⚠️ UNDER-REDLINING DETECTED")
            print("   - May be missing important issues")
            print("   - Recommendation: Set ENFORCEMENT_LEVEL=Balanced")
            print("   - Consider decreasing CONFIDENCE_THRESHOLD to 90")

        else:
            print("✅ REDLINE VOLUME APPROPRIATE")
            print("   - Focus on improving relevance rather than quantity")

        # Check balance
        if metrics_list[0]['llm_suggested'] > metrics_list[0]['rule_based'] * 2:
            print("\n📊 LLM OVER-ACTIVE")
            print("   - LLM is suggesting many non-rule-based changes")
            print("   - May need prompt refinement to focus on material issues")

        # Most common categories
        all_categories = {}
        for m in metrics_list:
            for cat, count in m['categories'].items():
                all_categories[cat] = all_categories.get(cat, 0) + count

        print("\n🎯 MOST FLAGGED CATEGORIES:")
        for cat, count in sorted(all_categories.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {cat}: {count} times")

        print("\nConsider if these categories are actually important for your deals.")


def main():
    """Main test workflow"""
    print("NDA Redline Quality Tester")
    print("="*60)

    # Get test file
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        print("Usage: python test_redline_quality.py <path_to_test_nda.docx>")
        print("\nUsing default test file: test_nda.docx")
        test_file = "test_nda.docx"

    if not Path(test_file).exists():
        print(f"Error: Test file '{test_file}' not found!")
        print("\nPlease provide a test NDA document:")
        print("  python test_redline_quality.py /path/to/your/nda.docx")
        return 1

    # Initialize tester
    tester = RedlineQualityTester(BACKEND_URL)

    print(f"\nTesting with: {test_file}")
    print(f"Backend: {BACKEND_URL}")
    print("\nRunning quality tests...")

    # Test 1: Current settings
    print("\nTest 1: Analyzing with current settings...")
    try:
        job_id = tester.upload_document(test_file)
        print(f"  Job ID: {job_id}")
        print("  Waiting for completion...")
        results = tester.wait_for_completion(job_id)
        metrics = tester.analyze_results(results)
        tester.print_analysis(metrics, "Current Settings")
        tester.results.append(metrics)
    except Exception as e:
        print(f"  Error: {e}")
        return 1

    # Generate recommendations
    tester.generate_recommendations(tester.results)

    # Print improvement suggestions
    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print("1. Review the redlines in the web interface")
    print("2. Note which ones are actually useful vs noise")
    print("3. Adjust Railway environment variables:")
    print("   - ENFORCEMENT_LEVEL (Lenient/Balanced/Bloody)")
    print("   - CONFIDENCE_THRESHOLD (90-99)")
    print("   - VALIDATION_RATE (0.1-0.3)")
    print("\n4. Update prompts in master_prompt.py with your preferences")
    print("5. Add training examples from your successful deals")
    print("\n6. Re-run this test to measure improvement")

    return 0


if __name__ == "__main__":
    sys.exit(main())