# [WEB-50D] Session Report: Fix MCP Data Visibility on Cloud

## Status: COMPLETED
## Date: 2026-02-06

## Objective
Documents created locally (13 context packs/playbooks/status + 19 V3 folders) were NOT visible via cloud MCP tools. Investigate root cause and fix.

## Root Cause Analysis

### Finding: Local and Cloud share SAME Firestore
- Both local (localhost:8000) and Cloud Run use `firestore.Client()` with default credentials
- Project: `github-chatgpt-ggcloud` (same for both)
- No Firestore emulator running (verified: emulator env vars not set)
- Data IS shared — 62 documents visible from both endpoints

### Root Cause: MCP Tools Used Wrong Endpoints
The MCP `list_documents` and `get_document` tools were calling GitHub API endpoints instead of Firestore KB endpoints:

| Tool | OLD Endpoint (wrong) | NEW Endpoint (fixed) |
|------|---------------------|---------------------|
| `list_documents` | `GET /api/docs/tree` (GitHub API) | `GET /kb/list` (Firestore KB) |
| `get_document` | `GET /api/docs/file` (GitHub API) | `GET /kb/get/{doc_id}` (Firestore KB) |

The `/api/docs/tree` endpoint (in `docs_api.py`) proxies the GitHub repo `Huyen1974/web-test`, which only contains repo files — NOT Firestore KB documents.

## Changes Made

### 1. New KB Read Endpoints (`agent_data/server.py`)
- `GET /kb/list` — Lists all KB documents from Firestore, with optional `prefix` filter
- `GET /kb/get/{doc_id:path}` — Gets full document content from Firestore by ID
- Both endpoints skip soft-deleted documents (`deleted_at is not None`)
- Uses existing `_fs_key()` for slash-path encoding

### 2. MCP STDIO Server (`mcp_server/stdio_server.py`)
- `list_documents` handler: `/api/docs/tree` → `/kb/list`
- `get_document` handler: `/api/docs/file` → `/kb/get/{doc_id}`
- GitHub docs fallback preserved for `get_document` if KB lookup fails

### 3. MCP HTTP Server (`mcp_server/server.py`)
- Same changes as STDIO server
- `list_documents()`: uses `/kb/list` with prefix param
- `get_document()`: uses `/kb/get/` with GitHub fallback

### 4. Cloud Run Deploy
- Deployed revision `00050-q86` (1Gi memory)
- Routed 100% traffic to new revision

## Verification Results

### Cloud `/kb/list` Endpoint
| Category | Count | Status |
|----------|-------|--------|
| Context Packs (docs/context-packs/*) | 6 + 2 folders | PASS |
| Playbooks (docs/playbooks/*) | 4 + 2 folders | PASS |
| Status (docs/status/*) | 3 + 2 folders | PASS |
| Total KB documents | 62 | PASS |

### Cloud Content Spot-Checks
| Document | Key Content Verified |
|----------|---------------------|
| governance.md | GC-LAW 1.3 (single SA), No-Code-New, Hybrid principle, Two-hat process |
| agent-data.md | 8 MCP tools listed, API endpoints, V3 structure, slash path docs |
| web-frontend.md | Agency OS components, DocsTreeView, Directus integration, Nuxt 3 stack |
| infrastructure.md | GCP project ID, Cloud Run details, Qdrant cluster, deploy commands |

### RAG Search Test
- Query: "governance context pack" → Returns governance constitution content
- `search_knowledge` works end-to-end on Cloud Run

## Issues Found
1. **Cloud Run revision caching**: Deploy created revision 00050-q86 but didn't auto-route traffic. Had to manually `update-traffic` to new revision.
2. **Agent Data context pack has stale endpoint refs**: The `agent-data.md` pack still lists old endpoints (`/api/docs/tree`, `/api/docs/file`) for MCP read tools. Should update to `/kb/list` and `/kb/get/` in a future session.

## Files Modified
- `agent_data/server.py` — Added `/kb/list` and `/kb/get/{doc_id:path}` endpoints
- `mcp_server/stdio_server.py` — Updated list_documents + get_document to use /kb/ endpoints
- `mcp_server/server.py` — Same updates for HTTP MCP server

## Next Steps
1. Update agent-data.md context pack to reference correct `/kb/` endpoints
2. Consider adding `/kb/search` endpoint as lightweight alternative to `/chat`
3. Proceed to WEB-50E or next mission

## Governance Compliance
- No new Service Accounts (GC-LAW 1.3)
- Hybrid config maintained (local + cloud)
- No new UI components
- GitHub docs fallback preserved (backward compatible)
