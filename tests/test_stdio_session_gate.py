import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import mcp_server.stdio_server as stdio_server


@pytest.mark.unit
def test_stdio_session_gate_bootstraps_once():
    async def _run():
        stdio_server._session_ready_result = None
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ready": True,
            "status": "PASS",
            "session_id": "stdio:test",
        }

        with patch.object(
            stdio_server,
            "_request_with_fallback",
            AsyncMock(return_value=mock_response),
        ) as mock_request:
            result1 = await stdio_server._ensure_remote_session_ready(mock_client)
            result2 = await stdio_server._ensure_remote_session_ready(mock_client)

        assert result1["ready"] is True
        assert result2["ready"] is True
        assert mock_request.await_count == 1
        stdio_server._session_ready_result = None

    asyncio.run(_run())
