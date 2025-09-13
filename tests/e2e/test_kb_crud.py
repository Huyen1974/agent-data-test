import pytest
from fastapi.testclient import TestClient

import agent_data.server as server


class _Snap:
    def __init__(self, data):
        self._data = dict(data)

    @property
    def exists(self):
        return True

    def to_dict(self):
        return dict(self._data)


class _Doc:
    def __init__(self, store, doc_id):
        self._store = store
        self._id = doc_id

    def set(self, data):
        self._store[self._id] = dict(data)

    def update(self, updates):
        self._store[self._id].update(dict(updates))

    def get(self):
        return _Snap(self._store[self._id])


class _Col:
    def __init__(self, buckets):
        self._buckets = buckets

    def document(self, doc_id):
        return _Doc(self._buckets, doc_id)


class _FS:
    def __init__(self):
        self._collections = {}

    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = {}
        return _Col(self._collections[name])


pytestmark = pytest.mark.e2e


def _setup_fake_db(monkeypatch):
    fake = _FS()
    monkeypatch.setattr(server, "agent", server.agent)
    server.agent.db = fake
    return fake


def test_kb_crud_endpoints(monkeypatch):
    _setup_fake_db(monkeypatch)
    client = TestClient(server.app)
    monkeypatch.setenv("API_KEY", "test-key")

    # Create
    r = client.post(
        "/documents",
        json={"content": "Hello KB", "metadata": {"source": "unit"}},
        headers={"x-api-key": "test-key"},
    )
    assert r.status_code == 200
    doc = r.json()
    doc_id = doc["id"]
    assert doc["status"] == "created"

    # Update
    r2 = client.put(
        f"/documents/{doc_id}",
        json={"content": "Hello KB v2", "metadata": {"v": 2}},
        headers={"x-api-key": "test-key"},
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "updated"

    # Soft delete
    r3 = client.delete(f"/documents/{doc_id}", headers={"x-api-key": "test-key"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "deleted"
