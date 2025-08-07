#!/usr/bin/env python3
"""
Validate secrets from Google Secret Manager for expiration alerts.

This script implements CP6.1 from Checkpoint Plan V7 to check PAT/secret expiration,
supporting centralized secrets management per HP-05 (Central Secrets Inheritance)
and GC-LAW §3 (Secret Management). Provides fallback mechanism per GH-LAW §5.5
when sync-secrets workflow is down >24h.

Key features:
- Fetches secrets and expiry dates from Google Secret Manager (central source)
- Parses RFC 3339 expiry timestamps
- Calculates days remaining for critical secrets
- Sends Slack alerts for secrets <15 days from expiration
- Exit codes: 0 (success), 1 (error/expired), 2 (warning/<15 days)
"""

import logging
import os
import sys
from datetime import UTC, datetime

try:
    import requests
    from dateutil.parser import parse as parse_date
    from google.cloud import secretmanager
except ImportError as e:
    print(f"ERROR: Required dependency not available: {e}")
    print("Ensure google-cloud-secret-manager and python-dateutil are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Critical secrets to monitor (per rotation policy: 90 days prod, 120 days test)
CRITICAL_SECRETS = {
    "gh_pat_sync_secrets": "GitHub PAT for sync-secrets workflow",
    "gh_pat_sync_secrets_expiry": "GitHub PAT expiry timestamp",
    # Add more critical secrets as needed
    # 'openai_api_key_expiry': 'OpenAI API Key expiry timestamp',
    # 'qdrant_cluster1_key_expiry': 'Qdrant Cluster Key expiry timestamp',
}

# Warning threshold (days)
WARNING_THRESHOLD_DAYS = 15

# Google Cloud project for secrets
GCP_PROJECT = "github-chatgpt-ggcloud"


def get_secret_client() -> secretmanager.SecretManagerServiceClient:
    """Initialize and return Secret Manager client."""
    try:
        return secretmanager.SecretManagerServiceClient()
    except Exception as e:
        logger.error(f"Failed to initialize Secret Manager client: {e}")
        raise


def get_secret_value(
    client: secretmanager.SecretManagerServiceClient, secret_name: str
) -> str | None:
    """
    Fetch secret value from Google Secret Manager.

    Args:
        client: Secret Manager client
        secret_name: Name of the secret

    Returns:
        Secret value or None if not found/error
    """
    try:
        name = f"projects/{GCP_PROJECT}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.warning(f"Failed to fetch secret '{secret_name}': {e}")
        return None


def parse_rfc3339_timestamp(timestamp_str: str) -> datetime | None:
    """
    Parse RFC 3339 timestamp string to datetime object.

    Args:
        timestamp_str: RFC 3339 formatted timestamp

    Returns:
        Parsed datetime object or None if invalid
    """
    try:
        # Use dateutil.parser for robust RFC 3339 parsing
        dt = parse_date(timestamp_str)
        # Ensure timezone awareness
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception as e:
        logger.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def calculate_days_remaining(expiry_date: datetime) -> int:
    """
    Calculate days remaining until expiry.

    Args:
        expiry_date: Expiry datetime

    Returns:
        Days remaining (negative if expired)
    """
    now = datetime.now(UTC)
    delta = expiry_date - now
    return delta.days


def send_slack_alert(message: str, is_critical: bool = False) -> bool:
    """
    Send alert to Slack channel.

    Args:
        message: Alert message
        is_critical: Whether this is a critical alert

    Returns:
        True if sent successfully, False otherwise
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not set, cannot send Slack alert")
        print(f"WARNING: {message}")
        return False

    try:
        color = "danger" if is_critical else "warning"
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": "🔐 Secrets Validation Alert",
                    "text": message,
                    "footer": "Agent Data Langroid - CP6.1 Secrets Monitor",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        logger.info("Slack alert sent successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        print(f"WARNING: Failed to send alert - {message}")
        return False


def validate_secret_expiry(
    client: secretmanager.SecretManagerServiceClient, secret_name: str, description: str
) -> tuple[int, str]:
    """
    Validate a single secret's expiry.

    Args:
        client: Secret Manager client
        secret_name: Name of the secret containing expiry timestamp
        description: Human-readable description of the secret

    Returns:
        Tuple of (status_code, message)
        status_code: 0 (ok), 1 (expired), 2 (warning)
    """
    expiry_secret_name = f"{secret_name}_expiry"
    expiry_value = get_secret_value(client, expiry_secret_name)

    if not expiry_value:
        logger.warning(f"No expiry information found for {secret_name}")
        return 0, f"No expiry tracking for {description}"

    expiry_date = parse_rfc3339_timestamp(expiry_value.strip())
    if not expiry_date:
        logger.error(f"Invalid expiry format for {secret_name}: {expiry_value}")
        return 1, f"Invalid expiry format for {description}"

    days_remaining = calculate_days_remaining(expiry_date)

    if days_remaining < 0:
        # Expired
        message = f"🚨 EXPIRED: {description} expired {abs(days_remaining)} days ago!"
        logger.error(message)
        send_slack_alert(message, is_critical=True)
        return 1, message
    elif days_remaining < WARNING_THRESHOLD_DAYS:
        # Warning
        message = f"⚠️  WARNING: {description} expires in {days_remaining} days"
        logger.warning(message)
        send_slack_alert(message, is_critical=False)
        return 2, message
    else:
        # OK
        message = f"✅ OK: {description} expires in {days_remaining} days"
        logger.info(message)
        return 0, message


def main() -> int:
    """
    Main validation function.

    Returns:
        Exit code: 0 (success), 1 (error/expired), 2 (warning)
    """
    logger.info("Starting secrets validation (CP6.1 compliance check)")

    try:
        client = get_secret_client()
    except Exception as e:
        logger.error(f"Cannot initialize Secret Manager client: {e}")
        return 1

    overall_status = 0
    results = []

    # Validate each critical secret
    for secret_name, description in CRITICAL_SECRETS.items():
        if secret_name.endswith("_expiry"):
            # Skip expiry secrets themselves, they're checked by their base secret
            continue

        status, message = validate_secret_expiry(client, secret_name, description)
        results.append((secret_name, status, message))

        # Track highest severity status
        if status > overall_status:
            overall_status = status

    # Log summary
    logger.info("=== Secrets Validation Summary ===")
    for secret_name, status, message in results:
        status_emoji = "✅" if status == 0 else "⚠️" if status == 2 else "🚨"
        logger.info(f"{status_emoji} {secret_name}: {message}")

    if overall_status == 0:
        logger.info("All secrets validation passed")
    elif overall_status == 1:
        logger.error("Critical secrets validation failed - immediate action required")
    else:
        logger.warning("Secrets validation completed with warnings")

    logger.info(f"Secrets validation completed with exit code {overall_status}")
    return overall_status


if __name__ == "__main__":
    sys.exit(main())
