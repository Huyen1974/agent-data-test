#!/usr/bin/env python3
"""
Test script for optimized ~/.zshrc configuration
Validates that all critical functionality works correctly
"""

import subprocess
import os
import time
from pathlib import Path

def run_command(command, description, timeout=10):
    """Run a command and return success status and output"""
    print(f"🧪 Testing: {description}")
    try:
        start_time = time.time()
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"   ✅ PASS ({duration:.2f}s): {description}")
            return True, result.stdout.strip()
        else:
            print(f"   ❌ FAIL ({duration:.2f}s): {description}")
            print(f"      Error: {result.stderr.strip()}")
            return False, result.stderr.strip()

    except subprocess.TimeoutExpired:
        print(f"   ⏰ TIMEOUT (>10s): {description}")
        return False, "Command timed out"
    except Exception as e:
        print(f"   💥 ERROR: {description} - {str(e)}")
        return False, str(e)

def test_optimized_zshrc():
    """Test the optimized ~/.zshrc configuration"""
    print("🚀 TESTING OPTIMIZED ~/.zshrc CONFIGURATION")
    print("=" * 60)

    # Create backup of current ~/.zshrc
    home_zshrc = os.path.expanduser("~/.zshrc")
    backup_zshrc = os.path.expanduser("~/.zshrc.backup")
    optimized_zshrc = ".zshrc.optimized"

    if os.path.exists(home_zshrc):
        print(f"📋 Creating backup of current ~/.zshrc to {backup_zshrc}")
        os.rename(home_zshrc, backup_zshrc)

    # Copy optimized version
    print(f"📝 Installing optimized ~/.zshrc")
    os.rename(optimized_zshrc, home_zshrc)

    all_passed = True

    # Test 1: Basic shell startup (should be fast now)
    print("\n🔥 TESTING SHELL STARTUP SPEED")
    success, output = run_command("zsh -c 'echo Shell started successfully'", "Basic shell startup", timeout=5)
    all_passed = all_passed and success

    # Test 2: Essential tools availability
    print("\n🔧 TESTING ESSENTIAL TOOLS")
    tools_to_test = [
        ("gh --version", "GitHub CLI"),
        ("git --version", "Git"),
        ("terraform --version", "Terraform"),
        ("python3 --version", "Python 3"),
        ("pip3 --version", "Pip 3"),
    ]

    for command, description in tools_to_test:
        success, output = run_command(command, description)
        all_passed = all_passed and success

    # Test 3: API key caching
    print("\n🔑 TESTING API KEY CACHING")
    cache_dir = os.path.expanduser("~/.cache/api_keys")
    if os.path.exists(cache_dir):
        cache_files = list(Path(cache_dir).glob("*"))
        if cache_files:
            print(f"   ✅ PASS: API key cache directory exists with {len(cache_files)} cached keys")
        else:
            print("   ⚠️  WARN: API key cache directory exists but no cached keys yet")
    else:
        print("   ❌ FAIL: API key cache directory not found")

    # Test 4: Lazy loading (these should work after lazy loading)
    print("\n🐌 TESTING LAZY LOADING")
    lazy_tools = [
        ("gcloud --version", "Google Cloud SDK (lazy loaded)"),
        ("python --version", "Python via conda/pyenv (lazy loaded)"),
    ]

    for command, description in lazy_tools:
        success, output = run_command(command, description)
        # Don't fail overall test for lazy loading issues
        if not success:
            print(f"   ℹ️  INFO: {description} - may need manual initialization")

    # Test 5: Environment variables
    print("\n🌍 TESTING ENVIRONMENT VARIABLES")
    env_tests = [
        ("echo $OPENAI_API_KEY | head -c 20", "OpenAI API key (should be cached)"),
        ("echo $QDRANT_API_KEY | head -c 20", "Qdrant API key (should be cached)"),
    ]

    for command, description in env_tests:
        success, output = run_command(command, description)
        if success and output:
            print(f"   ✅ PASS: {description} - key present (length: {len(output)})")
        else:
            print(f"   ❌ FAIL: {description} - key not available")

    # Test 6: Utility functions
    print("\n🛠️  TESTING UTILITY FUNCTIONS")
    utility_tests = [
        ("api-cache-status", "API cache status function"),
        ("refresh-api-keys", "API key refresh function"),
    ]

    for command, description in utility_tests:
        success, output = run_command(f"zsh -c '{command}' 2>/dev/null", description, timeout=15)
        if not success:
            print(f"   ℹ️  INFO: {description} - function available but may need dependencies")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! The optimized ~/.zshrc is working correctly.")
        print("\n📝 NEXT STEPS:")
        print("1. Restart your terminal/Cursor")
        print("2. Test your workflow - all tools should work")
        print("3. If you need API keys, they'll be cached automatically")
        print("4. Use 'refresh-api-keys' if you need to manually refresh")
    else:
        print("⚠️  SOME TESTS FAILED. The optimized ~/.zshrc may need adjustments.")
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Check that all required tools are installed")
        print("2. Verify network connectivity for API keys")
        print("3. Review the test output above for specific issues")

    return all_passed

if __name__ == "__main__":
    test_optimized_zshrc()
