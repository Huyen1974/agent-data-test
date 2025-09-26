#!/usr/bin/env python3
"""Diagnostic script to investigate Cloud Function issue."""

import json
import logging
import sys

import requests
from google.cloud import secretmanager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

PROJECT_ID = "github-chatgpt-ggcloud"
APP_SECRET_ID = "lark-app-secret-sg"
TARGET_SECRET_ID = "lark-access-token-sg"
FUNCTION_URL = "https://asia-southeast1-github-chatgpt-ggcloud.cloudfunctions.net/generate_lark_token"


def diagnose_secret_permissions():
    """Check if we can read and write to the secrets."""
    print("=== DIAGNOSIS: SECRET MANAGER PERMISSIONS ===")

    try:
        client = secretmanager.SecretManagerServiceClient()

        # Check if we can read app secret
        print("1. Testing read access to lark-app-secret-sg...")
        try:
            app_secret_path = client.secret_version_path(
                PROJECT_ID, APP_SECRET_ID, "latest"
            )
            response = client.access_secret_version(request={"name": app_secret_path})
            secret_value = response.payload.data.decode("UTF-8")
            print(f"   ✅ Can read app secret (length: {len(secret_value)})")
        except Exception as e:
            print(f"   ❌ Cannot read app secret: {e}")
            return False

        # Check if we can write to target secret
        print("2. Testing write access to lark-access-token-sg...")
        try:
            parent = client.secret_path(PROJECT_ID, TARGET_SECRET_ID)
            response = client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": b"test-token"},
                }
            )
            print(f"   ✅ Can write to target secret: {response.name}")

            # Clean up the test version
            version_name = response.name
            client.disable_secret_version(request={"name": version_name})
            client.destroy_secret_version(request={"name": version_name})
            print("   ✅ Test version cleaned up")

        except Exception as e:
            print(f"   ❌ Cannot write to target secret: {e}")
            return False

        return True

    except Exception as e:
        print(f"❌ Secret Manager client error: {e}")
        return False


def diagnose_function_logs():
    """Try to get more information about the function failure."""
    print("\n=== DIAGNOSIS: FUNCTION FAILURE ANALYSIS ===")

    try:
        # Try calling the function with more detailed headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Lark-Token-Tester/1.0",
        }

        print("1. Calling function with detailed logging...")
        response = requests.post(FUNCTION_URL, headers=headers, timeout=60)

        print(f"   Status Code: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")

        try:
            response_data = response.json()
            print(
                f"   Response Body: {json.dumps(response_data, indent=2, ensure_ascii=False)}"
            )
        except Exception:
            print(f"   Response Body (raw): {response.text}")

        return response_data if response.status_code == 200 else None

    except Exception as e:
        print(f"❌ Error calling function: {e}")
        return None


def check_current_token_state():
    """Check the current state of the Lark token secret."""
    print("\n=== DIAGNOSIS: CURRENT TOKEN STATE ===")

    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_path(PROJECT_ID, TARGET_SECRET_ID)

        # List all versions
        versions = list(client.list_secret_versions(request={"parent": secret_path}))

        print(f"1. Total versions: {len(versions)}")

        enabled_versions = []
        disabled_versions = []

        for version in versions:
            if version.state == secretmanager.SecretVersion.State.ENABLED:
                enabled_versions.append(version)
            else:
                disabled_versions.append(version)

        print(f"2. Enabled versions: {len(enabled_versions)}")
        print(f"3. Disabled versions: {len(disabled_versions)}")

        # Read the latest version
        if enabled_versions:
            latest_version = sorted(
                enabled_versions, key=lambda v: v.create_time, reverse=True
            )[0]
            print(f"4. Latest version: {latest_version.name}")

            try:
                response = client.access_secret_version(
                    request={"name": latest_version.name}
                )
                token = response.payload.data.decode("UTF-8")
                print(f"5. Current token length: {len(token)}")
                print(
                    f"6. Token preview: {token[:10]}...{token[-5:] if len(token) > 15 else token}"
                )
            except Exception as e:
                print(f"5. ❌ Cannot read latest token: {e}")

        return True

    except Exception as e:
        print(f"❌ Error checking token state: {e}")
        return False


def main():
    """Main diagnostic function."""
    print("🔍 LARK TOKEN FUNCTION DIAGNOSTIC TOOL")
    print("=" * 50)

    results = []

    # Test 1: Secret Manager permissions
    results.append(("Secret Manager Permissions", diagnose_secret_permissions()))

    # Test 2: Function failure analysis
    function_result = diagnose_function_logs()
    results.append(("Function Call Analysis", function_result is not None))

    # Test 3: Current token state
    results.append(("Current Token State Check", check_current_token_state()))

    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  - {test_name}: {status}")

    if passed == total:
        print("\n🎉 All diagnostic tests passed!")
    else:
        print(f"\n⚠️  {total - passed} diagnostic test(s) failed - need investigation")

    return 0


if __name__ == "__main__":
    sys.exit(main())
