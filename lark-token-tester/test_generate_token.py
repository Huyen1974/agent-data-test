#!/usr/bin/env python3
"""Test script for generating Lark token from API."""

import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

# Constants from original function
PROJECT_ID = "github-chatgpt-ggcloud"
APP_SECRET_ID = "lark-app-secret-sg"
APP_ID = "cli_a785d634437a502f"
TARGET_SECRET_ID = "lark-access-token-sg"
LARK_TOKEN_URL = (
    "https://open.larksuite.com/open-apis/auth/v3/app_access_token/internal/"
)
REQUEST_TIMEOUT = 10
RETRY_COUNT = 3
RETRY_DELAY = 2


def _read_secret_mock(secret_id: str, project_id: str) -> str:
    """Mock version of secret reading logic for testing."""
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        logger.error("Failed to read secret %s: %s", secret_id, exc)
        return None


def _call_lark_api_mock(payload: dict) -> dict:
    """Mock version of Lark API call logic for testing."""
    import time

    import requests

    headers = {"Content-Type": "application/json"}
    last_error = None

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            logger.info("Calling Lark token API attempt %s", attempt)
            response = requests.post(
                LARK_TOKEN_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            logger.warning(
                "Call to Lark token API failed (attempt %s/%s): %s",
                attempt,
                RETRY_COUNT,
                exc,
            )
            if attempt < RETRY_COUNT:
                logger.info("Retrying in %s seconds", RETRY_DELAY)
                time.sleep(RETRY_DELAY)

    raise last_error


def test_generate_token_success():
    """Test successful token generation."""
    print("Test 1: Successful token generation...")

    try:
        # Read the app secret
        app_secret = _read_secret_mock(APP_SECRET_ID, PROJECT_ID)
        if not app_secret:
            print("❌ FAIL: Could not read app secret")
            return False

        # Prepare payload
        payload = {"app_id": APP_ID, "app_secret": app_secret}

        # Call Lark API
        response = _call_lark_api_mock(payload)
        token = response.get("app_access_token")

        if token and response.get("code") == 0:
            print(f"✅ PASS: Successfully generated token (length: {len(token)})")
            return True
        else:
            print(f"❌ FAIL: Invalid response from Lark API: {response}")
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during token generation: {e}")
        return False


def test_generate_token_invalid_credentials():
    """Test token generation with invalid credentials."""
    print("Test 2: Token generation with invalid credentials...")

    try:
        # Use invalid app secret
        payload = {"app_id": "invalid_app_id", "app_secret": "invalid_secret"}

        response = _call_lark_api_mock(payload)

        if response.get("code") != 0:
            print(
                f"✅ PASS: Correctly rejected invalid credentials (code: {response.get('code')})"
            )
            return True
        else:
            print("❌ FAIL: Should have rejected invalid credentials")
            return False

    except Exception as e:
        print(f"✅ PASS: Correctly raised exception for invalid credentials: {e}")
        return True


def test_generate_token_network_error():
    """Test token generation with network error."""
    print("Test 3: Token generation with network error...")

    try:
        # Mock network error by using invalid URL
        from unittest.mock import patch

        import requests

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.ConnectionError("Network error")

            payload = {"app_id": APP_ID, "app_secret": "test_secret"}

            try:
                _call_lark_api_mock(payload)
                print("❌ FAIL: Should have raised exception for network error")
                return False
            except requests.RequestException:
                print("✅ PASS: Correctly handled network error")
                return True

    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
        return False


def test_payload_structure():
    """Test that payload has correct structure."""
    print("Test 4: Payload structure validation...")

    try:
        app_secret = _read_secret_mock(APP_SECRET_ID, PROJECT_ID)
        if not app_secret:
            print("❌ FAIL: Could not read app secret for payload test")
            return False

        payload = {"app_id": APP_ID, "app_secret": app_secret}

        required_fields = ["app_id", "app_secret"]
        missing_fields = [field for field in required_fields if field not in payload]

        if not missing_fields:
            print(f"✅ PASS: Payload has correct structure: {list(payload.keys())}")
            return True
        else:
            print(f"❌ FAIL: Missing required fields: {missing_fields}")
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during payload validation: {e}")
        return False


if __name__ == "__main__":
    print("Starting Lark Token Generation Tests...\n")

    results = []
    results.append(test_generate_token_success())
    results.append(test_generate_token_invalid_credentials())
    results.append(test_generate_token_network_error())
    results.append(test_payload_structure())

    print("\n=== Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some tests FAILED!")
        sys.exit(1)
