#!/usr/bin/env python3
"""
Test runner for Citation Management Agent validation.
Executes comprehensive test suite and generates summary report.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_test_suite():
    """Run the complete test suite for Citation Management Agent."""

    print("🧪 Citation Management Agent - Test Suite Runner")
    print("=" * 60)

    # Change to the agent directory
    agent_dir = Path(__file__).parent.parent
    test_dir = Path(__file__).parent

    print(f"📁 Agent Directory: {agent_dir}")
    print(f"🧪 Test Directory: {test_dir}")
    print()

    # Test categories with their descriptions
    test_categories = [
        ("test_agent.py", "Core Agent Functionality"),
        ("test_tools.py", "Citation Tools & Functions"),
        ("test_integration.py", "Workflow Integration"),
        ("test_performance.py", "Performance & Scalability"),
        ("test_validation.py", "Requirements Validation")
    ]

    total_start_time = time.time()
    all_results = []

    for test_file, description in test_categories:
        print(f"🔄 Running {description}...")
        print(f"   Test File: {test_file}")

        start_time = time.time()

        # Run pytest for specific test file
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_dir / test_file),
            "-v",
            "--tb=short",
            "--disable-warnings"
        ],
        cwd=agent_dir,
        capture_output=True,
        text=True
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"   ✅ PASSED ({duration:.2f}s)")
            status = "PASSED"
        else:
            print(f"   ❌ FAILED ({duration:.2f}s)")
            print(f"   Error Output: {result.stderr}")
            status = "FAILED"

        all_results.append({
            "category": description,
            "file": test_file,
            "status": status,
            "duration": duration,
            "output": result.stdout,
            "error": result.stderr
        })

        print()

    total_duration = time.time() - total_start_time

    # Summary Report
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)

    passed_count = sum(1 for r in all_results if r["status"] == "PASSED")
    failed_count = sum(1 for r in all_results if r["status"] == "FAILED")

    print(f"📈 Overall Results:")
    print(f"   Total Categories: {len(all_results)}")
    print(f"   ✅ Passed: {passed_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   ⏱️  Total Duration: {total_duration:.2f}s")
    print()

    # Detailed Results
    print("📋 Detailed Results:")
    for result in all_results:
        status_icon = "✅" if result["status"] == "PASSED" else "❌"
        print(f"   {status_icon} {result['category']}: {result['status']} ({result['duration']:.2f}s)")

    print()

    # Overall Status
    if failed_count == 0:
        print("🎉 ALL TESTS PASSED - AGENT READY FOR PRODUCTION!")
        print("📄 See VALIDATION_REPORT.md for detailed validation results")
        return True
    else:
        print("⚠️  SOME TESTS FAILED - REVIEW REQUIRED")
        print("🔍 Check error outputs above for debugging information")
        return False


def run_quick_validation():
    """Run a quick validation subset for rapid feedback."""

    print("⚡ Citation Management Agent - Quick Validation")
    print("=" * 50)

    test_dir = Path(__file__).parent
    agent_dir = Path(__file__).parent.parent

    # Run subset of critical tests
    critical_tests = [
        "test_validation.py::TestGitHubIssueRequirements::test_req_multi_style_formatting",
        "test_validation.py::TestGitHubIssueRequirements::test_req_duplicate_detection_95_percent_accuracy",
        "test_validation.py::TestGitHubIssueRequirements::test_req_processing_speed_100_citations_1_minute",
        "test_agent.py::TestAgentBasicFunctionality::test_agent_basic_response"
    ]

    for test in critical_tests:
        print(f"🔄 Running {test.split('::')[-1]}...")

        result = subprocess.run([
            sys.executable, "-m", "pytest",
            str(test_dir / test.split("::")[0]) + "::" + "::".join(test.split("::")[1:]),
            "-v",
            "--tb=short",
            "--disable-warnings"
        ],
        cwd=agent_dir,
        capture_output=True,
        text=True
        )

        if result.returncode == 0:
            print(f"   ✅ PASSED")
        else:
            print(f"   ❌ FAILED")
            return False

    print()
    print("⚡ Quick validation completed successfully!")
    print("🚀 Run full test suite with: python run_tests.py --full")
    return True


def main():
    """Main test runner entry point."""

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        success = run_quick_validation()
    else:
        success = run_test_suite()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()