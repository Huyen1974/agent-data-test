from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server
from agent_data.vector_store import VectorSyncResult


@pytest.fixture(autouse=True)
def stub_vector_store(monkeypatch: pytest.MonkeyPatch):
    store = MagicMock()
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

    payload = {
        "document_id": "doc-123",
        "new_parent_id": "folder-789",
        "position": {"ordering": 5},
    }

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
    assert updates["ordering"] == 5
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

    payload = {
        "document_id": "doc-123",
        "new_parent_id": "child-1",
    }

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
