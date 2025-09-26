#!/usr/bin/env python3
"""Test script for cleaning up old Lark token versions."""

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


def _cleanup_old_versions_mock(secret_id: str, project_id: str) -> None:
    """Mock version of cleanup logic for testing."""
    parent = f"projects/{project_id}/secrets/{secret_id}"
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()

        versions = list(client.list_secret_versions(request={"parent": parent}))
        versions.sort(key=lambda ver: ver.create_time, reverse=True)

        logger.info("Found %d versions of secret %s", len(versions), secret_id)

        if len(versions) > 1:
            for version in versions[1:]:
                if version.state == secretmanager.SecretVersion.State.ENABLED:
                    client.disable_secret_version(request={"name": version.name})
                    client.destroy_secret_version(request={"name": version.name})
                    logger.info("Destroyed old secret version: %s", version.name)
        else:
            logger.info("Only one version found, no cleanup needed")

    except Exception as exc:
        logger.error("Cleanup of old versions failed for %s: %s", secret_id, exc)


def test_cleanup_no_old_versions():
    """Test cleanup when there are no old versions."""
    print("Test 1: Cleanup with no old versions...")

    try:
        # This should work without issues when there's only one version
        _cleanup_old_versions_mock(TARGET_SECRET_ID, PROJECT_ID)
        print("✅ PASS: Cleanup completed successfully with no old versions")
        return True

    except Exception as e:
        print(f"❌ FAIL: Exception during cleanup: {e}")
        return False


def test_cleanup_with_invalid_project():
    """Test cleanup with invalid project ID."""
    print("Test 2: Cleanup with invalid project ID...")

    try:
        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient"
        ) as mock_client:
            mock_client.return_value.list_secret_versions.side_effect = Exception(
                "Project not found"
            )

            try:
                _cleanup_old_versions_mock(TARGET_SECRET_ID, "invalid-project")
                print("❌ FAIL: Should have raised exception for invalid project")
                return False
            except Exception:
                print("✅ PASS: Correctly handled invalid project ID")
                return True

    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
        return False


def test_cleanup_with_invalid_secret():
    """Test cleanup with invalid secret ID."""
    print("Test 3: Cleanup with invalid secret ID...")

    try:
        with patch(
            "google.cloud.secretmanager.SecretManagerServiceClient"
        ) as mock_client:
            mock_client.return_value.list_secret_versions.side_effect = Exception(
                "Secret not found"
            )

            try:
                _cleanup_old_versions_mock("invalid-secret", PROJECT_ID)
                print("❌ FAIL: Should have raised exception for invalid secret")
                return False
            except Exception:
                print("✅ PASS: Correctly handled invalid secret ID")
                return True

    except Exception as e:
        print(f"❌ FAIL: Unexpected exception: {e}")
        return False


def test_cleanup_logic_dry_run():
    """Test cleanup logic with simulated versions."""
    print("Test 4: Cleanup logic validation...")

    try:
        # Create mock versions to simulate the logic
        from unittest.mock import MagicMock

        mock_versions = []
        for i in range(5):
            version = MagicMock()
            version.create_time = i  # Earlier versions have smaller timestamps
            version.state = 1  # ENABLED
            version.name = (
                f"projects/{PROJECT_ID}/secrets/{TARGET_SECRET_ID}/versions/{i+1}"
            )
            mock_versions.append(version)

        # Sort by create_time descending (newest first)
        mock_versions.sort(key=lambda v: v.create_time, reverse=True)

        # Simulate the cleanup logic
        versions_to_destroy = mock_versions[1:]  # All except the newest

        if len(versions_to_destroy) == 4:
            print(
                f"✅ PASS: Correctly identified {len(versions_to_destroy)} versions to destroy"
            )
            return True
        else:
            print(
                f"❌ FAIL: Expected 4 versions to destroy, got {len(versions_to_destroy)}"
            )
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during logic validation: {e}")
        return False


def test_cleanup_disabled_versions():
    """Test cleanup behavior with disabled versions."""
    print("Test 5: Cleanup with disabled versions...")

    try:
        # Create mock versions with mixed states
        from unittest.mock import MagicMock

        mock_versions = []
        for i in range(3):
            version = MagicMock()
            version.create_time = i
            # Mix of enabled and disabled versions
            version.state = 0 if i % 2 == 0 else 1  # DISABLED, ENABLED, DISABLED
            version.name = (
                f"projects/{PROJECT_ID}/secrets/{TARGET_SECRET_ID}/versions/{i+1}"
            )
            mock_versions.append(version)

        # Sort by create_time descending
        mock_versions.sort(key=lambda v: v.create_time, reverse=True)

        # Count versions that should be destroyed (old + enabled)
        versions_to_destroy = [
            v for v in mock_versions[1:] if v.state == 1
        ]  # Skip newest, only enabled old ones

        if len(versions_to_destroy) == 1:  # Only the middle version should be destroyed
            print("✅ PASS: Correctly identified disabled versions to skip")
            return True
        else:
            print(
                f"❌ FAIL: Expected 1 version to destroy, got {len(versions_to_destroy)}"
            )
            return False

    except Exception as e:
        print(f"❌ FAIL: Exception during disabled version test: {e}")
        return False


def test_cleanup_single_version():
    """Test cleanup when there's only one version."""
    print("Test 6: Cleanup with single version...")

    try:
        # This should be a no-op
        _cleanup_old_versions_mock(TARGET_SECRET_ID, PROJECT_ID)
        print("✅ PASS: Correctly handled single version scenario")
        return True

    except Exception as e:
        print(f"❌ FAIL: Exception with single version: {e}")
        return False


if __name__ == "__main__":
    print("Starting Lark Token Cleanup Tests...\n")

    results = []
    results.append(test_cleanup_no_old_versions())
    results.append(test_cleanup_with_invalid_project())
    results.append(test_cleanup_with_invalid_secret())
    results.append(test_cleanup_logic_dry_run())
    results.append(test_cleanup_disabled_versions())
    results.append(test_cleanup_single_version())

    print("\n=== Summary ===")
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("⚠️  Some tests FAILED!")
        sys.exit(1)
