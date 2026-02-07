"""Tests for agent_data.resilient_client — retry, health tracking, discovery."""

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_data.resilient_client import (
    ResilientCaller,
    ServiceHealthRegistry,
    ServiceStatus,
    discover_services,
    health_registry,
    probe_openai,
    probe_qdrant,
    sync_retry,
)


# ---------------------------------------------------------------------------
# sync_retry tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestSyncRetry:
    def test_retries_on_connection_error(self):
        call_count = 0

        @sync_retry(max_retries=3, service_name="test")
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("connection refused")

        with pytest.raises(ConnectionError):
            failing_func()
        assert call_count == 3

    def test_succeeds_after_transient_failure(self):
        call_count = 0

        @sync_retry(max_retries=3, service_name="test")
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temporary")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    def test_no_retry_on_value_error(self):
        call_count = 0

        @sync_retry(max_retries=3, service_name="test")
        def bad_args_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            bad_args_func()
        assert call_count == 1  # No retries for ValueError


# ---------------------------------------------------------------------------
# ServiceHealthRegistry tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestServiceHealthRegistry:
    def test_transitions(self):
        reg = ServiceHealthRegistry()
        reg.register("svc")
        assert reg.get_status("svc").status == ServiceStatus.UNKNOWN

        reg.mark_healthy("svc", 10.0)
        assert reg.get_status("svc").status == ServiceStatus.OK

        reg.mark_unhealthy("svc", "timeout")
        assert reg.get_status("svc").status == ServiceStatus.DEGRADED

        reg.mark_unhealthy("svc", "timeout")
        reg.mark_unhealthy("svc", "timeout")
        assert reg.get_status("svc").status == ServiceStatus.DOWN

    def test_summary_format(self):
        reg = ServiceHealthRegistry()
        reg.mark_healthy("qdrant", 12.5)
        reg.mark_unhealthy("openai", "key missing")
        summary = reg.summary()
        assert "qdrant" in summary
        assert summary["qdrant"]["status"] == "ok"
        assert summary["qdrant"]["latency_ms"] == 12.5
        assert summary["openai"]["status"] == "degraded"
        assert summary["openai"]["last_error"] == "key missing"

    def test_cache_freshness(self):
        reg = ServiceHealthRegistry()
        assert reg.is_cache_fresh("unknown") is False

        reg.mark_healthy("svc", 5.0)
        assert reg.is_cache_fresh("svc") is True

    def test_overall_status_healthy(self):
        reg = ServiceHealthRegistry()
        reg.mark_healthy("a", 1)
        reg.mark_healthy("b", 2)
        assert reg.overall_status() == "healthy"

    def test_overall_status_degraded(self):
        reg = ServiceHealthRegistry()
        reg.mark_healthy("a", 1)
        reg.mark_unhealthy("b", "err")
        assert reg.overall_status() == "degraded"


# ---------------------------------------------------------------------------
# ResilientCaller tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestResilientCaller:
    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        import httpx

        caller = ResilientCaller(
            service_name="test-svc", base_url="http://fake", max_retries=2
        )
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.request = AsyncMock(
            side_effect=httpx.ConnectError("connection failed")
        )
        caller._client = mock_client

        with pytest.raises(httpx.ConnectError):
            await caller.get("/test")

        # Should have been called max_retries times
        assert mock_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self):
        caller = ResilientCaller(service_name="test-hc", base_url="http://fake")
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.request = AsyncMock(return_value=mock_response)
        caller._client = mock_client

        result = await caller.health_check()
        assert result["service"] == "test-hc"
        assert result["status"] == "ok"
        assert "latency_ms" in result


# ---------------------------------------------------------------------------
# Probe tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestProbes:
    @pytest.mark.asyncio
    async def test_probe_qdrant_healthy(self):
        mock_store = MagicMock()
        mock_store.enabled = True
        mock_store.count.return_value = 42

        with patch("agent_data.vector_store.get_vector_store", return_value=mock_store):
            result = await probe_qdrant()
        assert result is True

    @pytest.mark.asyncio
    async def test_probe_qdrant_disabled(self):
        mock_store = MagicMock()
        mock_store.enabled = False

        with patch("agent_data.vector_store.get_vector_store", return_value=mock_store):
            result = await probe_qdrant()
        assert result is True

    @pytest.mark.asyncio
    async def test_probe_qdrant_failure(self):
        mock_store = MagicMock()
        mock_store.enabled = True
        mock_store.count.side_effect = ConnectionError("refused")

        with patch("agent_data.vector_store.get_vector_store", return_value=mock_store):
            result = await probe_qdrant()
        assert result is False

    @pytest.mark.asyncio
    async def test_probe_openai_with_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        result = await probe_openai()
        assert result is True

    @pytest.mark.asyncio
    async def test_probe_openai_without_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = await probe_openai()
        assert result is False


# ---------------------------------------------------------------------------
# discover_services tests
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestDiscoverServices:
    def test_discovers_from_service_env(self, monkeypatch):
        monkeypatch.setenv("SERVICE_MYAPI_URL", "http://myapi.example.com")
        services = discover_services()
        assert "myapi" in services
        assert services["myapi"].base_url == "http://myapi.example.com"
        # Cleanup
        monkeypatch.delenv("SERVICE_MYAPI_URL")
        discover_services()

    def test_backward_compat_qdrant(self, monkeypatch):
        # Remove any SERVICE_ vars that might conflict
        for key in list(os.environ):
            if key.startswith("SERVICE_") and key.endswith("_URL"):
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("QDRANT_URL", "https://qdrant.example.com")
        services = discover_services()
        assert "qdrant" in services
        assert services["qdrant"].base_url == "https://qdrant.example.com"

    def test_empty_when_no_vars(self, monkeypatch):
        # Remove all SERVICE_ and legacy vars
        for key in list(os.environ):
            if key.startswith("SERVICE_") and key.endswith("_URL"):
                monkeypatch.delenv(key, raising=False)
        for legacy in [
            "QDRANT_URL",
            "QDRANT_API_URL",
            "OPENAI_API_URL",
            "OPENAI_BASE_URL",
        ]:
            monkeypatch.delenv(legacy, raising=False)
        services = discover_services()
        assert len(services) == 0
