# WEB-50B: Slash Fix + V3 Directory Structure

## Status: COMPLETED
**Date**: 2026-02-06
**Branch**: main

---

## Summary

Three-part mission: (A) fix the slash limitation in core API so document IDs with slashes work for all CRUD operations, (B) verify local development setup, (C) create v3 directory structure with 19 folder READMEs and 3 templates.

## Part A: Slash Fix

### Problem
FastAPI routes using `{doc_id}` only match single path segments. Document IDs with slashes (e.g. `docs/test/file.md`) caused 404 errors on UPDATE, DELETE, and MOVE operations.

### Solution: Catch-all route + Firestore key encoding

1. Changed 3 route definitions from `{doc_id}` to `{doc_id:path}`:
   - `PUT /documents/{doc_id:path}`
   - `POST /documents/{doc_id:path}/move`
   - `DELETE /documents/{doc_id:path}`

2. Added `_fs_key()` helper to encode slashes for Firestore:
   ```python
   def _fs_key(doc_id: str) -> str:
       return doc_id.replace("/", "__")
   ```
   Applied to all 8 `.document(doc_id)` calls in server.py.

### Files Changed

| File | Changes |
|------|---------|
| `agent_data/server.py` | Added `_fs_key()`, changed 3 routes to `{doc_id:path}`, updated 8 Firestore calls |
| `mcp_server/stdio_server.py` | Removed "flat ID only" restrictions from tool descriptions |
| `mcp_server/server.py` | Same tool description updates |

### Test Results
```
CREATE  docs/verify/slash-fix.md  → 200 ✅ (revision 1)
UPDATE  docs/verify/slash-fix.md  → 200 ✅ (revision 2)
MOVE    docs/verify/slash-fix.md  → 200 ✅ (revision 3)
DELETE  docs/verify/slash-fix.md  → 200 ✅ (revision 4)
Flat ID backward compat           → 200 ✅
```

## Part B: Local Setup Verification

| Component | Status |
|-----------|--------|
| Agent Data (localhost:8000) | RUNNING |
| MCP Server (stdio via Claude Desktop) | RUNNING |
| Claude Desktop config | Local-first (localhost:8000) |
| API Key | `test-key-local` |

## Part C: V3 Directory Structure

### Created 19 Folder READMEs

```
docs/
├── foundation/
│   ├── README.md
│   ├── constitution/README.md
│   ├── laws/README.md
│   └── architecture/README.md
├── plans/
│   ├── README.md
│   ├── blueprints/README.md
│   ├── sprints/README.md
│   ├── processes/README.md
│   └── specs/README.md
├── operations/
│   ├── README.md
│   ├── sessions/README.md
│   ├── research/README.md
│   ├── decisions/README.md
│   └── lessons/README.md
├── context-packs/README.md
├── playbooks/README.md
├── status/README.md
├── discussions/README.md
└── templates/README.md
```

All 19: HTTP 200, revision 1 ✅

### Created 3 Templates

| Template | Path | Status |
|----------|------|--------|
| Session Report | `docs/templates/session-report.md` | ✅ rev 1 |
| Decision Record (ADR) | `docs/templates/decision-record.md` | ✅ rev 1 |
| Context Pack | `docs/templates/context-pack.md` | ✅ rev 1 |

### Existing Documents (Migration Reference)

Existing git-based docs available via `/api/docs/tree`:

| Old Path | Suggested V3 Location |
|----------|----------------------|
| `docs/ssot/constitution.md` | `docs/foundation/constitution/` |
| `docs/ssot/Law_of_data_and_connection.md` | `docs/foundation/laws/` |
| `docs/dev/blueprints/*` (12 files) | `docs/plans/blueprints/` |
| `docs/dev/investigations/*` (6 files) | `docs/operations/research/` |
| `docs/dev/reports/*` (1 file) | `docs/operations/sessions/` |
| `docs/dev/ssot/*` (7 files) | `docs/foundation/` (various) |
| `docs/ops/*` (5 files) | `docs/playbooks/` |

Migration is a reference mapping — git-based docs and Firestore KB docs coexist. Actual migration can be done incrementally.

## Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/create_v3_structure.py` | Creates 19 folder README documents |
| `scripts/create_v3_templates.py` | Creates 3 template documents |

## No New Service Accounts Created
Confirmed: no new GCP service accounts were created.
