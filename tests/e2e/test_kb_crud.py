from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server

pytestmark = pytest.mark.e2e


def _setup_pg_mocks():
    """Set agent.db = True and return pg_store patches + in-memory store."""
    server.agent.db = True
    store: dict[str, dict] = {}

    def fake_get(collection, key):
        return store.get(key)

    def fake_set(collection, key, data):
        store[key] = dict(data)

    def fake_update(collection, key, updates):
        if key in store:
            store[key].update(updates)

    def fake_stream(collection):
        return [{"_key": k, **v} for k, v in store.items()]

    return store, fake_get, fake_set, fake_update, fake_stream


@patch("agent_data.pg_store.stream_docs")
@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.get_doc")
def test_kb_crud_endpoints(mock_get, mock_set, mock_update, mock_stream, monkeypatch):
    store, fake_get, fake_set, fake_update, fake_stream = _setup_pg_mocks()
    mock_get.side_effect = fake_get
    mock_set.side_effect = fake_set
    mock_update.side_effect = fake_update
    mock_stream.side_effect = fake_stream

    client = TestClient(server.app)
    monkeypatch.setenv("API_KEY", "test-key")

    # Create
    r = client.post(
        "/documents",
        json={
            "document_id": "kb-doc-001",
            "parent_id": "root",
            "content": {
                "mime_type": "text/markdown",
                "body": "Hello KB",
            },
            "metadata": {
                "title": "Hello KB",
                "source": "unit",
            },
            "is_human_readable": True,
        },
        headers={"x-api-key": "test-key"},
    )
    assert r.status_code == 200
    doc = r.json()
    doc_id = doc["id"]
    assert doc["status"] == "created"

    # Update
    r2 = client.put(
        f"/documents/{doc_id}",
        json={
            "document_id": doc_id,
            "patch": {
                "content": {
                    "mime_type": "text/markdown",
                    "body": "Hello KB v2",
                },
                "metadata": {
                    "title": "Hello KB v2",
                    "version": 2,
                },
            },
            "update_mask": ["content", "metadata"],
            "last_known_revision": 1,
        },
        headers={"x-api-key": "test-key"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "updated"

    # Soft delete
    r3 = client.delete(f"/documents/{doc_id}", headers={"x-api-key": "test-key"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "deleted"
