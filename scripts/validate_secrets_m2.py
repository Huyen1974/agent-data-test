#!/usr/bin/env python3
"""
validate_secrets_m2.py - M2 Security Verify: GitHub Secrets Validation
Part of Prompt 169m - Security Verification System

Validates GitHub repository secrets configuration for:
- Central repository secrets availability
- Child repository secrets availability
- PAT authentication to GitHub API
- Absence of forbidden PAT secrets in child repositories

Requirements:
- Python 3.11+
- requests library
- Valid GitHub PAT for API access

Exit codes:
- 0: All validations passed
- 1: Critical validation failed

Output: JSON to stdout with validation results
"""

import argparse
import json
import sys
from datetime import UTC, datetime

try:
    import requests
except ImportError:
    print("ERROR: requests library not available. Install with: pip install requests")
    sys.exit(1)


class GitHubSecretsValidator:
    """GitHub secrets validation for M2 security verification."""

    REQUIRED_SECRETS = [
        "GCP_PROJECT_ID",
        "GCP_SERVICE_ACCOUNT",
        "GCP_WIF_POOL",
        "GCP_WIF_PROVIDER",
    ]

    def __init__(self, pat_token: str):
        """Initialize validator with GitHub PAT."""
        self.pat_token = pat_token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {pat_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "M2-Security-Verify/1.0",
            }
        )

    def validate_pat_auth(self) -> bool:
        """
        Validate PAT authentication with GitHub API.

        Returns:
            True if PAT is valid (HTTP 200), False otherwise
        """
        try:
            response = self.session.get("https://api.github.com/user", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def get_repository_secrets(self, repo: str) -> list[str] | None:
        """
        Get list of secret names for a repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            List of secret names or None if failed
        """
        try:
            url = f"https://api.github.com/repos/{repo}/actions/secrets"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return [secret["name"] for secret in data.get("secrets", [])]
            return None
        except Exception:
            return None

    def check_required_secrets(self, repo: str) -> bool:
        """
        Check if repository has all required secrets.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            True if all required secrets are present
        """
        secrets = self.get_repository_secrets(repo)
        if secrets is None:
            return False

        return all(secret in secrets for secret in self.REQUIRED_SECRETS)

    def check_forbidden_pat_secrets(self, repo: str) -> bool:
        """
        Check if repository contains any forbidden PAT secrets.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            True if forbidden PAT secrets are found
        """
        secrets = self.get_repository_secrets(repo)
        if secrets is None:
            return False

        # Check for secrets containing "PAT" (case-insensitive)
        return any("pat" in secret.lower() for secret in secrets)


def load_pat_from_file(pat_file: str) -> str:
    """
    Load PAT token from file.

    Args:
        pat_file: Path to file containing PAT

    Returns:
        PAT token string

    Raises:
        SystemExit: If file cannot be read
    """
    try:
        with open(pat_file, encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"ERROR: Cannot read PAT file '{pat_file}': {e}")
        sys.exit(1)


def main() -> int:
    """
    Main validation function.

    Returns:
        Exit code: 0 (success), 1 (failure)
    """
    parser = argparse.ArgumentParser(
        description="M2 Security Verify: GitHub Secrets Validation"
    )
    parser.add_argument(
        "--central", required=True, help="Central repository in format 'owner/repo'"
    )
    parser.add_argument(
        "--child", required=True, help="Child repository in format 'owner/repo'"
    )
    parser.add_argument(
        "--pat-file", required=True, help="Path to file containing GitHub PAT"
    )

    args = parser.parse_args()

    # Load PAT token
    pat_token = load_pat_from_file(args.pat_file)

    # Initialize validator
    validator = GitHubSecretsValidator(pat_token)

    # Perform validations
    timestamp_utc = datetime.now(UTC).isoformat()

    # 1. Validate PAT authentication
    pat_http_200 = validator.validate_pat_auth()
    if not pat_http_200:
        print("ERROR: PAT authentication failed (HTTP != 200)")
        result = {
            "central_min_ok": False,
            "child_min_ok": False,
            "pat_http_200": False,
            "forbidden_pat_present": False,
            "timestamp_utc": timestamp_utc,
        }
        print(json.dumps(result, indent=2))
        return 1

    # 2. Check central repository secrets
    central_min_ok = validator.check_required_secrets(args.central)

    # 3. Check child repository secrets
    child_min_ok = validator.check_required_secrets(args.child)

    # 4. Check for forbidden PAT secrets in child
    forbidden_pat_present = validator.check_forbidden_pat_secrets(args.child)

    # Prepare result
    result = {
        "central_min_ok": central_min_ok,
        "child_min_ok": child_min_ok,
        "pat_http_200": pat_http_200,
        "forbidden_pat_present": forbidden_pat_present,
        "timestamp_utc": timestamp_utc,
    }

    # Output JSON result
    print(json.dumps(result, indent=2))

    # Return exit code based on validation results
    if not all([central_min_ok, child_min_ok, pat_http_200]) or forbidden_pat_present:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
