import subprocess
from pathlib import Path

import pytest

from tests.langroid_test_stubs import install_langroid_stubs

install_langroid_stubs()

from agent_data.session_readiness import (
    CLASS_SESSION_BINDING_FAILED,
    CLASS_TOOL_ROUTE_DOWN,
    SessionGateError,
    SessionReadinessGate,
)


@pytest.mark.unit
def test_session_gate_passes_and_uses_cache():
    calls = {"health": 0, "bind": 0, "sentinel": 0, "sleep": []}

    def health():
        calls["health"] += 1
        return {"overall_status": "healthy"}

    def bind(session_id: str):
        calls["bind"] += 1
        return {"session_id": session_id}

    def sentinel():
        calls["sentinel"] += 1
        return {"hits": 1, "top_document": "knowledge/doc.md"}

    gate = SessionReadinessGate(
        health_check=health,
        bind_session=bind,
        sentinel_check=sentinel,
        sleep_fn=lambda seconds: calls["sleep"].append(seconds),
        ttl_seconds=60,
        backoff_seconds=(0, 2, 5, 10),
    )

    result1 = gate.ensure_ready(
        session_id="sess-1",
        agent="codex",
        transport="http-mcp",
    )
    result2 = gate.ensure_ready(
        session_id="sess-1",
        agent="codex",
        transport="http-mcp",
    )

    assert result1.ready is True
    assert result1.status == "PASS"
    assert result1.attempts == 1
    assert result2.ready is True
    assert result2.cached is True
    assert calls["health"] == 1
    assert calls["bind"] == 1
    assert calls["sentinel"] == 1
    assert calls["sleep"] == []


@pytest.mark.unit
def test_session_gate_retries_and_logs_incident():
    sleeps: list[float] = []

    def sentinel():
        raise SessionGateError(
            classification=CLASS_TOOL_ROUTE_DOWN,
            failure_stage="sentinel_query",
            message="Sentinel query returned empty context",
            details={"query": "agent data access confirmation"},
        )

    gate = SessionReadinessGate(
        health_check=lambda: {"overall_status": "healthy"},
        bind_session=lambda session_id: {"session_id": session_id},
        sentinel_check=sentinel,
        sleep_fn=lambda seconds: sleeps.append(seconds),
        ttl_seconds=60,
        backoff_seconds=(0, 2, 5),
    )

    result = gate.ensure_ready(
        session_id="sess-2",
        agent="codex",
        transport="http-mcp",
    )

    assert result.ready is False
    assert result.status == "NOT_READY"
    assert result.classification == CLASS_TOOL_ROUTE_DOWN
    assert result.failure_stage == "sentinel_query"
    assert result.attempts == 3
    assert sleeps == [2, 5]
    assert "system_issue" not in result.details


@pytest.mark.unit
def test_session_gate_classifies_binding_failures():
    gate = SessionReadinessGate(
        health_check=lambda: {"overall_status": "healthy"},
        bind_session=lambda session_id: (_ for _ in ()).throw(
            SessionGateError(
                classification=CLASS_SESSION_BINDING_FAILED,
                failure_stage="session_binding",
                message="history backend unavailable",
                details={"session_id": session_id},
            )
        ),
        sentinel_check=lambda: {"hits": 1},
        sleep_fn=lambda seconds: None,
        ttl_seconds=60,
        backoff_seconds=(0,),
    )

    result = gate.ensure_ready(
        session_id="sess-3",
        agent="gpt",
        transport="rest-chat",
    )

    assert result.ready is False
    assert result.classification == CLASS_SESSION_BINDING_FAILED
    assert result.failure_stage == "session_binding"


@pytest.mark.unit
def test_session_ready_script_parses_responses(tmp_path: Path):
    curl_path = tmp_path / "curl"
    curl_path.write_text(
        """#!/bin/bash
OUT=""
URL=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o)
      OUT="$2"
      shift 2
      ;;
    http://*|https://*)
      URL="$1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ "$URL" == *"/health" ]]; then
  printf '{"status":"healthy"}' > "$OUT"
  printf '200'
elif [[ "$URL" == *"/session-ready" ]]; then
  printf '{"status":"PASS","ready":true,"session_id":"stub-session","agent":"codex","transport":"cli-selftest","attempts":1,"sentinel_hits":1}' > "$OUT"
  printf '200'
elif [[ "$URL" == *"/chat" ]]; then
  printf '{"session_id":"stub-session","context":[{"document_id":"knowledge/current-state/reports/gpt-agent-data-access-confirmation.md"}]}' > "$OUT"
  printf '200'
else
  printf '{}' > "$OUT"
  printf '500'
fi
""",
        encoding="utf-8",
    )
    curl_path.chmod(0o755)

    env = {
        "PATH": f"{tmp_path}:{Path('/bin')}:{Path('/usr/bin')}:{Path('/usr/local/bin')}",
        "AGENT_DATA_API_KEY": "test-key",
        "AGENT_DATA_URL": "https://example.invalid/api",
        "AGENT_NAME": "codex",
        "AGENT_TRANSPORT": "cli-selftest",
        "SESSION_ID": "stub-session",
    }

    result = subprocess.run(
        ["bash", "scripts/test-agent-data-session-ready.sh"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
    )

    assert result.returncode == 0
    assert "STATUS=PASS" in result.stdout
    assert "failure_stage=none" in result.stdout
    assert "classification=none" in result.stdout
    assert "session_ready_http=200" in result.stdout
    assert "chat_http=200" in result.stdout
