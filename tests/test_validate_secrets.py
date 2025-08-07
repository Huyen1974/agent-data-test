"""
Unit tests for scripts/validate_secrets.py

Tests the secrets validation functionality per CP6.1 requirements.
Validates exit codes, alert mechanisms, and RFC 3339 parsing.
"""

import os
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import validate_secrets


@pytest.mark.unit
class TestValidateSecrets:
    """Test suite for validate_secrets.py functionality."""

    def test_parse_rfc3339_timestamp_valid(self):
        """Test parsing valid RFC 3339 timestamps."""
        # Test various valid formats
        test_cases = [
            "2025-11-20T00:00:00Z",
            "2025-11-20T00:00:00+00:00",
            "2025-11-20T08:00:00+08:00",
            "2025-12-31T23:59:59Z",
        ]

        for timestamp_str in test_cases:
            result = validate_secrets.parse_rfc3339_timestamp(timestamp_str)
            assert result is not None, f"Failed to parse: {timestamp_str}"
            assert isinstance(result, datetime)
            assert result.tzinfo is not None, f"Missing timezone: {timestamp_str}"

    def test_parse_rfc3339_timestamp_invalid(self):
        """Test parsing invalid timestamp formats."""
        invalid_cases = [
            "invalid-date",
            "2025-13-01T00:00:00Z",  # Invalid month
            "2025-11-32T00:00:00Z",  # Invalid day
            "",
            None,
        ]

        for invalid_ts in invalid_cases:
            result = validate_secrets.parse_rfc3339_timestamp(str(invalid_ts))
            assert result is None, f"Should have failed: {invalid_ts}"

    def test_calculate_days_remaining(self):
        """Test days remaining calculation."""
        now = datetime.now(UTC)

        # Future date
        future_date = now + timedelta(days=30, hours=1)  # Add hour to ensure full day
        days = validate_secrets.calculate_days_remaining(future_date)
        assert days >= 30

        # Past date (expired)
        past_date = now - timedelta(days=5, hours=1)  # Subtract hour to ensure full day
        days = validate_secrets.calculate_days_remaining(past_date)
        assert days <= -5

        # Same day
        same_day = now + timedelta(hours=12)
        days = validate_secrets.calculate_days_remaining(same_day)
        assert days == 0

    @patch("validate_secrets.requests.post")
    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"})
    def test_send_slack_alert_success(self, mock_post):
        """Test successful Slack alert sending."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = validate_secrets.send_slack_alert("Test message", is_critical=True)
        assert result is True
        mock_post.assert_called_once()

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert "attachments" in payload
        assert payload["attachments"][0]["color"] == "danger"
        assert "Test message" in payload["attachments"][0]["text"]

    @patch("validate_secrets.requests.post")
    @patch.dict(os.environ, {}, clear=True)
    def test_send_slack_alert_no_webhook(self, mock_post):
        """Test Slack alert when webhook URL not set."""
        result = validate_secrets.send_slack_alert("Test message")
        assert result is False
        mock_post.assert_not_called()

    @patch("validate_secrets.requests.post")
    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"})
    def test_send_slack_alert_failure(self, mock_post):
        """Test Slack alert sending failure."""
        mock_post.side_effect = Exception("Network error")

        result = validate_secrets.send_slack_alert("Test message")
        assert result is False

    @patch("validate_secrets.get_secret_value")
    def test_validate_secret_expiry_no_expiry_secret(self, mock_get_secret):
        """Test validation when expiry secret doesn't exist."""
        mock_client = Mock()
        mock_get_secret.return_value = None

        status, message = validate_secrets.validate_secret_expiry(
            mock_client, "test_secret", "Test Secret"
        )

        assert status == 0
        assert "No expiry tracking" in message

    @patch("validate_secrets.get_secret_value")
    @patch("validate_secrets.send_slack_alert")
    def test_validate_secret_expiry_expired(self, mock_slack, mock_get_secret):
        """Test validation of expired secret."""
        mock_client = Mock()
        # Set expiry to 5 days ago
        past_date = datetime.now(UTC) - timedelta(days=5, hours=1)
        mock_get_secret.return_value = past_date.isoformat()
        mock_slack.return_value = True

        status, message = validate_secrets.validate_secret_expiry(
            mock_client, "test_secret", "Test Secret"
        )

        assert status == 1
        assert "EXPIRED" in message
        assert "days ago" in message  # Be flexible with exact number
        mock_slack.assert_called_once()
        # Verify critical alert
        call_args = mock_slack.call_args
        assert call_args[1]["is_critical"] is True

    @patch("validate_secrets.get_secret_value")
    @patch("validate_secrets.send_slack_alert")
    def test_validate_secret_expiry_warning(self, mock_slack, mock_get_secret):
        """Test validation of secret approaching expiry."""
        mock_client = Mock()
        # Set expiry to 10 days in future (< 15 day threshold)
        future_date = datetime.now(UTC) + timedelta(days=10, hours=12)
        mock_get_secret.return_value = future_date.isoformat()
        mock_slack.return_value = True

        status, message = validate_secrets.validate_secret_expiry(
            mock_client, "test_secret", "Test Secret"
        )

        assert status == 2
        assert "WARNING" in message
        assert "days" in message  # Be flexible with exact number
        mock_slack.assert_called_once()
        # Verify warning alert
        call_args = mock_slack.call_args
        assert call_args[1]["is_critical"] is False

    @patch("validate_secrets.get_secret_value")
    def test_validate_secret_expiry_good(self, mock_get_secret):
        """Test validation of secret with good expiry."""
        mock_client = Mock()
        # Set expiry to 30 days in future (> 15 day threshold)
        future_date = datetime.now(UTC) + timedelta(days=30, hours=12)
        mock_get_secret.return_value = future_date.isoformat()

        status, message = validate_secrets.validate_secret_expiry(
            mock_client, "test_secret", "Test Secret"
        )

        assert status == 0
        assert "OK" in message
        assert "days" in message  # Be flexible with exact number

    @patch("validate_secrets.get_secret_value")
    def test_validate_secret_expiry_invalid_format(self, mock_get_secret):
        """Test validation with invalid expiry format."""
        mock_client = Mock()
        mock_get_secret.return_value = "invalid-date-format"

        status, message = validate_secrets.validate_secret_expiry(
            mock_client, "test_secret", "Test Secret"
        )

        assert status == 1
        assert "Invalid expiry format" in message

    @patch("validate_secrets.get_secret_client")
    @patch("validate_secrets.validate_secret_expiry")
    def test_main_success(self, mock_validate, mock_client):
        """Test main function with all validations passing."""
        mock_client.return_value = Mock()
        mock_validate.return_value = (0, "OK: Test secret expires in 30 days")

        # Mock CRITICAL_SECRETS to avoid expiry suffix filtering
        with patch.dict(
            validate_secrets.CRITICAL_SECRETS, {"test_secret": "Test Secret"}
        ):
            exit_code = validate_secrets.main()

        assert exit_code == 0

    @patch("validate_secrets.get_secret_client")
    @patch("validate_secrets.validate_secret_expiry")
    def test_main_warning(self, mock_validate, mock_client):
        """Test main function with warnings."""
        mock_client.return_value = Mock()
        mock_validate.return_value = (2, "WARNING: Test secret expires in 10 days")

        with patch.dict(
            validate_secrets.CRITICAL_SECRETS, {"test_secret": "Test Secret"}
        ):
            exit_code = validate_secrets.main()

        assert exit_code == 2

    @patch("validate_secrets.get_secret_client")
    @patch("validate_secrets.validate_secret_expiry")
    def test_main_critical(self, mock_validate, mock_client):
        """Test main function with critical failures."""
        mock_client.return_value = Mock()
        mock_validate.return_value = (1, "EXPIRED: Test secret expired 5 days ago")

        with patch.dict(
            validate_secrets.CRITICAL_SECRETS, {"test_secret": "Test Secret"}
        ):
            exit_code = validate_secrets.main()

        assert exit_code == 1

    @patch("validate_secrets.get_secret_client")
    def test_main_client_failure(self, mock_client):
        """Test main function when client initialization fails."""
        mock_client.side_effect = Exception("Authentication failed")

        exit_code = validate_secrets.main()
        assert exit_code == 1

    @patch("validate_secrets.secretmanager.SecretManagerServiceClient")
    def test_get_secret_client_success(self, mock_sm_client):
        """Test successful Secret Manager client creation."""
        mock_client_instance = Mock()
        mock_sm_client.return_value = mock_client_instance

        client = validate_secrets.get_secret_client()
        assert client == mock_client_instance

    @patch("validate_secrets.secretmanager.SecretManagerServiceClient")
    def test_get_secret_client_failure(self, mock_sm_client):
        """Test Secret Manager client creation failure."""
        mock_sm_client.side_effect = Exception("Auth error")

        with pytest.raises(Exception, match="Auth error"):
            validate_secrets.get_secret_client()

    def test_get_secret_value_success(self):
        """Test successful secret value retrieval."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.payload.data = b"secret-value"
        mock_client.access_secret_version.return_value = mock_response

        result = validate_secrets.get_secret_value(mock_client, "test_secret")
        assert result == "secret-value"

        # Verify correct secret path construction
        expected_name = f"projects/{validate_secrets.GCP_PROJECT}/secrets/test_secret/versions/latest"
        mock_client.access_secret_version.assert_called_once()
        call_args = mock_client.access_secret_version.call_args
        assert call_args[1]["request"]["name"] == expected_name

    def test_get_secret_value_failure(self):
        """Test secret value retrieval failure."""
        mock_client = Mock()
        mock_client.access_secret_version.side_effect = Exception("Not found")

        result = validate_secrets.get_secret_value(mock_client, "test_secret")
        assert result is None


@pytest.mark.unit
class TestScriptIntegration:
    """Integration tests for the script as a whole."""

    @patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"})
    @patch("validate_secrets.secretmanager.SecretManagerServiceClient")
    @patch("validate_secrets.requests.post")
    def test_end_to_end_warning_scenario(self, mock_post, mock_sm_client):
        """Test end-to-end scenario with warning condition."""
        # Setup mocks
        mock_client = Mock()
        mock_sm_client.return_value = mock_client

        # Mock secret responses - expiry in 10 days (warning threshold)
        future_date = datetime.now(UTC) + timedelta(days=10)

        def mock_secret_access(request):
            secret_name = request["name"]
            mock_response = Mock()
            if "expiry" in secret_name:
                mock_response.payload.data = future_date.isoformat().encode()
            else:
                mock_response.payload.data = b"mock-secret-value"
            return mock_response

        mock_client.access_secret_version.side_effect = mock_secret_access

        # Mock successful Slack response
        mock_slack_response = Mock()
        mock_slack_response.raise_for_status.return_value = None
        mock_post.return_value = mock_slack_response

        # Run the validation
        with patch.dict(
            validate_secrets.CRITICAL_SECRETS, {"test_secret": "Test Secret"}
        ):
            exit_code = validate_secrets.main()

        # Verify warning exit code
        assert exit_code == 2

        # Verify Slack was called (could be called multiple times for multiple secrets)
        assert mock_post.call_count >= 1

        # Check that at least one call had warning content
        warning_found = False
        for call in mock_post.call_args_list:
            if call[1]["json"]["attachments"][0]["color"] == "warning":
                warning_found = True
                break
        assert warning_found, "Expected at least one warning alert"
