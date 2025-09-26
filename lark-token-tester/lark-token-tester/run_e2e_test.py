#!/usr/bin/env python3
"""End-to-End integration test for Lark Token workflow."""

import logging
import sys
import time

import requests
from google.cloud import secretmanager

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

# Configuration
PROJECT_ID = "github-chatgpt-ggcloud"
TARGET_SECRET_ID = "lark-access-token-sg"
LARK_API_BASE = "https://open.larksuite.com/open-apis"

APP_SECRET_ID = "lark-app-secret-sg"
APP_ID = "cli_a785d634437a502f"
LARK_TOKEN_URL = (
    "https://open.larksuite.com/open-apis/auth/v3/app_access_token/internal/"
)

# Cloud Function URL
FUNCTION_URL = "https://generate-lark-token-pfne2mqwja-as.a.run.app"


def step_1_call_function() -> bool:
    """Step 1: Call Cloud Function to generate new token."""
    print()
    print("=" * 60)
    print("STEP 1: CALLING CLOUD FUNCTION")
    print("=" * 60)

    try:
        logger.info("Calling generate_lark_token function at: %s", FUNCTION_URL)

        # Make HTTP POST request to trigger token generation
        response = requests.post(
            FUNCTION_URL, timeout=60, headers={"Content-Type": "application/json"}
        )

        logger.info("Function response status: %d", response.status_code)
        logger.info("Function response: %s", response.text)

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("status") == "OK":
                print("✅ PASS: Cloud Function executed successfully")
                return True
            else:
                print(
                    f"❌ FAIL: Function returned error: {response_data.get('message')}"
                )
                return False
        else:
            print(f"❌ FAIL: Function returned HTTP {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Network error calling function: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False


def step_2_read_new_token() -> str | None:
    """Step 2: Read new token from Secret Manager."""
    print()
    print("=" * 60)
    print("STEP 2: READING NEW TOKEN FROM SECRET MANAGER")
    print("=" * 60)

    try:
        # Wait a moment for the function to complete and secret to be updated
        logger.info("Waiting 5 seconds for token generation to complete...")
        time.sleep(5)

        # Initialize Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_version_path(PROJECT_ID, TARGET_SECRET_ID, "latest")

        # Read the latest version
        response = client.access_secret_version(request={"name": secret_path})
        token = response.payload.data.decode("UTF-8")

        if token:
            print(f"✅ PASS: Successfully read new token (length: {len(token)})")
            # Mask token for security in logs
            masked_token = (
                token[:10] + "..." + token[-5:] if len(token) > 15 else "****"
            )
            print(f"🔑 Token: {masked_token}")
            return token
        else:
            print("❌ FAIL: Token is empty")
            return None

    except Exception as e:
        print(f"❌ FAIL: Error reading token: {e}")
        return None


def step_3_validate_token(token: str) -> bool:
    """Step 3: Validate token by comparing with Lark API response."""
    print()
    print("=" * 60)
    print("STEP 3: VALIDATING TOKEN WITH LARK API")
    print("=" * 60)

    try:
        client = secretmanager.SecretManagerServiceClient()
        app_secret_path = client.secret_version_path(
            PROJECT_ID, APP_SECRET_ID, "latest"
        )
        app_secret = client.access_secret_version(
            request={"name": app_secret_path}
        ).payload.data.decode("UTF-8")

        if not app_secret:
            print("❌ FAIL: App secret is empty or missing")
            return False

        payload = {"app_id": APP_ID, "app_secret": app_secret}
        headers = {"Content-Type": "application/json"}

        logger.info("Calling Lark API to verify stored token")
        response = requests.post(
            LARK_TOKEN_URL, json=payload, headers=headers, timeout=30
        )
        logger.info("Verification response status: %d", response.status_code)

        if response.status_code != 200:
            print(f"❌ FAIL: Lark API returned HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False

        data = response.json()
        if data.get("code") != 0:
            print(f"❌ FAIL: Lark API error: {data.get('msg', 'Unknown error')}")
            return False

        api_token = data.get("app_access_token")
        if api_token == token:
            print("✅ PASS: Token matches current Lark app access token")
            return True

        print("❌ FAIL: Token mismatch between Secret Manager and Lark API")
        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ FAIL: Network error validating token: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error during validation: {e}")
        return False


def step_4_check_cleanup() -> bool:
    """Step 4: Verify cleanup - only 1 version should remain."""
    print()
    print("=" * 60)
    print("STEP 4: VERIFYING CLEANUP (ONLY 1 VERSION)")
    print("=" * 60)

    try:
        # Initialize Secret Manager client
        client = secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_path(PROJECT_ID, TARGET_SECRET_ID)

        # List all versions
        versions = list(client.list_secret_versions(request={"parent": secret_path}))
        enabled_versions = [
            v for v in versions if v.state == secretmanager.SecretVersion.State.ENABLED
        ]

        print(f"📊 Total versions found: {len(versions)}")
        print(f"🔓 Enabled versions: {len(enabled_versions)}")
        print(f"🔒 Disabled versions: {len(versions) - len(enabled_versions)}")

        if len(enabled_versions) == 1:
            print("✅ PASS: Correctly cleaned up - only 1 enabled version remains")
            latest_version = enabled_versions[0]
            print(f"📅 Latest version: {latest_version.name}")
            return True
        else:
            print(f"❌ FAIL: Expected 1 enabled version, found {len(enabled_versions)}")
            print("This indicates cleanup did not work properly")
            return False

    except Exception as e:
        print(f"❌ FAIL: Error checking cleanup: {e}")
        return False


def main():
    """Main function to run the complete E2E test."""
    print("🚀 Starting Lark Token E2E Integration Test")
    print("=" * 60)
    print("This test will validate the complete token refresh workflow:")
    print("1. Call Cloud Function to generate new token")
    print("2. Read new token from Secret Manager")
    print("3. Validate token with Lark API")
    print("4. Verify cleanup (only 1 version remains)")
    print("=" * 60)

    results = []

    # Step 1: Call Function
    results.append(("Step 1 - Call Function", step_1_call_function()))

    # Step 2: Read New Token
    token = None
    if results[-1][1]:  # If step 1 passed
        token = step_2_read_new_token()
        results.append(("Step 2 - Read Token", token is not None))
    else:
        print("⏭️  Skipping Step 2 (function call failed)")
        results.append(("Step 2 - Read Token", False))

    # Step 3: Validate Token
    if results[-1][1] and token:  # If step 2 passed
        results.append(("Step 3 - Validate Token", step_3_validate_token(token)))
    else:
        print("⏭️  Skipping Step 3 (token reading failed)")
        results.append(("Step 3 - Validate Token", False))

    # Step 4: Check Cleanup
    results.append(("Step 4 - Verify Cleanup", step_4_check_cleanup()))

    # Summary
    print()
    print("=" * 60)
    print("📊 E2E TEST RESULTS SUMMARY")
    print("=" * 60)

    total_steps = len(results)
    passed_steps = sum(1 for _, passed in results if passed)

    print(f"Total Steps: {total_steps}")
    print(f"Passed: {passed_steps}")
    print(f"Failed: {total_steps - passed_steps}")

    print()
    print("📋 DETAILED RESULTS:")
    for step_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  - {step_name}: {status}")

    print()
    print("=" * 60)

    if passed_steps == total_steps:
        print("🎉 ALL STEPS PASSED! E2E workflow is working correctly! 🎉")
        return 0
    else:
        print(f"⚠️  {total_steps - passed_steps} STEP(S) FAILED!")
        print("The Lark token workflow has issues that need to be addressed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
