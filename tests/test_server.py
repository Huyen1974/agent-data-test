from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server
from agent_data.vector_store import VectorSyncResult


@pytest.fixture(autouse=True)
def stub_vector_store(monkeypatch: pytest.MonkeyPatch):
    store = MagicMock()
    store.enabled = False
    store.upsert_document.return_value = VectorSyncResult(status="skipped")
    store.delete_document.return_value = VectorSyncResult(status="deleted")
    store.update_metadata.return_value = VectorSyncResult(status="skipped")

    monkeypatch.setattr(server.vector_store, "get_vector_store", lambda: store)
    monkeypatch.setenv("API_KEY", "secret")
    return store


@pytest.mark.unit
def test_ingest_gcs_uri_returns_disabled(monkeypatch):
    """Posting a GCS URI to /ingest returns a disabled message."""
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    payload = {"text": "gs://test-bucket/test.pdf"}
    resp = client.post("/ingest", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 202
    body = resp.json()
    assert "disabled" in body.get("content", "").lower()


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.set_doc")
def test_ingest_inline_text_returns_202(
    mock_set_doc: MagicMock, mock_ensure_pg: MagicMock, monkeypatch
):
    """Posting inline text to /ingest returns 202."""
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    payload = {"text": "Some inline knowledge text"}
    resp = client.post("/ingest", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 202
    assert isinstance(resp.json().get("content"), str)


@pytest.mark.unit
@patch("agent_data.server.agent")
def test_query_knowledge_calls_agent_llm_response(mock_agent: MagicMock, monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    client = TestClient(server.app)

    mock_reply = MagicMock()
    mock_reply.content = "Hello back"
    mock_agent.llm_response.return_value = mock_reply
    mock_agent.history = None
    mock_agent.config = MagicMock(vecdb=None)
    mock_agent.set_session = MagicMock()

    payload = {"query": "Hello", "routing": {"noop_qdrant": True}}
    resp = client.post("/chat", json=payload, headers={"x-api-key": "test-key"})

    assert resp.status_code == 200
    mock_agent.llm_response.assert_called_once()
    body = resp.json()
    assert body.get("content") == "Hello back"
    assert body.get("usage", {}).get("qdrant_hits") == 0


@pytest.mark.unit
@patch("agent_data.server.agent")
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.stream_docs")
def test_query_knowledge_returns_context(
    mock_stream: MagicMock, mock_ensure_pg: MagicMock, mock_agent: MagicMock, monkeypatch
):
    monkeypatch.setenv("API_KEY", "test-key")
    client = TestClient(server.app)

    mock_agent.history = None
    mock_agent.set_session = MagicMock()
    mock_agent.config = MagicMock(vecdb="qdrant")
    mock_reply = MagicMock()
    mock_reply.content = "Langroid is great"
    mock_agent.llm_response.return_value = mock_reply

    documents = [
        {
            "_key": "doc-1",
            "document_id": "doc-1",
            "content": {"body": "Langroid helps orchestrate multi-agent systems."},
            "metadata": {"tags": ["langroid", "ai"]},
        }
    ]

    mock_stream.return_value = documents

    payload = {
        "query": "What is Langroid?",
        "filters": {"tags": ["langroid"]},
        "top_k": 3,
    }

    resp = client.post("/chat", json=payload, headers={"x-api-key": "test-key"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["context"][0]["document_id"] == "doc-1"
    assert data["usage"]["qdrant_hits"] == 1


@pytest.mark.unit
def test_metrics_endpoint_exposes_custom_metrics():
    client = TestClient(server.app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text or ""
    # Verify our custom metric names are present in exposition
    assert "agent_chat_messages_total" in body
    assert "agent_ingest_success_total" in body
    assert "agent_rag_query_latency_seconds" in body


@pytest.mark.unit
def test_health_endpoint_ok():
    client = TestClient(server.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert {"status", "version", "langroid_available"}.issubset(body.keys())


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.get_doc")
def test_create_document_persists_payload(
    mock_get_doc: MagicMock,
    mock_set_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    # Document does not exist yet
    mock_get_doc.return_value = None

    payload = {
        "document_id": "doc-123",
        "parent_id": "root",
        "content": {"mime_type": "text/markdown", "body": "# Intro"},
        "metadata": {"title": "Intro Doc", "tags": ["intro"]},
    }

    resp = client.post("/documents", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    mock_set_doc.assert_called_once()
    stored = mock_set_doc.call_args[0][2]  # third positional arg is data
    assert stored["document_id"] == payload["document_id"]
    assert stored["parent_id"] == payload["parent_id"]
    assert stored["content"]["body"] == "# Intro"
    assert stored["metadata"]["title"] == "Intro Doc"
    assert stored["is_human_readable"] is False
    assert stored["revision"] == 1
    assert resp.json()["revision"] == 1
    stub_vector_store.upsert_document.assert_called_once()


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_create_document_conflict_returns_error(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    # Document already exists
    mock_get_doc.return_value = {"document_id": "doc-123", "deleted_at": None}

    payload = {
        "document_id": "doc-123",
        "parent_id": "root",
        "content": {"mime_type": "text/plain", "body": "Hello"},
        "metadata": {"title": "Hello"},
    }

    resp = client.post("/documents", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 409
    detail = resp.json()
    assert detail.get("code") == "CONFLICT"
    assert detail.get("details", {}).get("document_id") == "doc-123"
    stub_vector_store.upsert_document.assert_not_called()


@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.get_doc")
def test_create_document_sets_vector_status_ready(
    mock_get_doc: MagicMock,
    mock_set_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    # Document does not exist yet
    mock_get_doc.return_value = None

    payload = {
        "document_id": "doc-456",
        "parent_id": "root",
        "content": {"mime_type": "text/plain", "body": "Content"},
        "metadata": {"title": "Doc"},
        "is_human_readable": True,
    }

    resp = client.post("/documents", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    # vector_status is set via update_doc after vector sync
    mock_update_doc.assert_called()
    update_payload = mock_update_doc.call_args[0][2]
    assert update_payload["vector_status"] == "ready"
    assert update_payload.get("vector_error") is None


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.get_doc")
def test_update_document_revision_conflict(
    mock_get_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = {
        "revision": 5,
        "content": {"mime_type": "text/plain", "body": "Hello"},
        "metadata": {"title": "Hello"},
        "is_human_readable": False,
    }

    payload = {
        "document_id": "doc-123",
        "patch": {
            "metadata": {"title": "Hello v2"},
        },
        "update_mask": ["metadata"],
        "last_known_revision": 4,
    }

    resp = client.put(
        "/documents/doc-123",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 409
    detail = resp.json()
    assert detail.get("code") == "CONFLICT"
    assert detail.get("details", {}).get("expected_revision") == 4
    assert detail.get("details", {}).get("actual_revision") == 5


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.get_doc")
def test_update_document_syncs_vector(
    mock_get_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    mock_get_doc.return_value = {
        "revision": 1,
        "content": {"mime_type": "text/plain", "body": "Old"},
        "metadata": {"title": "Old"},
        "is_human_readable": False,
        "parent_id": "root",
    }

    payload = {
        "document_id": "doc-123",
        "patch": {
            "content": {"mime_type": "text/plain", "body": "New body"},
            "metadata": {"title": "New"},
        },
        "update_mask": ["content", "metadata"],
        "last_known_revision": 1,
    }

    resp = client.put(
        "/documents/doc-123",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    stub_vector_store.upsert_document.assert_called_once()
    vector_args = stub_vector_store.upsert_document.call_args.kwargs
    assert vector_args["content"] == "New body"
    assert vector_args["metadata"]["title"] == "New"
    # update_doc should have been called with vector_status
    assert mock_update_doc.call_count >= 2
    last_update = mock_update_doc.call_args_list[-1][0][2]
    assert last_update["vector_status"] == "ready"


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.get_doc")
def test_update_document_replaces_content_body(
    mock_get_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    mock_get_doc.return_value = {
        "revision": 4,
        "content": {"mime_type": "text/markdown", "body": "Old body"},
        "metadata": {"title": "Old"},
        "is_human_readable": True,
        "parent_id": "root",
    }

    payload = {
        "document_id": "doc-abc",
        "patch": {
            "content": {"mime_type": "text/markdown", "body": "Updated body"},
            "metadata": {"title": "Updated"},
        },
        "update_mask": ["content", "metadata"],
        "last_known_revision": 4,
    }

    resp = client.put(
        "/documents/doc-abc",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    mock_update_doc.assert_called()
    first_update = mock_update_doc.call_args_list[0][0][2]
    assert first_update["content"]["body"] == "Updated body"
    assert first_update["metadata"]["title"] == "Updated"
    stub_vector_store.upsert_document.assert_called_once()
    vector_kwargs = stub_vector_store.upsert_document.call_args.kwargs
    assert vector_kwargs["content"] == "Updated body"


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.get_doc")
def test_move_document_updates_parent(
    mock_get_doc: MagicMock,
    mock_set_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.update_metadata.return_value = VectorSyncResult(status="ready")

    doc_data = {
        "revision": 2,
        "parent_id": "root",
        "deleted_at": None,
        "content": {"body": "Original body"},
        "metadata": {"title": "Original"},
        "is_human_readable": False,
    }

    parent_data = {"parent_id": "root"}

    def get_doc_side_effect(collection, key):
        if key == "doc-123":
            return doc_data
        if key == "folder-789":
            return parent_data
        return None

    mock_get_doc.side_effect = get_doc_side_effect

    payload = {"new_parent_id": "folder-789"}

    resp = client.post(
        "/documents/doc-123/move",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "moved"
    mock_update_doc.assert_called()
    updates = mock_update_doc.call_args_list[0][0][2]
    assert updates["parent_id"] == "folder-789"
    assert updates["revision"] == 3
    stub_vector_store.update_metadata.assert_called_once()
    stub_vector_store.upsert_document.assert_not_called()


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.get_doc")
def test_move_document_minimal_payload_updates_parent(
    mock_get_doc: MagicMock,
    mock_set_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """Ensure the move API only requires new_parent_id and updates pg_store."""

    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.update_metadata.return_value = VectorSyncResult(status="ready")

    doc_data = {
        "revision": 7,
        "parent_id": "folder-old",
        "deleted_at": None,
        "content": {"body": "Body"},
        "metadata": {"title": "Title"},
        "is_human_readable": True,
    }

    parent_data = {"parent_id": "root"}

    def get_doc_side_effect(collection, key):
        if key == "doc-xyz":
            return doc_data
        if key == "folder-new":
            return parent_data
        return None

    mock_get_doc.side_effect = get_doc_side_effect

    resp = client.post(
        "/documents/doc-xyz/move",
        json={"new_parent_id": "folder-new"},
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "moved"
    updates = mock_update_doc.call_args_list[0][0][2]
    assert updates["parent_id"] == "folder-new"
    assert updates["revision"] == 8
    stub_vector_store.update_metadata.assert_called_once()
    stub_vector_store.upsert_document.assert_not_called()


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_move_document_detects_cycle(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_data = {
        "revision": 1,
        "parent_id": "root",
        "deleted_at": None,
    }

    child_data = {"parent_id": "doc-123"}

    def get_doc_side_effect(collection, key):
        if key == "doc-123":
            return doc_data
        if key == "child-1":
            return child_data
        return None

    mock_get_doc.side_effect = get_doc_side_effect

    payload = {"new_parent_id": "child-1"}

    resp = client.post(
        "/documents/doc-123/move",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 400
    detail = resp.json()
    assert detail.get("code") == "INVALID_ARGUMENT"
    assert detail.get("details", {}).get("parent_id") == "child-1"


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.get_doc")
def test_delete_document_marks_deleted(
    mock_get_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = {"revision": 3}

    resp = client.delete("/documents/doc-123", headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    stub_vector_store.delete_document.assert_called_once_with("doc-123")
    assert resp.json()["revision"] == 4
    mock_update_doc.assert_called_once()
    updates = mock_update_doc.call_args[0][2]
    assert updates["vector_status"] == "deleted"
    assert updates["revision"] == 4
    assert "deleted_at" in updates


# ---------------------------------------------------------------------------
# TD-011: GET /documents/{path} (truncated + vector search)
# ---------------------------------------------------------------------------
@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_get_document_truncated_by_default(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    long_body = "A" * 1000
    mock_get_doc.return_value = {
        "document_id": "knowledge/dev/long-doc.md",
        "content": {"mime_type": "text/markdown", "body": long_body},
        "metadata": {"title": "Long Doc"},
        "revision": 2,
        "deleted_at": None,
    }

    resp = client.get(
        "/documents/knowledge/dev/long-doc.md",
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["truncated"] is True
    assert len(body["content"]) == 500
    assert body["content_length"] == 1000
    assert body["revision"] == 2
    assert "related" in body


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_get_document_full_returns_complete(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    long_body = "B" * 1000
    mock_get_doc.return_value = {
        "document_id": "knowledge/dev/full-doc.md",
        "content": {"body": long_body},
        "metadata": {"title": "Full"},
        "revision": 1,
        "deleted_at": None,
    }

    resp = client.get(
        "/documents/knowledge/dev/full-doc.md?full=true",
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["truncated"] is False
    assert len(body["content"]) == 1000
    assert "related" not in body


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_get_document_not_found(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = None

    resp = client.get(
        "/documents/knowledge/missing",
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 404


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_get_document_short_content_not_truncated(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    short_body = "Hello world"
    mock_get_doc.return_value = {
        "document_id": "test/short",
        "content": {"body": short_body},
        "metadata": {"title": "Short"},
        "revision": 1,
        "deleted_at": None,
    }

    resp = client.get("/documents/test/short", headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["truncated"] is False
    assert body["content"] == short_body


# ---------------------------------------------------------------------------
# TD-009: PATCH /documents/{path}
# ---------------------------------------------------------------------------
@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.get_doc")
def test_patch_document_replaces_string(
    mock_get_doc: MagicMock,
    mock_update_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = {
        "document_id": "knowledge/dev/doc.md",
        "content": {
            "mime_type": "text/markdown",
            "body": "Hello world, this is a test.",
        },
        "metadata": {"title": "Doc"},
        "revision": 3,
        "deleted_at": None,
        "parent_id": "knowledge/dev",
        "is_human_readable": False,
    }

    resp = client.patch(
        "/documents/knowledge/dev/doc.md",
        json={"old_str": "Hello world", "new_str": "Hi earth"},
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "patched"
    assert body["revision"] == 4
    assert mock_update_doc.call_count >= 1
    stored = mock_update_doc.call_args_list[0][0][2]
    assert stored["content"]["body"] == "Hi earth, this is a test."


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_patch_document_not_found(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = None

    resp = client.patch(
        "/documents/knowledge/missing",
        json={"old_str": "foo", "new_str": "bar"},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 404


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_patch_document_old_str_missing(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = {
        "content": {"body": "Actual content here"},
        "metadata": {"title": "X"},
        "revision": 1,
        "deleted_at": None,
    }

    resp = client.patch(
        "/documents/test/doc",
        json={"old_str": "NOT IN CONTENT", "new_str": "bar"},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "NOT_FOUND_IN_CONTENT"


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_patch_document_ambiguous_match(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    mock_get_doc.return_value = {
        "content": {"body": "foo bar foo baz"},
        "metadata": {"title": "X"},
        "revision": 1,
        "deleted_at": None,
    }

    resp = client.patch(
        "/documents/test/doc",
        json={"old_str": "foo", "new_str": "qux"},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "AMBIGUOUS"


# ---------------------------------------------------------------------------
# TD-010: POST /documents/batch
# ---------------------------------------------------------------------------
@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_batch_read_multiple_docs(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_a = {
        "document_id": "doc/a",
        "content": {"body": "A" * 600},
        "metadata": {"title": "Doc A"},
        "revision": 1,
        "deleted_at": None,
    }
    doc_b = {
        "document_id": "doc/b",
        "content": {"body": "Short"},
        "metadata": {"title": "Doc B"},
        "revision": 2,
        "deleted_at": None,
    }

    def get_doc_side_effect(collection, key):
        if key == "doc__a":
            return doc_a
        if key == "doc__b":
            return doc_b
        return None

    mock_get_doc.side_effect = get_doc_side_effect

    resp = client.post(
        "/documents/batch",
        json={"paths": ["doc/a", "doc/b", "doc/missing"]},
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3

    # First doc is truncated
    assert body["items"][0]["truncated"] is True
    assert len(body["items"][0]["content"]) == 500
    assert body["items"][0]["content_length"] == 600

    # Second doc is short, not truncated
    assert body["items"][1]["truncated"] is False
    assert body["items"][1]["content"] == "Short"

    # Third doc is missing
    assert body["items"][2]["error"] == "not_found"


@pytest.mark.unit
@patch("agent_data.server._ensure_pg", return_value=True)
@patch("agent_data.pg_store.get_doc")
def test_batch_read_full_mode(
    mock_get_doc: MagicMock,
    mock_ensure_pg: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    big_body = "C" * 800
    mock_get_doc.return_value = {
        "document_id": "doc/c",
        "content": {"body": big_body},
        "metadata": {"title": "C"},
        "revision": 1,
        "deleted_at": None,
    }

    resp = client.post(
        "/documents/batch",
        json={"paths": ["doc/c"], "full": True},
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"][0]["truncated"] is False
    assert len(body["items"][0]["content"]) == 800


@pytest.mark.unit
def test_batch_read_empty_paths_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    resp = client.post(
        "/documents/batch",
        json={"paths": []},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 422  # validation error


@pytest.mark.unit
def test_batch_read_exceeds_max_rejected(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    paths = [f"doc/{i}" for i in range(21)]
    resp = client.post(
        "/documents/batch",
        json={"paths": paths},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 422  # validation error
