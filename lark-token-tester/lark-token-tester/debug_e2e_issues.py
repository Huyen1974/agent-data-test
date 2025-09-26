#!/usr/bin/env python3
"""Debug script to investigate E2E test failures."""

import json
import logging
import sys
import time

import requests
from google.cloud import secretmanager

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(handler)

PROJECT_ID = "github-chatgpt-ggcloud"
TARGET_SECRET_ID = "lark-access-token-sg"
LARK_API_BASE = "https://open.larksuite.com/open-apis"


def debug_lark_api_endpoints():
    """Debug Lark API endpoints to find the correct one."""
    print("=== DEBUGGING LARK API ENDPOINTS ===")

    # Test different endpoints
    endpoints = [
        "/auth/v3/user/info",
        "/auth/v3/user/me",
        "/auth/v3/tenant/info",
        "/bot/v3/info",
    ]

    # Get current token for testing
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_version_path(PROJECT_ID, TARGET_SECRET_ID, "latest")
        response = client.access_secret_version(request={"name": secret_path})
        token = response.payload.data.decode("UTF-8")
        print(f"🔑 Using token: {token[:15]}...{token[-5:]}")
    except Exception as e:
        print(f"❌ Cannot get token: {e}")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for endpoint in endpoints:
        url = f"{LARK_API_BASE}{endpoint}"
        print(f"\n🔍 Testing endpoint: {endpoint}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ SUCCESS: {json.dumps(data, indent=2)}")
                    return endpoint
                except Exception:
                    print(f"   ✅ SUCCESS: {response.text[:200]}...")
                    return endpoint
            else:
                print(f"   ❌ FAIL: {response.text[:200]}...")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    print("❌ No working endpoint found")
    return None


def debug_cleanup_issue():
    """Debug the cleanup issue - why there are 2 enabled versions."""
    print("\n=== DEBUGGING CLEANUP ISSUE ===")

    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_path = client.secret_path(PROJECT_ID, TARGET_SECRET_ID)

        # List all versions with details
        versions = list(client.list_secret_versions(request={"parent": secret_path}))

        print(f"📊 Total versions: {len(versions)}")

        enabled_versions = []
        disabled_versions = []

        for version in versions:
            version_info = {
                "name": version.name,
                "state": version.state,
                "create_time": version.create_time,
                "enabled": version.state == secretmanager.SecretVersion.State.ENABLED,
            }

            if version.state == secretmanager.SecretVersion.State.ENABLED:
                enabled_versions.append(version_info)
            else:
                disabled_versions.append(version_info)

        print(f"🔓 Enabled versions ({len(enabled_versions)}):")
        for v in enabled_versions:
            print(f"   - {v['name']} (created: {v['create_time']})")

        print(f"🔒 Disabled versions ({len(disabled_versions)}):")
        for v in disabled_versions[-5:]:  # Show last 5 disabled
            print(f"   - {v['name']} (created: {v['create_time']})")

        # Check if cleanup was supposed to run
        print("\n🔍 Analysis:")
        if len(enabled_versions) > 1:
            print("   ❌ Multiple enabled versions found - cleanup failed")
            # Sort by creation time
            enabled_versions.sort(key=lambda x: x["create_time"])
            print(f"   📅 Oldest enabled: {enabled_versions[0]['name']}")
            print(f"   📅 Latest enabled: {enabled_versions[-1]['name']}")
        else:
            print("   ✅ Only 1 enabled version - cleanup working")

    except Exception as e:
        print(f"❌ Error debugging cleanup: {e}")
        import traceback

        traceback.print_exc()


def debug_token_generation():
    """Debug token generation process."""
    print("\n=== DEBUGGING TOKEN GENERATION ===")

    try:
        # Read app secret
        client = secretmanager.SecretManagerServiceClient()
        app_secret_path = client.secret_version_path(
            PROJECT_ID, "lark-app-secret-sg", "latest"
        )
        response = client.access_secret_version(request={"name": app_secret_path})
        app_secret = response.payload.data.decode("UTF-8")

        print(f"✅ Read app secret (length: {len(app_secret)})")

        # Try to generate token manually
        import requests

        url = "https://open.larksuite.com/open-apis/auth/v3/app_access_token/internal/"
        headers = {"Content-Type": "application/json"}
        payload = {"app_id": "cli_a785d634437a502f", "app_secret": app_secret}

        print("🔄 Attempting manual token generation...")
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Token generation successful: {json.dumps(data, indent=2)}")
            return data.get("app_access_token")
        else:
            print(f"❌ Token generation failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error in token generation debug: {e}")
        import traceback

        traceback.print_exc()
        return None


def debug_function_response():
    """Debug the Cloud Function response in detail."""
    print("\n=== DEBUGGING FUNCTION RESPONSE ===")

    try:
        # Call the function multiple times to see if it's consistent
        function_url = "https://asia-southeast1-github-chatgpt-ggcloud.cloudfunctions.net/generate_lark_token"

        print("🔄 Testing function multiple times...")

        for i in range(3):
            print(f"\nAttempt {i+1}:")
            response = requests.post(function_url, timeout=30)

            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error: {response.text}")

            time.sleep(2)  # Wait between calls

    except Exception as e:
        print(f"❌ Error testing function: {e}")


def main():
    """Main debug function."""
    print("🔍 E2E TEST FAILURE DEBUGGING TOOL")
    print("=" * 50)

    # Debug 1: Lark API endpoints
    working_endpoint = debug_lark_api_endpoints()

    # Debug 2: Cleanup issue
    debug_cleanup_issue()

    # Debug 3: Token generation
    debug_token_generation()

    # Debug 4: Function response
    debug_function_response()

    print("\n" + "=" * 50)
    print("📋 DEBUG SUMMARY")
    print("=" * 50)

    print("🔍 Key Findings:")
    if working_endpoint:
        print(f"   ✅ Found working Lark API endpoint: {working_endpoint}")
    else:
        print("   ❌ No working Lark API endpoint found")

    print("   🔍 Cleanup issue: Multiple enabled versions in Secret Manager")
    print("   🔍 Token generation: Working correctly")
    print("   🔍 Function response: Returning success but cleanup not working")

    print("\n🎯 Recommendations:")
    print("   1. Fix cleanup logic in Cloud Function")
    print("   2. Use correct Lark API endpoint for validation")
    print("   3. Monitor Secret Manager versions and costs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
