# Vector Integrity Audit — Pre-Implementation Report

**Date:** 2026-02-08
**Auditor:** Claude Code CLI
**Branch:** main (pre feat/vector-integrity)

---

## 1. Library Versions

| Package | Version |
|---------|---------|
| langroid | 0.58.0 |
| qdrant-client | 1.15.0 |
| openai | 1.97.0 |
| tenacity | 8.5.0 |
| fastapi | 0.116.1 |

## 2. Available Methods for Vector Management

### Langroid DocChatAgent (relevant methods)
- `ingest`, `ingest_docs`, `ingest_doc_paths`, `ingest_dataframe` — ingestion entry points
- `delete_id` — delete a specific item by ID
- `clear` — clears vector store
- **No** `replace_document` or `update_document` method exists

### Langroid QdrantDB VectorStore (all methods)
- `add_documents` — primary way to add vectors
- `delete_collection` — drops entire collection
- `clear_all_collections`, `clear_empty_collections` — bulk cleanup
- `get_all_documents`, `get_documents_by_ids` — retrieval
- **NOTABLE GAP**: No `delete_documents`, `delete_by_id`, or `delete_by_filter`

### Qdrant Client (relevant methods)
- `delete` — delete points by filter or IDs (**primary tool for cleanup**)
- `scroll` — iterate through all points (essential for auditing)
- `count` — get point count in collection
- `search`, `search_batch`, `search_groups` — search modes
- `upsert` — insert or update points
- `batch_update_points` — batch operations

### Conclusion on Method Selection
- **Langroid has NO per-document delete** at the VectorStore level
- **Solution: Qdrant `client.delete()` with filter** (Option B/C from mission spec)
- This is already implemented in `vector_store.py:_qdrant_delete()` using `FilterSelector`

## 3. Current CRUD + Vector Sync Flow

### CREATE (`POST /documents` — server.py:951-1010)
1. Validate document doesn't exist (or is soft-deleted)
2. Write to Firestore with `vector_status: "pending"`
3. Best-effort `_sync_vector_entry()` → upserts vectors
4. Update `vector_status` to "ready" or "error"

### UPDATE (`PUT /documents/{doc_id}` — server.py:1012-1125)
1. Fetch from Firestore, validate revision
2. Apply patch (content, metadata, is_human_readable) per `update_mask`
3. Write updates to Firestore (increments revision)
4. `_delete_vector_entry(doc_id)` — delete ALL old vectors
5. `_sync_vector_entry(...)` — upsert new vectors
6. **Issue**: Steps 4-5 are not atomic; if 5 fails after 4 succeeds, vectors are lost

### DELETE (`DELETE /documents/{doc_id}` — server.py:1216-1255)
1. Soft-delete: set `deleted_at`, `vector_status: "deleted"`
2. Best-effort `_delete_vector_entry(doc_id)`
3. If vector delete fails, orphan vectors remain

### MOVE (`POST /documents/{doc_id}/move` — server.py:1127-1214)
1. Validate move target (no cycles)
2. Update `parent_id` in Firestore
3. Re-sync vectors with `_sync_vector_entry()` (full re-embed)
4. **Issue**: Does NOT call `_delete_vector_entry()` first — accumulates stale vectors

## 4. Vector Store Implementation (`vector_store.py`)

### Key Class: `QdrantVectorStore`
- **Chunking**: `_split_text()` — character-based, 4000 char chunks, 400 overlap
- **Point IDs**: Deterministic via `uuid5(NAMESPACE_DNS, f"{doc_id}:chunk:{idx}")`
- **Payload schema**: `{content, document_id, metadata, parent_id, is_human_readable}`
- **Retry**: All Qdrant operations use `@sync_retry()` decorator (tenacity, 3 attempts, exponential backoff)

### Methods
| Method | Purpose |
|--------|---------|
| `upsert_document()` | Chunk + embed + upsert to Qdrant |
| `delete_document()` | Filter-based delete all chunks by document_id |
| `search()` | Vector similarity search with dedup |
| `count()` | Total vector count in collection |
| `list_document_ids()` | Scroll all points, return unique document_ids |

## 5. Issues Identified

### CRITICAL
1. **MOVE does not delete old vectors** — `move_document()` calls `_sync_vector_entry()` but NOT `_delete_vector_entry()` first. Since point IDs are deterministic based on `doc_id:chunk:idx`, if chunk count stays the same, upsert overwrites. But if chunk count changes, stale chunks accumulate.

### HIGH
2. **No atomicity between Firestore write and vector sync** — If vector upsert fails after Firestore update, document shows updated content but vectors are stale or missing.
3. **UPDATE metadata-only still deletes+re-creates all vectors** — Unnecessary when content hasn't changed; wastes embedding API calls.

### MEDIUM
4. **No `vector_pending` flag** — When vector sync fails, `vector_status: "error"` is set but there's no mechanism to retry automatically.
5. **`/kb/cleanup-orphans` doesn't have dry_run** — Deletes immediately with no preview.
6. **`/kb/cleanup-orphans` doesn't have max_delete limit** — No safety cap.
7. **`/health` has no data integrity metrics** — Only shows service status, not doc/vector counts.

### LOW
8. **Structured logging incomplete** — Vector operations log info/error but without structured fields (action, old/new counts, duration).

## 6. Current Endpoint Summary

| Endpoint | Exists | Vector Maintenance |
|----------|--------|--------------------|
| `/health` | Yes | Service status only, no data integrity |
| `/kb/reindex` | Yes | Re-index all docs (no delete-first) |
| `/kb/cleanup-orphans` | Yes | Basic orphan cleanup (no dry_run, no limit) |
| `/admin/audit-sync` | **No** | Need: orphan/ghost detection |
| `/admin/orphan-cleanup` | **No** | Need: dry_run + max_delete + detailed report |
| `/admin/reindex-missing` | **No** | Need: re-index only ghost documents |

## 7. Existing Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/test_vector_store.py` | 6 tests | upsert, delete, chunking |
| `tests/unit/test_kb_crud_unit.py` | CRUD endpoints (unit) | Basic mocks |
| `tests/e2e/test_kb_crud.py` | CRUD endpoints (e2e) | With server mocks |

### Test Gaps
- No tests for vector sync during UPDATE (delete+re-create)
- No tests for MOVE vector sync
- No tests for metadata-only update optimization
- No tests for failed vector sync recovery
- No tests for audit/cleanup endpoints
- No integration tests for full lifecycle

## 8. Implementation Plan

**Chosen approach**: Option C (Hybrid) — already implemented in codebase.
- `_qdrant_delete()` uses Qdrant `client.delete()` with `FilterSelector` by `document_id`
- `upsert_document()` uses Qdrant `client.upsert()` via Langroid-style chunking
- Both wrapped with `@sync_retry()` for resilience

**Key fix needed**: The delete+upsert pattern exists but needs:
1. Fix MOVE to also delete old vectors first
2. Optimize metadata-only updates to skip re-embedding
3. Add structured logging around vector operations
4. Extend /health with data integrity metrics
5. Add admin endpoints for audit/cleanup with safety controls
