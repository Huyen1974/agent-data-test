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

    monkeypatch.setattr(server.vector_store, "get_vector_store", lambda: store)
    monkeypatch.setenv("API_KEY", "secret")
    return store


@pytest.mark.unit
@patch("agent_data.server.pubsub_v1.PublisherClient")
def test_ingest_publishes_to_pubsub(mock_pub: MagicMock):
    client = TestClient(server.app)
    # Setup mock publish future
    future = MagicMock()
    future.result.return_value = "msg-123"
    mock_pub.return_value.publish.return_value = future

    payload = {"text": "gs://test-bucket/test.pdf"}
    resp = client.post("/ingest", json=payload)

    assert resp.status_code == 202
    mock_pub.assert_called_once()
    # Verify publish invoked with JSON payload containing gcs_uri
    args, kwargs = mock_pub.return_value.publish.call_args
    assert "projects" in args[0] and "/topics/" in args[0]
    sent = kwargs.get("data") or (args[1] if len(args) > 1 else b"")
    assert b"test-bucket/test.pdf" in sent
    assert isinstance(resp.json().get("content"), str)


@pytest.mark.unit
@patch("agent_data.server.agent")
def test_query_knowledge_calls_agent_llm_response(mock_agent: MagicMock):
    client = TestClient(server.app)

    mock_reply = MagicMock()
    mock_reply.content = "Hello back"
    mock_agent.llm_response.return_value = mock_reply
    mock_agent.history = None
    mock_agent.config = MagicMock(vecdb=None)
    mock_agent.set_session = MagicMock()

    payload = {"query": "Hello", "routing": {"noop_qdrant": True}}
    resp = client.post("/chat", json=payload)

    assert resp.status_code == 200
    mock_agent.llm_response.assert_called_once()
    body = resp.json()
    assert body.get("content") == "Hello back"
    assert body.get("usage", {}).get("qdrant_hits") == 0


@pytest.mark.unit
@patch("agent_data.server.agent")
@patch("agent_data.server._firestore")
def test_query_knowledge_returns_context(mock_fs: MagicMock, mock_agent: MagicMock):
    client = TestClient(server.app)

    mock_agent.history = None
    mock_agent.set_session = MagicMock()
    mock_agent.config = MagicMock(vecdb="qdrant")
    mock_reply = MagicMock()
    mock_reply.content = "Langroid is great"
    mock_agent.llm_response.return_value = mock_reply

    class FakeSnapshot:
        def __init__(self, data):
            self._data = data

        def to_dict(self):
            return self._data

    class FakeCollection:
        def __init__(self, docs):
            self._docs = docs

        def stream(self):
            for doc in self._docs:
                yield FakeSnapshot(doc)

    documents = [
        {
            "document_id": "doc-1",
            "content": {"body": "Langroid helps orchestrate multi-agent systems."},
            "metadata": {"tags": ["langroid", "ai"]},
        }
    ]

    fake_db = MagicMock()
    fake_db.collection.return_value = FakeCollection(documents)
    mock_fs.return_value = fake_db

    payload = {
        "query": "What is Langroid?",
        "filters": {"tags": ["langroid"]},
        "top_k": 3,
    }

    resp = client.post("/chat", json=payload)

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
@patch("agent_data.server._firestore")
def test_create_document_persists_payload(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = False
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    payload = {
        "document_id": "doc-123",
        "parent_id": "root",
        "content": {"mime_type": "text/markdown", "body": "# Intro"},
        "metadata": {"title": "Intro Doc", "tags": ["intro"]},
    }

    resp = client.post("/documents", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    doc_ref.set.assert_called_once()
    stored = doc_ref.set.call_args[0][0]
    assert stored["document_id"] == payload["document_id"]
    assert stored["parent_id"] == payload["parent_id"]
    assert stored["content"] == payload["content"]
    assert stored["metadata"]["title"] == "Intro Doc"
    assert stored["is_human_readable"] is False
    assert stored["revision"] == 1
    assert resp.json()["revision"] == 1
    doc_ref.update.assert_called()
    stub_vector_store.upsert_document.assert_called_once()


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_create_document_conflict_returns_error(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {"document_id": "doc-123"}
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    payload = {
        "document_id": "doc-123",
        "parent_id": "root",
        "content": {"mime_type": "text/plain", "body": "Hello"},
        "metadata": {"title": "Hello"},
    }

    resp = client.post("/documents", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 409
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "CONFLICT"
    assert detail.get("details", {}).get("document_id") == "doc-123"
    stub_vector_store.upsert_document.assert_not_called()


@patch("agent_data.server._firestore")
def test_create_document_sets_vector_status_ready(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    doc_snapshot = MagicMock()
    doc_snapshot.exists = False
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    payload = {
        "document_id": "doc-456",
        "parent_id": "root",
        "content": {"mime_type": "text/plain", "body": "Content"},
        "metadata": {"title": "Doc"},
        "is_human_readable": True,
    }

    resp = client.post("/documents", json=payload, headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    doc_ref.update.assert_called()
    update_payload = doc_ref.update.call_args[0][0]
    assert update_payload["vector_status"] == "ready"
    assert update_payload.get("vector_error") is None


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_update_document_revision_conflict(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "revision": 5,
        "content": {"mime_type": "text/plain", "body": "Hello"},
        "metadata": {"title": "Hello"},
        "is_human_readable": False,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

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
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "CONFLICT"
    assert detail.get("details", {}).get("expected_revision") == 4
    assert detail.get("details", {}).get("actual_revision") == 5


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_update_document_syncs_vector(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "revision": 1,
        "content": {"mime_type": "text/plain", "body": "Old"},
        "metadata": {"title": "Old"},
        "is_human_readable": False,
        "parent_id": "root",
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

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
    updates = doc_ref.update.call_args_list[-1][0][0]
    assert updates["vector_status"] == "ready"


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_update_document_replaces_content_body(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "revision": 4,
        "content": {"mime_type": "text/markdown", "body": "Old body"},
        "metadata": {"title": "Old"},
        "is_human_readable": True,
        "parent_id": "root",
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

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
    doc_ref.update.assert_called()
    first_update = doc_ref.update.call_args_list[0][0][0]
    assert first_update["content"]["body"] == "Updated body"
    assert first_update["metadata"]["title"] == "Updated"
    stub_vector_store.upsert_document.assert_called_once()
    vector_kwargs = stub_vector_store.upsert_document.call_args.kwargs
    assert vector_kwargs["content"] == "Updated body"


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_move_document_updates_parent(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "revision": 2,
        "parent_id": "root",
        "deleted_at": None,
        "content": {"body": "Original body"},
        "metadata": {"title": "Original"},
        "is_human_readable": False,
    }

    parent_snapshot = MagicMock()
    parent_snapshot.exists = True
    parent_snapshot.to_dict.return_value = {"parent_id": "root"}

    doc_ref = MagicMock()
    parent_ref = MagicMock()

    def document_side_effect(doc_id: str):
        if doc_id == "doc-123":
            return doc_ref
        if doc_id == "folder-789":
            return parent_ref
        missing = MagicMock()
        missing.get.return_value = MagicMock(exists=False)
        return missing

    collection = MagicMock()
    collection.document.side_effect = document_side_effect
    doc_ref.get.return_value = doc_snapshot
    parent_ref.get.return_value = parent_snapshot
    mock_fs.return_value.collection.return_value = collection

    payload = {"new_parent_id": "folder-789"}

    resp = client.post(
        "/documents/doc-123/move",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "moved"
    assert doc_ref.update.call_count >= 1
    updates = doc_ref.update.call_args_list[0][0][0]
    assert updates["parent_id"] == "folder-789"
    assert updates["revision"] == 3
    stub_vector_store.upsert_document.assert_called_once()


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_move_document_minimal_payload_updates_parent(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """Ensure the move API only requires new_parent_id and updates Firestore."""

    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    stub_vector_store.upsert_document.return_value = VectorSyncResult(status="ready")

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "revision": 7,
        "parent_id": "folder-old",
        "deleted_at": None,
        "content": {"body": "Body"},
        "metadata": {"title": "Title"},
        "is_human_readable": True,
    }

    parent_snapshot = MagicMock()
    parent_snapshot.exists = True

    doc_ref = MagicMock()
    parent_ref = MagicMock()

    def document_side_effect(doc_id: str):
        if doc_id == "doc-xyz":
            return doc_ref
        if doc_id == "folder-new":
            return parent_ref
        missing = MagicMock()
        missing.get.return_value = MagicMock(exists=False)
        return missing

    collection = MagicMock()
    collection.document.side_effect = document_side_effect
    doc_ref.get.return_value = doc_snapshot
    parent_ref.get.return_value = parent_snapshot
    mock_fs.return_value.collection.return_value = collection

    resp = client.post(
        "/documents/doc-xyz/move",
        json={"new_parent_id": "folder-new"},
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "moved"
    updates = doc_ref.update.call_args_list[0][0][0]
    assert updates["parent_id"] == "folder-new"
    assert updates["revision"] == 8
    stub_vector_store.upsert_document.assert_called_once()


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_move_document_detects_cycle(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "revision": 1,
        "parent_id": "root",
        "deleted_at": None,
    }

    child_snapshot = MagicMock()
    child_snapshot.exists = True
    child_snapshot.to_dict.return_value = {"parent_id": "doc-123"}

    doc_ref = MagicMock()
    child_ref = MagicMock()

    def document_side_effect(doc_id: str):
        if doc_id == "doc-123":
            return doc_ref
        if doc_id == "child-1":
            return child_ref
        missing = MagicMock()
        missing.get.return_value = MagicMock(exists=False)
        return missing

    collection = MagicMock()
    collection.document.side_effect = document_side_effect
    doc_ref.get.return_value = doc_snapshot
    child_ref.get.return_value = child_snapshot
    mock_fs.return_value.collection.return_value = collection

    payload = {"new_parent_id": "child-1"}

    resp = client.post(
        "/documents/doc-123/move",
        json=payload,
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 400
    detail = resp.json().get("detail", {})
    assert detail.get("code") == "INVALID_ARGUMENT"
    assert detail.get("details", {}).get("parent_id") == "child-1"


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_delete_document_marks_deleted(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {"revision": 3}
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.delete("/documents/doc-123", headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    stub_vector_store.delete_document.assert_called_once_with("doc-123")
    assert resp.json()["revision"] == 4
    doc_ref.update.assert_called_once()
    updates = doc_ref.update.call_args[0][0]
    assert updates["vector_status"] == "deleted"
    assert updates["revision"] == 4
    assert "deleted_at" in updates


# ---------------------------------------------------------------------------
# TD-011: GET /documents/{path} (truncated + vector search)
# ---------------------------------------------------------------------------
@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_get_document_truncated_by_default(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    long_body = "A" * 1000
    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "document_id": "knowledge/dev/long-doc.md",
        "content": {"mime_type": "text/markdown", "body": long_body},
        "metadata": {"title": "Long Doc"},
        "revision": 2,
        "deleted_at": None,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

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
@patch("agent_data.server._firestore")
def test_get_document_full_returns_complete(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    long_body = "B" * 1000
    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "document_id": "knowledge/dev/full-doc.md",
        "content": {"body": long_body},
        "metadata": {"title": "Full"},
        "revision": 1,
        "deleted_at": None,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

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
@patch("agent_data.server._firestore")
def test_get_document_not_found(mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = False
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.get(
        "/documents/knowledge/missing",
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 404


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_get_document_short_content_not_truncated(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    short_body = "Hello world"
    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "document_id": "test/short",
        "content": {"body": short_body},
        "metadata": {"title": "Short"},
        "revision": 1,
        "deleted_at": None,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.get("/documents/test/short", headers={"x-api-key": "secret"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["truncated"] is False
    assert body["content"] == short_body


# ---------------------------------------------------------------------------
# TD-009: PATCH /documents/{path}
# ---------------------------------------------------------------------------
@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_patch_document_replaces_string(
    mock_fs: MagicMock,
    stub_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "document_id": "knowledge/dev/doc.md",
        "content": {"mime_type": "text/markdown", "body": "Hello world, this is a test."},
        "metadata": {"title": "Doc"},
        "revision": 3,
        "deleted_at": None,
        "parent_id": "knowledge/dev",
        "is_human_readable": False,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.patch(
        "/documents/knowledge/dev/doc.md",
        json={"old_str": "Hello world", "new_str": "Hi earth"},
        headers={"x-api-key": "secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "patched"
    assert body["revision"] == 4
    assert doc_ref.update.call_count >= 1
    stored = doc_ref.update.call_args_list[0][0][0]
    assert stored["content"]["body"] == "Hi earth, this is a test."


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_patch_document_not_found(mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = False
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.patch(
        "/documents/knowledge/missing",
        json={"old_str": "foo", "new_str": "bar"},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 404


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_patch_document_old_str_missing(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "content": {"body": "Actual content here"},
        "metadata": {"title": "X"},
        "revision": 1,
        "deleted_at": None,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.patch(
        "/documents/test/doc",
        json={"old_str": "NOT IN CONTENT", "new_str": "bar"},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "NOT_FOUND_IN_CONTENT"


@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_patch_document_ambiguous_match(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "content": {"body": "foo bar foo baz"},
        "metadata": {"title": "X"},
        "revision": 1,
        "deleted_at": None,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

    resp = client.patch(
        "/documents/test/doc",
        json={"old_str": "foo", "new_str": "qux"},
        headers={"x-api-key": "secret"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "AMBIGUOUS"


# ---------------------------------------------------------------------------
# TD-010: POST /documents/batch
# ---------------------------------------------------------------------------
@pytest.mark.unit
@patch("agent_data.server._firestore")
def test_batch_read_multiple_docs(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    def make_snap(doc_id, body, title, revision):
        s = MagicMock()
        s.exists = True
        s.to_dict.return_value = {
            "document_id": doc_id,
            "content": {"body": body},
            "metadata": {"title": title},
            "revision": revision,
            "deleted_at": None,
        }
        return s

    snap1 = make_snap("doc/a", "A" * 600, "Doc A", 1)
    snap2 = make_snap("doc/b", "Short", "Doc B", 2)

    missing_snap = MagicMock()
    missing_snap.exists = False

    def doc_side_effect(key):
        ref = MagicMock()
        if "doc__a" in key:
            ref.get.return_value = snap1
        elif "doc__b" in key:
            ref.get.return_value = snap2
        else:
            ref.get.return_value = missing_snap
        return ref

    mock_fs.return_value.collection.return_value.document.side_effect = doc_side_effect

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
@patch("agent_data.server._firestore")
def test_batch_read_full_mode(
    mock_fs: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("API_KEY", "secret")
    client = TestClient(server.app)

    big_body = "C" * 800
    doc_snapshot = MagicMock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = {
        "document_id": "doc/c",
        "content": {"body": big_body},
        "metadata": {"title": "C"},
        "revision": 1,
        "deleted_at": None,
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = doc_snapshot
    mock_fs.return_value.collection.return_value.document.return_value = doc_ref

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
