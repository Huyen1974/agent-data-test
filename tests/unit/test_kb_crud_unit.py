"""Unit tests for KB CRUD endpoints using pg_store mocks."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server

pytestmark = pytest.mark.unit


def _setup_db(monkeypatch):
    """Mark agent.db as available so _ensure_pg() passes."""
    monkeypatch.setattr(server, "agent", server.agent)
    server.agent.db = True


@patch("agent_data.pg_store.update_doc")
@patch("agent_data.pg_store.set_doc")
@patch("agent_data.pg_store.get_doc")
def test_kb_crud_endpoints_unit(mock_get, mock_set, mock_update, monkeypatch):
    _setup_db(monkeypatch)
    monkeypatch.setenv("API_KEY", "test-key")

    # In-memory store to simulate pg_store behavior
    store: dict[str, dict] = {}

    def fake_get(collection, key):
        return store.get(key)

    def fake_set(collection, key, data):
        store[key] = dict(data)

    def fake_update(collection, key, updates):
        if key in store:
            store[key].update(updates)

    mock_get.side_effect = fake_get
    mock_set.side_effect = fake_set
    mock_update.side_effect = fake_update

    client = TestClient(server.app)

    # Create
    create_payload = {
        "document_id": "doc-crud-1",
        "parent_id": "root",
        "content": {"mime_type": "text/plain", "body": "Hello KB"},
        "metadata": {"title": "Hello KB", "source": "unit"},
        "is_human_readable": True,
    }
    r = client.post(
        "/documents",
        json=create_payload,
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
                    "mime_type": "text/plain",
                    "body": "Hello KB v2",
                },
                "metadata": {"title": "Hello KB", "v": 2},
            },
            "update_mask": ["content", "metadata"],
            "last_known_revision": 1,
        },
        headers={"x-api-key": "test-key"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "updated"
    assert r2.json()["revision"] == 2

    # Soft delete
    r3 = client.delete(f"/documents/{doc_id}", headers={"x-api-key": "test-key"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "deleted"
