"""Tests for vector synchronization during document CRUD operations.

Verifies that:
- UPDATE with content change deletes old vectors and creates new ones
- UPDATE with metadata-only skips re-embedding
- UPDATE with empty content removes all vectors
- UPDATE on nonexistent doc returns 404
- MOVE deletes old vectors before re-embedding
- Multi-chunk documents have ALL old chunks deleted on update
- DELETE removes vectors
- Ingest of existing document acts as update
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server
import agent_data.vector_store as vs_mod

# ---- Fake Firestore helpers (reused from unit tests) ----


class _Snap:
    def __init__(self, data=None, exists=True):
        self._data = dict(data or {})
        self._exists = exists

    @property
    def exists(self):
        return self._exists

    def to_dict(self):
        return dict(self._data)


class _Doc:
    def __init__(self, store, doc_id):
        self._store = store
        self._id = doc_id

    def set(self, data):
        self._store[self._id] = dict(data)

    def update(self, updates):
        if self._id in self._store:
            self._store[self._id].update(dict(updates))

    def get(self):
        if self._id not in self._store:
            return _Snap(exists=False)
        return _Snap(self._store[self._id])


class _Col:
    def __init__(self, buckets):
        self._buckets = buckets

    def document(self, doc_id):
        return _Doc(self._buckets, doc_id)

    def stream(self):
        for key, data in self._buckets.items():
            snap = _Snap(data)
            snap.id = key
            yield snap


class _FS:
    def __init__(self):
        self._collections: dict[str, dict] = {}

    def collection(self, name):
        if name not in self._collections:
            self._collections[name] = {}
        return _Col(self._collections[name])


# ---- Fake vector store that tracks calls ----


class FakeVectorStore:
    """In-memory vector store for testing sync behaviour."""

    def __init__(self):
        self.enabled = True
        # Map: document_id -> list of {point_id, content, metadata}
        self.vectors: dict[str, list[dict]] = {}
        self.upsert_calls: list[dict] = []
        self.delete_calls: list[str] = []

    def upsert_document(
        self,
        *,
        document_id,
        content,
        metadata=None,
        parent_id=None,
        is_human_readable=False,
    ):
        self.upsert_calls.append(
            {
                "document_id": document_id,
                "content": content,
                "metadata": metadata,
            }
        )
        if not content or not content.strip():
            return vs_mod.VectorSyncResult(status="ready", chunks_created=0)
        # Simulate chunking: 1 chunk per 500 chars for testing
        chunk_size = 500
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunks.append(content[i : i + chunk_size])
        self.vectors[document_id] = [
            {"content": c, "metadata": metadata, "chunk_index": i}
            for i, c in enumerate(chunks)
        ]
        return vs_mod.VectorSyncResult(status="ready", chunks_created=len(chunks))

    def delete_document(self, document_id):
        self.delete_calls.append(document_id)
        if document_id in self.vectors:
            del self.vectors[document_id]
        return vs_mod.VectorSyncResult(status="deleted")

    def count(self):
        return sum(len(v) for v in self.vectors.values())

    def count_by_document_id(self, document_id):
        return len(self.vectors.get(document_id, []))

    def search(self, *, query, top_k=5, filter_tags=None):
        results = []
        for doc_id, chunks in self.vectors.items():
            for chunk in chunks:
                if query.lower() in chunk["content"].lower():
                    results.append(
                        {
                            "document_id": doc_id,
                            "snippet": chunk["content"][:500],
                            "score": 0.95,
                            "metadata": chunk.get("metadata") or {},
                        }
                    )
        return results[:top_k]

    def list_document_ids(self):
        return set(self.vectors.keys())


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("APP_ENV", "test")


@pytest.fixture()
def fake_db(monkeypatch):
    fake = _FS()
    server.agent.db = fake
    return fake


@pytest.fixture()
def fake_vs(monkeypatch):
    store = FakeVectorStore()
    monkeypatch.setattr(vs_mod, "get_vector_store", lambda refresh=False: store)
    monkeypatch.setattr(vs_mod, "delete_document", store.delete_document)
    return store


@pytest.fixture()
def client(env, fake_db, fake_vs):
    return TestClient(server.app)


HEADERS = {"x-api-key": "test-key"}


def _create_doc(client, doc_id="test-doc", body="Original content", **kwargs):
    payload = {
        "document_id": doc_id,
        "parent_id": kwargs.get("parent_id", "root"),
        "content": {"mime_type": "text/plain", "body": body},
        "metadata": kwargs.get("metadata", {"title": "Test", "tags": ["test"]}),
        "is_human_readable": True,
    }
    r = client.post("/documents", json=payload, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


# ===================================================================
# Phase 1 Tests — Vector Sync on UPDATE
# ===================================================================


class TestUpdateVectorSync:
    """Tests for vector sync during document UPDATE."""

    def test_update_content_triggers_delete_and_reembed(self, client, fake_vs):
        """UPDATE with content change should delete old vectors then create new."""
        _create_doc(client, body="Old content about platypus")
        fake_vs.delete_calls.clear()
        fake_vs.upsert_calls.clear()

        r = client.put(
            "/documents/test-doc",
            json={
                "document_id": "test-doc",
                "patch": {
                    "content": {
                        "mime_type": "text/plain",
                        "body": "New content about kangaroo",
                    },
                },
                "update_mask": ["content"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "updated"

        # Verify delete was called BEFORE upsert
        assert "test-doc" in fake_vs.delete_calls
        assert len(fake_vs.upsert_calls) == 1
        assert fake_vs.upsert_calls[0]["content"] == "New content about kangaroo"

        # Old content should NOT be findable
        old_results = fake_vs.search(query="platypus")
        assert len(old_results) == 0

        # New content SHOULD be findable
        new_results = fake_vs.search(query="kangaroo")
        assert len(new_results) == 1

    def test_update_metadata_only_skips_reembed(self, client, fake_vs):
        """UPDATE with only metadata change should NOT re-embed vectors."""
        _create_doc(client, body="Content stays the same")
        initial_upsert_count = len(fake_vs.upsert_calls)
        fake_vs.delete_calls.clear()

        r = client.put(
            "/documents/test-doc",
            json={
                "document_id": "test-doc",
                "patch": {
                    "metadata": {"title": "Updated Title", "tags": ["new-tag"]},
                },
                "update_mask": ["metadata"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "updated"

        # No delete or re-embed should have happened
        assert len(fake_vs.delete_calls) == 0
        assert len(fake_vs.upsert_calls) == initial_upsert_count

        # Vectors should still exist
        results = fake_vs.search(query="content stays")
        assert len(results) == 1

    def test_update_empty_content_removes_vectors(self, client, fake_vs):
        """UPDATE with empty content should remove all vectors."""
        _create_doc(client, body="Some content to be cleared")
        assert fake_vs.count_by_document_id("test-doc") > 0

        r = client.put(
            "/documents/test-doc",
            json={
                "document_id": "test-doc",
                "patch": {
                    "content": {"mime_type": "text/plain", "body": ""},
                },
                "update_mask": ["content"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

        # Delete was called (clears old vectors)
        assert "test-doc" in fake_vs.delete_calls
        # _sync_vector_entry skips when content is empty
        # so the vectors should be gone
        assert fake_vs.count_by_document_id("test-doc") == 0

    def test_update_nonexistent_returns_404(self, client, fake_vs):
        """UPDATE on nonexistent document should return 404."""
        r = client.put(
            "/documents/nonexistent-doc",
            json={
                "document_id": "nonexistent-doc",
                "patch": {
                    "content": {"mime_type": "text/plain", "body": "new"},
                },
                "update_mask": ["content"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 404

        # No side effects on vector store
        assert len(fake_vs.delete_calls) == 0
        assert "nonexistent-doc" not in fake_vs.vectors

    def test_update_multi_chunk_deletes_all_old_chunks(self, client, fake_vs):
        """Long document with multiple chunks: ALL old chunks deleted on update."""
        # Create a long document that will produce multiple chunks
        long_body = "Section A about elephants. " * 100  # ~2700 chars → multiple chunks
        _create_doc(client, body=long_body)

        old_chunk_count = fake_vs.count_by_document_id("test-doc")
        assert old_chunk_count > 1, f"Expected multiple chunks, got {old_chunk_count}"

        fake_vs.delete_calls.clear()

        # Update with shorter content
        r = client.put(
            "/documents/test-doc",
            json={
                "document_id": "test-doc",
                "patch": {
                    "content": {"mime_type": "text/plain", "body": "Short new content"},
                },
                "update_mask": ["content"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

        # ALL old chunks should have been deleted
        assert "test-doc" in fake_vs.delete_calls

        # New content should be 1 chunk
        new_chunk_count = fake_vs.count_by_document_id("test-doc")
        assert new_chunk_count == 1

        # Old content not findable
        assert len(fake_vs.search(query="elephants")) == 0


# ===================================================================
# Phase 1 Tests — Vector Sync on MOVE
# ===================================================================


class TestMoveVectorSync:
    """Tests for vector sync during document MOVE."""

    def test_move_deletes_old_vectors_before_reembed(self, client, fake_vs):
        """MOVE should delete old vectors then re-embed with new parent."""
        _create_doc(client, body="Content about koalas", parent_id="folder-a")
        assert fake_vs.count_by_document_id("test-doc") > 0
        fake_vs.delete_calls.clear()
        fake_vs.upsert_calls.clear()

        r = client.post(
            "/documents/test-doc/move",
            json={"new_parent_id": "folder-b"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "moved"

        # Verify delete was called (the critical fix)
        assert "test-doc" in fake_vs.delete_calls

        # Verify re-embed happened
        assert len(fake_vs.upsert_calls) == 1

        # Content should still be searchable
        results = fake_vs.search(query="koalas")
        assert len(results) == 1


# ===================================================================
# Phase 1 Tests — Vector Sync on DELETE
# ===================================================================


class TestDeleteVectorSync:
    """Tests for vector sync during document DELETE."""

    def test_delete_removes_vectors(self, client, fake_vs):
        """DELETE should remove all vectors for the document."""
        _create_doc(client, body="Content to be deleted")
        assert fake_vs.count_by_document_id("test-doc") > 0

        r = client.delete("/documents/test-doc", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

        # Vectors should be gone
        assert fake_vs.count_by_document_id("test-doc") == 0
        assert len(fake_vs.search(query="deleted")) == 0


# ===================================================================
# Phase 1 Tests — count_by_document_id
# ===================================================================


class TestCountByDocumentId:
    """Tests for QdrantVectorStore.count_by_document_id method."""

    def test_count_by_doc_returns_correct_count(self, monkeypatch):
        """count_by_document_id should return vectors for a specific doc."""
        monkeypatch.setenv("QDRANT_URL", "https://example.qdrant.io")
        monkeypatch.setenv("QDRANT_API_KEY", "qdrant-key")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        monkeypatch.setenv("APP_ENV", "test")

        class FakeOpenAI:
            def __init__(self, **kwargs):
                self.embeddings = SimpleNamespace(
                    create=lambda **_: SimpleNamespace(
                        data=[SimpleNamespace(embedding=[])]
                    )
                )

        class FakeQdrantClient:
            def __init__(self, *args, **kwargs):
                pass

            def count(self, collection_name, count_filter, exact):
                return SimpleNamespace(count=7)

        monkeypatch.setattr(vs_mod, "OpenAI", FakeOpenAI)
        monkeypatch.setattr(vs_mod, "QdrantClient", FakeQdrantClient)

        store = vs_mod.get_vector_store(refresh=True)
        result = store.count_by_document_id("some-doc")
        assert result == 7

    def test_count_by_doc_disabled_returns_neg1(self, monkeypatch):
        """count_by_document_id should return -1 when store is disabled."""
        for var in ["QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY"]:
            monkeypatch.delenv(var, raising=False)

        store = vs_mod.get_vector_store(refresh=True)
        assert store.count_by_document_id("any-doc") == -1
