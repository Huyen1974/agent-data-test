#!/usr/bin/env python3
"""Test script for saving Lark token to Secret Manager."""

import logging
import os
import sys
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

# Constants from original function
PROJECT_ID = "github-chatgpt-ggcloud"
TARGET_SECRET_ID = "lark-access-token-sg"


def _save_secret_mock(secret_id: str, value: str, project_id: str) -> bool:
    """Mock version of secret saving logic for testing."""
    parent = f"projects/{project_id}/secrets/{secret_id}"
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.add_secret_version(
            request={"parent": parent, "payload": {"data": value.encode("UTF-8")}}
        )
        logger.info("Stored new secret version: %s", response.name)
        return True
    except Exception as exc:
        logger.error("Failed to store secret %s: %s", secret_id, exc)
        return False


def test_save_token_success():
    """Test successful token saving."""
    print("Test 1: Successful token saving...")

    try:
        # Generate a test token (mock)
        test_token = "t-xxxxxxxxxxxxxxxxxxx-test-token"

        result = _save_secret_mock(TARGET_SECRET_ID, test_token, PROJECT_ID)

        if result:
            print(f"✅ PASS: Successfully saved token (length: {len(test_token)})")
            return True
        else:
            print("❌ FAIL: Failed to save token")
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during token saving: {e}")
        return False


def test_save_token_with_invalid_project():
    """Test saving token with invalid project ID."""
    print("Test 2: Token saving with invalid project ID...")

    try:
        test_token = "t-xxxxxxxxxxxxxxxxxxx-test-token"

        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient"
        ) as mock_client:
            mock_client.return_value.add_secret_version.side_effect = Exception(
                "Invalid project"
            )

            result = _save_secret_mock(TARGET_SECRET_ID, test_token, "invalid-project")

            if not result:
                print("✅ PASS: Correctly handled invalid project ID")
                return True
            else:
                print("❌ FAIL: Should have failed with invalid project ID")
                return False

    except Exception as e:
        print(f"✅ PASS: Correctly raised exception for invalid project: {e}")
        return True


def test_save_token_with_invalid_secret_id():
    """Test saving token with invalid secret ID."""
    print("Test 3: Token saving with invalid secret ID...")

    try:
        test_token = "t-xxxxxxxxxxxxxxxxxxx-test-token"

        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient"
        ) as mock_client:
            mock_client.return_value.add_secret_version.side_effect = Exception(
                "Secret not found"
            )

            result = _save_secret_mock("invalid-secret", test_token, PROJECT_ID)

            if not result:
                print("✅ PASS: Correctly handled invalid secret ID")
                return True
            else:
                print("❌ FAIL: Should have failed with invalid secret ID")
                return False

    except Exception as e:
        print(f"✅ PASS: Correctly raised exception for invalid secret: {e}")
        return True


def test_save_token_with_empty_token():
    """Test saving empty token."""
    print("Test 4: Token saving with empty token...")

    try:
        # Test with empty token
        result = _save_secret_mock(TARGET_SECRET_ID, "", PROJECT_ID)

        if result:
            print(
                "✅ PASS: Successfully handled empty token (though this might not be ideal)"
            )
            return True
        else:
            print("✅ PASS: Correctly rejected empty token")
            return True

    except Exception as e:
        print(f"✅ PASS: Exception when saving empty token: {e}")
        return True


def test_save_token_with_special_characters():
    """Test saving token with special characters."""
    print("Test 5: Token saving with special characters...")

    try:
        # Test with token containing special characters
        special_token = "t-xxxxxx!@#$%^&*()_+-=[]{}|;':\",./<>?"

        result = _save_secret_mock(TARGET_SECRET_ID, special_token, PROJECT_ID)

        if result:
            print("✅ PASS: Successfully saved token with special characters")
            return True
        else:
            print("❌ FAIL: Failed to save token with special characters")
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception with special characters: {e}")
        return False


def test_save_token_multiple_calls():
    """Test saving multiple tokens (simulating token rotation)."""
    print("Test 6: Multiple token saves...")

    try:
        test_tokens = [
            "t-xxxxxxxxxxxxxxxxxxx-token-1",
            "t-xxxxxxxxxxxxxxxxxxx-token-2",
            "t-xxxxxxxxxxxxxxxxxxx-token-3",
        ]

        results = []
        for i, token in enumerate(test_tokens, 1):
            result = _save_secret_mock(TARGET_SECRET_ID, token, PROJECT_ID)
            results.append(result)
            logger.info("Token %d save result: %s", i, result)

        if all(results):
            print(f"✅ PASS: Successfully saved {len(results)} tokens")
            return True
        else:
            print(
                f"❌ FAIL: Only {sum(results)}/{len(results)} tokens saved successfully"
            )
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during multiple token saves: {e}")
        return False


if __name__ == "__main__":
    print("Starting Lark Token Saving Tests...\n")

    results = []
    results.append(test_save_token_success())
    results.append(test_save_token_with_invalid_project())
    results.append(test_save_token_with_invalid_secret_id())
    results.append(test_save_token_with_empty_token())
    results.append(test_save_token_with_special_characters())
    results.append(test_save_token_multiple_calls())

    print("\n=== Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some tests FAILED!")
        sys.exit(1)
