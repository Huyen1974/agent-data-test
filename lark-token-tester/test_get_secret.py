#!/usr/bin/env python3
"""Test script for reading Lark app secret from Secret Manager."""

import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Copy the logic from the original function
PROJECT_ID = "github-chatgpt-ggcloud"
APP_SECRET_ID = "lark-app-secret-sg"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)


def _read_secret_mock(secret_id: str, project_id: str) -> str:
    """Mock version of secret reading logic for testing."""
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    try:
        # This is the logic we want to test - reading from Secret Manager
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        logger.error("Failed to read secret %s: %s", secret_id, exc)
        return None


def test_get_secret():
    """Test reading the Lark app secret."""
    print("=== Testing Secret Reading Logic ===")

    # Test 1: Test with valid secret ID and project
    print("Test 1: Reading lark-app-secret-sg...")
    try:
        secret_value = _read_secret_mock(APP_SECRET_ID, PROJECT_ID)
        if secret_value:
            print(f"✅ PASS: Successfully read secret (length: {len(secret_value)})")
            # Don't print the actual secret value for security
            return True
        else:
            print("❌ FAIL: Could not read secret or secret is empty")
            return False
    except Exception as e:
        print(f"❌ FAIL: Exception occurred: {e}")
        return False


def test_get_secret_with_invalid_project():
    """Test reading secret with invalid project ID."""
    print("Test 2: Reading secret with invalid project ID...")
    try:
        secret_value = _read_secret_mock(APP_SECRET_ID, "invalid-project")
        if secret_value is None:
            print("✅ PASS: Correctly handled invalid project ID")
            return True
        else:
            print("❌ FAIL: Should have failed with invalid project ID")
            return False
    except Exception as e:
        print(f"✅ PASS: Correctly raised exception for invalid project: {e}")
        return True


def test_get_secret_with_invalid_secret_id():
    """Test reading secret with invalid secret ID."""
    print("Test 3: Reading secret with invalid secret ID...")
    try:
        secret_value = _read_secret_mock("invalid-secret", PROJECT_ID)
        if secret_value is None:
            print("✅ PASS: Correctly handled invalid secret ID")
            return True
        else:
            print("❌ FAIL: Should have failed with invalid secret ID")
            return False
    except Exception as e:
        print(f"✅ PASS: Correctly raised exception for invalid secret: {e}")
        return True


if __name__ == "__main__":
    print("Starting Lark Secret Reading Tests...\n")

    results = []
    results.append(test_get_secret())
    results.append(test_get_secret_with_invalid_project())
    results.append(test_get_secret_with_invalid_secret_id())

    print("\n=== Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some tests FAILED!")
        sys.exit(1)
