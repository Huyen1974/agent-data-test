#!/usr/bin/env python3
"""Runner script to execute all Lark token generator tests."""

import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

TEST_SCRIPTS = [
    "test_get_secret.py",
    "test_generate_token.py",
    "test_save_token.py",
    "test_cleanup.py",
]


def run_test_script(script_name: str) -> tuple[str, int, str]:
    """Run a single test script and return (name, exit_code, output)."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        return script_name, result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return script_name, -1, "TIMEOUT: Script took longer than 5 minutes"
    except Exception as e:
        return script_name, -2, f"ERROR: {e}"


def print_test_result(script_name: str, exit_code: int, output: str):
    """Print formatted test result."""
    print(f"\n{'='*60}")
    print(f"TEST: {script_name}")
    print("=" * 60)

    if exit_code == 0:
        print("✅ RESULT: PASS")
    elif exit_code == 1:
        print("❌ RESULT: FAIL")
    elif exit_code == -1:
        print("⏰ RESULT: TIMEOUT")
    elif exit_code == -2:
        print("💥 RESULT: ERROR")
    else:
        print(f"❓ RESULT: UNKNOWN (exit code: {exit_code})")

    print("\n--- OUTPUT ---")
    if output.strip():
        print(output)
    else:
        print("(No output)")
    print("-" * 60)


def main():
    """Main function to run all tests and report results."""
    print("🚀 Starting Lark Token Generator Test Suite")
    print("=" * 60)

    test_results = []

    for script_name in TEST_SCRIPTS:
        if not os.path.exists(os.path.join(os.path.dirname(__file__), script_name)):
            print(f"❌ ERROR: Test script {script_name} not found!")
            continue

        script_name, exit_code, output = run_test_script(script_name)
        test_results.append((script_name, exit_code, output))
        print_test_result(script_name, exit_code, output)

    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)

    total_tests = len(test_results)
    passed_tests = sum(1 for _, code, _ in test_results if code == 0)
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")

    print("\n📋 DETAILED RESULTS:")
    for script_name, exit_code, _ in test_results:
        status = "✅ PASS" if exit_code == 0 else "❌ FAIL"
        print(f"  - {script_name}: {status}")

    print("\n" + "=" * 60)

    if failed_tests == 0:
        print("🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print(f"⚠️  {failed_tests} TEST(S) FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
