import os

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server

_openai_key = os.getenv("OPENAI_API_KEY", "")
_has_openai = _openai_key and _openai_key not in ("xxx", "test", "placeholder")


@pytest.mark.unit
@pytest.mark.skipif(not _has_openai, reason="OPENAI_API_KEY not set")
def test_server_ingest_and_query_local_fixture():
    app = server.app
    client = TestClient(app)

    ingest_uri = "gs://huyen1974-agent-data-knowledge-test/e2e_doc.txt"

    r1 = client.post("/chat", json={"message": f"Please ingest from {ingest_uri}"})
    assert r1.status_code == 200

    r2 = client.post(
        "/chat",
        json={"message": "What does the document say about Langroid?"},
    )
    assert r2.status_code == 200
    assert "framework" in r2.json()["response"].lower()
