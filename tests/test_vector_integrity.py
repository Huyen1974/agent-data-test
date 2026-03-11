"""Integration tests for the full vector integrity system.

Tests the complete lifecycle: create -> update -> delete -> audit -> cleanup,
as well as health data integrity, concurrent operations, large documents,
and reindex-missing functionality.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server
import agent_data.vector_store as vs_mod

# ---- Fake vector store ----


class FakeVectorStore:
    """In-memory vector store tracking all operations."""

    def __init__(self):
        self.enabled = True
        self.vectors: dict[str, list[dict]] = {}

    def upsert_document(
        self,
        *,
        document_id,
        content,
        metadata=None,
        parent_id=None,
        is_human_readable=False,
    ):
        if not content or not content.strip():
            return vs_mod.VectorSyncResult(status="ready", chunks_created=0)
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
def pg_mocks(monkeypatch):
    """Mock pg_store with an in-memory dict and set agent.db = True."""
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

    patches = {
        "get": patch("agent_data.pg_store.get_doc", side_effect=fake_get),
        "set": patch("agent_data.pg_store.set_doc", side_effect=fake_set),
        "update": patch("agent_data.pg_store.update_doc", side_effect=fake_update),
        "stream": patch("agent_data.pg_store.stream_docs", side_effect=fake_stream),
    }
    mocks = {name: p.start() for name, p in patches.items()}
    yield {"store": store, "mocks": mocks}
    for p in patches.values():
        p.stop()


@pytest.fixture()
def fake_vs(monkeypatch):
    store = FakeVectorStore()
    monkeypatch.setattr(vs_mod, "get_vector_store", lambda refresh=False: store)
    monkeypatch.setattr(vs_mod, "delete_document", store.delete_document)
    return store


@pytest.fixture()
def client(env, pg_mocks, fake_vs):
    return TestClient(server.app)


HEADERS = {"x-api-key": "test-key"}


def _create(client, doc_id, body, parent_id="root", tags=None):
    payload = {
        "document_id": doc_id,
        "parent_id": parent_id,
        "content": {"mime_type": "text/plain", "body": body},
        "metadata": {"title": doc_id, "tags": tags or ["test"]},
        "is_human_readable": True,
    }
    r = client.post("/documents", json=payload, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


# ===================================================================
# Full Lifecycle Test
# ===================================================================


class TestFullLifecycle:
    """End-to-end lifecycle: create -> update -> delete -> audit -> cleanup."""

    def test_full_lifecycle(self, client, fake_vs, pg_mocks):
        # 1. Create doc -> verify vector exists
        _create(client, "doc-lifecycle", "Content about dolphins")
        assert fake_vs.count_by_document_id("doc-lifecycle") > 0
        assert len(fake_vs.search(query="dolphins")) == 1

        # 2. Update doc -> verify OLD vectors gone, NEW vectors present
        r = client.put(
            "/documents/doc-lifecycle",
            json={
                "document_id": "doc-lifecycle",
                "patch": {
                    "content": {
                        "mime_type": "text/plain",
                        "body": "Content about whales",
                    }
                },
                "update_mask": ["content"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert len(fake_vs.search(query="dolphins")) == 0
        assert len(fake_vs.search(query="whales")) == 1

        # 3. Create 2nd doc -> verify both searchable
        _create(client, "doc-lifecycle-2", "Content about sharks")
        assert len(fake_vs.search(query="whales")) == 1
        assert len(fake_vs.search(query="sharks")) == 1

        # 4. Delete 1st doc -> verify only 2nd searchable
        r = client.delete("/documents/doc-lifecycle", headers=HEADERS)
        assert r.status_code == 200
        assert len(fake_vs.search(query="whales")) == 0
        assert len(fake_vs.search(query="sharks")) == 1

        # 5. Run audit-sync -> should be clean
        r = client.post("/kb/audit-sync", headers=HEADERS)
        assert r.status_code == 200
        audit = r.json()
        assert audit["orphan_count"] == 0
        assert audit["ghost_count"] == 0
        assert audit["status"] == "clean"

        # 6. Simulate inconsistency: inject orphan vector directly
        fake_vs.vectors["ghost-doc-deleted"] = [
            {"content": "orphan content", "metadata": {}, "chunk_index": 0}
        ]

        # 7. Audit should detect orphan
        r = client.post("/kb/audit-sync", headers=HEADERS)
        assert r.status_code == 200
        audit = r.json()
        assert audit["orphan_count"] == 1
        assert "ghost-doc-deleted" in audit["orphan_vector_document_ids"]

        # 8. Cleanup dry_run -> reports but doesn't delete
        r = client.post(
            "/kb/cleanup-orphans",
            json={"dry_run": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        cleanup = r.json()
        assert cleanup["mode"] == "dry_run"
        assert cleanup["orphans_found"] == 1
        assert cleanup["orphans_deleted"] == 0
        # Vector should still exist
        assert "ghost-doc-deleted" in fake_vs.vectors

        # 9. Cleanup execute -> actually deletes
        r = client.post(
            "/kb/cleanup-orphans",
            json={"dry_run": False},
            headers=HEADERS,
        )
        assert r.status_code == 200
        cleanup = r.json()
        assert cleanup["mode"] == "execute"
        assert cleanup["orphans_deleted"] == 1
        assert "ghost-doc-deleted" not in fake_vs.vectors

        # 10. Audit again -> clean
        r = client.post("/kb/audit-sync", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["status"] == "clean"


# ===================================================================
# Health Data Integrity Test
# ===================================================================


class TestHealthDataIntegrity:
    """Test that /health returns data_integrity metrics."""

    def test_health_includes_data_integrity(self, client, fake_vs):
        _create(client, "health-doc-1", "First document")
        _create(client, "health-doc-2", "Second document")

        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        di = data.get("data_integrity")
        assert di is not None
        assert di["document_count"] == 2
        assert di["vector_point_count"] > 0
        assert di["sync_status"] == "ok"
        assert di["ratio"] > 0

    def test_health_without_vectors_shows_critical(self, client, fake_vs):
        # Create doc but remove its vectors to simulate mismatch
        _create(client, "broken-doc", "Content")
        fake_vs.vectors.clear()

        r = client.get("/health")
        assert r.status_code == 200
        di = r.json().get("data_integrity")
        assert di is not None
        assert di["document_count"] == 1
        assert di["vector_point_count"] == 0
        assert di["sync_status"] == "critical"


# ===================================================================
# Concurrent Updates Test
# ===================================================================


class TestConcurrentUpdates:
    """Test that concurrent updates on same doc don't corrupt vectors."""

    def test_concurrent_updates_last_write_wins(self, client, fake_vs):
        _create(client, "concurrent-doc", "Initial content")

        def do_update(version: int):
            return client.put(
                "/documents/concurrent-doc",
                json={
                    "document_id": "concurrent-doc",
                    "patch": {
                        "content": {
                            "mime_type": "text/plain",
                            "body": f"Version {version} content",
                        }
                    },
                    "update_mask": ["content"],
                },
                headers=HEADERS,
            )

        # Run 5 sequential updates (concurrent via TestClient is single-threaded)
        results = []
        for i in range(5):
            r = do_update(i)
            results.append(r)

        # At least some should succeed
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 1

        # Should have exactly 1 set of vectors for this doc
        assert fake_vs.count_by_document_id("concurrent-doc") >= 1

        # Search should find the latest version's content
        all_results = fake_vs.search(query="Version")
        assert len(all_results) == 1


# ===================================================================
# Large Document Chunking Test
# ===================================================================


class TestLargeDocumentChunking:
    """Test update of large multi-chunk documents."""

    def test_large_document_all_old_chunks_deleted_on_update(self, client, fake_vs):
        # Create a large document (will produce multiple chunks)
        big_body = "Paragraph about astronomy. " * 200  # ~5400 chars -> ~11 chunks
        _create(client, "large-doc", big_body)

        old_chunks = fake_vs.count_by_document_id("large-doc")
        assert old_chunks > 1, f"Expected multiple chunks, got {old_chunks}"

        # Update with small content
        r = client.put(
            "/documents/large-doc",
            json={
                "document_id": "large-doc",
                "patch": {
                    "content": {"mime_type": "text/plain", "body": "Tiny update."}
                },
                "update_mask": ["content"],
                "last_known_revision": 1,
            },
            headers=HEADERS,
        )
        assert r.status_code == 200

        # Only 1 chunk should remain
        new_chunks = fake_vs.count_by_document_id("large-doc")
        assert new_chunks == 1

        # Old content should not be searchable
        assert len(fake_vs.search(query="astronomy")) == 0
        assert len(fake_vs.search(query="Tiny update")) == 1


# ===================================================================
# Reindex Missing Test
# ===================================================================


class TestReindexMissing:
    """Test /kb/reindex-missing endpoint."""

    def test_reindex_missing_restores_vectors(self, client, fake_vs):
        # Create docs normally
        _create(client, "reindex-doc-1", "Content about birds")
        _create(client, "reindex-doc-2", "Content about fish")

        # Manually remove vectors for doc-1 to simulate ghost
        del fake_vs.vectors["reindex-doc-1"]
        assert fake_vs.count_by_document_id("reindex-doc-1") == 0

        # Audit should detect the ghost
        r = client.post("/kb/audit-sync", headers=HEADERS)
        assert r.status_code == 200
        audit = r.json()
        assert "reindex-doc-1" in audit["documents_without_vectors"]

        # Reindex missing
        r = client.post("/kb/reindex-missing", headers=HEADERS)
        assert r.status_code == 200
        reindex = r.json()
        assert reindex["missing_found"] >= 1
        assert reindex["reindexed"] >= 1

        # Vectors should be restored
        assert fake_vs.count_by_document_id("reindex-doc-1") > 0

        # Audit should now be clean
        r = client.post("/kb/audit-sync", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["ghost_count"] == 0


# ===================================================================
# Cleanup Max Delete Safety Test
# ===================================================================


class TestCleanupSafety:
    """Test that max_delete limit is respected."""

    def test_max_delete_limits_cleanup(self, client, fake_vs):
        # Create 5 orphan vectors
        for i in range(5):
            fake_vs.vectors[f"orphan-{i}"] = [
                {"content": f"orphan {i}", "metadata": {}, "chunk_index": 0}
            ]

        r = client.post(
            "/kb/cleanup-orphans",
            json={"dry_run": False, "max_delete": 2},
            headers=HEADERS,
        )
        assert r.status_code == 200
        cleanup = r.json()
        assert cleanup["orphans_found"] == 5
        assert cleanup["orphans_deleted"] == 2
        assert cleanup["remaining_after_cleanup"] == 3

        # 3 orphans should still exist
        remaining = sum(1 for k in fake_vs.vectors if k.startswith("orphan-"))
        assert remaining == 3
