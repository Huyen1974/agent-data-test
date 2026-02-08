"""Tests for the auto-heal feature on /kb/audit-sync.

Verifies:
- Clean system: returns immediately, no reindex/cleanup called
- Ghosts detected: auto reindex + verification audit
- Orphans detected: auto cleanup + verification audit
- Mixed (ghosts + orphans): fix both + verification
- max_delete safety limit respected
- Partial failure: reports errors but does not crash
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import agent_data.server as server
import agent_data.vector_store as vs_mod

# ---- Fake Firestore ----


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


# ---- Fake vector store ----


class FakeVectorStore:
    def __init__(self):
        self.enabled = True
        self.vectors: dict[str, list[dict]] = {}
        self._fail_upsert_for: set[str] = set()

    def upsert_document(
        self,
        *,
        document_id,
        content,
        metadata=None,
        parent_id=None,
        is_human_readable=False,
    ):
        if document_id in self._fail_upsert_for:
            return vs_mod.VectorSyncResult(
                status="error", error="simulated upsert failure"
            )
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


def _create(client, doc_id, body, tags=None):
    payload = {
        "document_id": doc_id,
        "parent_id": "root",
        "content": {"mime_type": "text/plain", "body": body},
        "metadata": {"title": doc_id, "tags": tags or ["test"]},
        "is_human_readable": True,
    }
    r = client.post("/documents", json=payload, headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


# ===================================================================
# Test: clean system — returns immediately
# ===================================================================


class TestAutoHealCleanSystem:
    def test_auto_heal_clean_returns_immediately(self, client, fake_vs):
        """When system is clean, auto_heal returns audit result directly."""
        _create(client, "doc-1", "Content about cats")
        _create(client, "doc-2", "Content about dogs")

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()

        # Should return plain audit (no heal report)
        assert data["status"] == "clean"
        assert data["ghost_count"] == 0
        assert data["orphan_count"] == 0
        # No auto_heal key in response when clean
        assert "auto_heal" not in data

    def test_audit_without_auto_heal_unchanged(self, client, fake_vs):
        """Default call (no auto_heal) returns same as before."""
        _create(client, "doc-1", "Content")

        r = client.post("/kb/audit-sync", headers=HEADERS)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "clean"
        assert "auto_heal" not in data

    def test_audit_with_auto_heal_false_unchanged(self, client, fake_vs):
        """Explicit auto_heal=False returns plain audit even with issues."""
        _create(client, "doc-1", "Content")
        # Inject orphan
        fake_vs.vectors["orphan-doc"] = [
            {"content": "orphan", "metadata": {}, "chunk_index": 0}
        ]

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": False},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "needs_cleanup"
        assert data["orphan_count"] == 1
        # Orphan still exists (no healing)
        assert "orphan-doc" in fake_vs.vectors


# ===================================================================
# Test: ghosts detected — auto reindex
# ===================================================================


class TestAutoHealWithGhosts:
    def test_auto_heal_reindexes_ghosts(self, client, fake_vs):
        """Ghosts (docs without vectors) get re-indexed."""
        _create(client, "doc-1", "Content about birds")
        _create(client, "doc-2", "Content about fish")

        # Remove vectors for doc-1 to simulate ghost
        del fake_vs.vectors["doc-1"]
        assert fake_vs.count_by_document_id("doc-1") == 0

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["auto_heal"] is True
        assert data["final_status"] == "clean"

        # Before: had ghosts
        assert data["audit_before"]["ghost_count"] == 1
        assert "doc-1" in data["audit_before"]["documents_without_vectors"]

        # After: clean
        assert data["audit_after"]["ghost_count"] == 0

        # Reindex details
        assert data["reindex"]["reindexed"] == 1

        # Vectors restored
        assert fake_vs.count_by_document_id("doc-1") > 0


# ===================================================================
# Test: orphans detected — auto cleanup
# ===================================================================


class TestAutoHealWithOrphans:
    def test_auto_heal_cleans_orphans(self, client, fake_vs):
        """Orphans (vectors without docs) get cleaned up."""
        _create(client, "doc-1", "Content about trees")

        # Inject orphan vectors
        fake_vs.vectors["deleted-doc"] = [
            {"content": "stale data", "metadata": {}, "chunk_index": 0}
        ]

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["auto_heal"] is True
        assert data["final_status"] == "clean"

        # Before: had orphans
        assert data["audit_before"]["orphan_count"] == 1

        # After: clean
        assert data["audit_after"]["orphan_count"] == 0

        # Cleanup details
        assert data["cleanup"]["orphans_deleted"] == 1

        # Orphan gone
        assert "deleted-doc" not in fake_vs.vectors


# ===================================================================
# Test: mixed — ghosts + orphans
# ===================================================================


class TestAutoHealMixed:
    def test_auto_heal_fixes_both_ghosts_and_orphans(self, client, fake_vs):
        """Both ghosts and orphans fixed in single auto-heal run."""
        _create(client, "doc-1", "Content about mountains")
        _create(client, "doc-2", "Content about rivers")

        # Create ghost: remove vectors for doc-1
        del fake_vs.vectors["doc-1"]

        # Create orphan: inject vectors for non-existent doc
        fake_vs.vectors["ghost-doc"] = [
            {"content": "orphan data", "metadata": {}, "chunk_index": 0}
        ]

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["auto_heal"] is True
        assert data["final_status"] == "clean"

        # Both fixed
        assert data["audit_before"]["ghost_count"] == 1
        assert data["audit_before"]["orphan_count"] == 1
        assert data["audit_after"]["ghost_count"] == 0
        assert data["audit_after"]["orphan_count"] == 0

        # Reindex + cleanup both ran
        assert data["reindex"]["reindexed"] == 1
        assert data["cleanup"]["orphans_deleted"] == 1


# ===================================================================
# Test: max_delete safety limit
# ===================================================================


class TestAutoHealMaxDeleteLimit:
    def test_auto_heal_respects_max_delete_100(self, client, fake_vs):
        """Auto-heal cleanup caps at 100 orphans even if more exist."""
        _create(client, "doc-1", "Content")

        # Create 150 orphan vectors
        for i in range(150):
            fake_vs.vectors[f"orphan-{i:03d}"] = [
                {"content": f"orphan {i}", "metadata": {}, "chunk_index": 0}
            ]

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["auto_heal"] is True
        assert data["cleanup"]["orphans_found"] == 150
        assert data["cleanup"]["orphans_deleted"] == 100
        assert data["cleanup"]["remaining_after_cleanup"] == 50

        # Final audit should still show remaining orphans
        assert data["final_status"] == "needs_cleanup"
        assert data["audit_after"]["orphan_count"] == 50


# ===================================================================
# Test: partial failure — reindex fails for some docs
# ===================================================================


class TestAutoHealPartialFailure:
    def test_auto_heal_partial_reindex_failure(self, client, fake_vs):
        """If reindex fails for one doc, others still succeed and no crash."""
        _create(client, "doc-ok", "Content about success")
        _create(client, "doc-fail", "Content about failure")

        # Remove vectors for both to create ghosts
        del fake_vs.vectors["doc-ok"]
        del fake_vs.vectors["doc-fail"]

        # Make doc-fail always fail on upsert
        fake_vs._fail_upsert_for.add("doc-fail")

        r = client.post(
            "/kb/audit-sync",
            json={"auto_heal": True},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()

        assert data["auto_heal"] is True

        # Reindex: 1 success, 1 failure
        assert data["reindex"]["reindexed"] == 1
        assert len(data["reindex"]["failed"]) == 1
        assert data["reindex"]["failed"][0]["document_id"] == "doc-fail"

        # doc-ok should have vectors restored
        assert fake_vs.count_by_document_id("doc-ok") > 0
        # doc-fail still missing
        assert fake_vs.count_by_document_id("doc-fail") == 0

        # Final status reflects remaining issue
        assert data["audit_after"]["ghost_count"] == 1
