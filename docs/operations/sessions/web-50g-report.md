# WEB-50G Session Report: MCP Internal Dispatch + RAG Search Fix

**Date:** 2026-02-07
**Status:** Completed
**Branch:** main
**Revision:** agent-data-test-00054-pbs (100% traffic)

---

## Summary

Fixed two critical issues preventing Claude.ai MCP connector from working with Cloud Run:
1. Missing POST `/mcp` endpoint for MCP JSON-RPC protocol
2. RAG search using naive substring matching instead of vector/keyword search

## Changes Made

### Part A: MCP Internal Dispatch Fix

**Problem:** Claude.ai MCP connector sends POST to `/mcp` with JSON-RPC protocol (`{"method":"tools/call","params":{...}}`), but the server only had GET `/mcp` (server info) and POST `/mcp/tools/{tool_name}` (individual tool calls). Result: 405 Method Not Allowed.

**Fix in `agent_data/server.py`:**
1. Added `POST /mcp` handler (`mcp_jsonrpc`) that handles full MCP JSON-RPC protocol:
   - `initialize` — returns server capabilities and protocol version
   - `notifications/initialized` — acknowledgment
   - `tools/list` — returns all 8 tool definitions
   - `tools/call` — dispatches to internal Python functions
2. Refactored tool dispatch into shared `_dispatch_mcp_tool()` function used by both POST `/mcp` and POST `/mcp/tools/{tool_name}`
3. All tool calls use **direct internal function calls** — NO HTTP self-requests
4. Added API key validation to POST `/mcp` endpoint

### Part B: RAG Search Fix

**Problem:** `_retrieve_query_context` only checked if the full query string appeared in the first 200 chars of each document body (naive substring match). Queries like "web-frontend Agency OS DocsTreeView" never matched.

**Fix in `agent_data/server.py`:**
1. Updated `_retrieve_query_context` to use **Qdrant vector search** first (semantic similarity)
2. Falls back to **keyword overlap scoring** when Qdrant is unavailable:
   - Splits query into words, checks each word against full document body + title
   - Scores by keyword hit ratio (matched_words / total_words)
   - Sorts by score descending, returns top_k
3. Removed the `vecdb is None → noop_qdrant` shortcut so Firestore fallback always works

**Fix in `agent_data/vector_store.py`:**
1. Added `search()` method to `QdrantVectorStore`:
   - Embeds query via OpenAI
   - Searches Qdrant with optional tag filtering
   - Deduplicates results by document_id (multiple chunks may match)
2. Added `count()` method for diagnostics

### Part C: Additional Fixes

1. **Async thread fix:** `query_knowledge` (sync, uses langroid's `asyncio.run()`) was failing when called from async MCP dispatch. Fixed with `asyncio.to_thread()`.
2. **Reindex endpoint:** Added `POST /kb/reindex` (API key protected) to re-index all Firestore KB documents into Qdrant. Result: 100 docs indexed, 356 vectors created.
3. **Soft-delete re-creation:** Fixed `create_document` to allow re-creating soft-deleted documents (was returning 409 CONFLICT)
4. **E2E test script:** Created `scripts/test_mcp_e2e.sh` for reusable MCP testing

## Files Changed

| File | Changes |
|------|---------|
| `agent_data/server.py` | POST /mcp handler, _dispatch_mcp_tool, improved _retrieve_query_context, /kb/reindex, create_document soft-delete fix |
| `agent_data/vector_store.py` | Added search() and count() methods |
| `scripts/test_mcp_e2e.sh` | New E2E test script (9 tests) |
| `docs/operations/sessions/web-50g-report.md` | This report |

## Test Results

### Local E2E (9/9 PASS)
- initialize: PASS
- tools/list: PASS
- search_knowledge: PASS
- list_documents: PASS
- get_document: PASS
- upload_document: PASS
- update_document: PASS
- delete_document: PASS
- auth rejection: PASS

### Unit Tests (37/37 PASS)
All existing unit tests pass without modification.

### Cloud Run Search Verification (3/3 PASS, Qdrant vector search)
| Query | Expected | Found | Score |
|-------|----------|-------|-------|
| "governance hybrid Agents First" | governance.md | governance.md | 0.433 |
| "web frontend Nuxt DocsTreeView" | web-frontend.md | web-frontend.md | 0.574 |
| "playbook assembly task two-hat" | assembly-task.md | assembly-task.md | 0.400 |

### Reindex Results
- Firestore total: 113 documents
- Indexed to Qdrant: 100
- Skipped (deleted/empty): 13
- Errors: 0
- Qdrant vectors: 356

## Success Criteria Checklist

| # | Criteria | Status |
|---|----------|--------|
| 1 | MCP dispatch uses internal functions (NO HTTP) | Done |
| 2 | list_documents via MCP Cloud -> V3 structure | Done (8 context-packs) |
| 3 | get_document via MCP Cloud -> real content | Done (Agents First) |
| 4 | All 8 MCP tools via Cloud -> no 403 | Done |
| 5 | RAG search finds web-frontend pack | Done (score 0.574) |
| 6 | RAG search finds session report | Done (local verified) |
| 7 | RAG search finds playbook | Done (score 0.400) |
| 8 | E2E test script saved | Done (scripts/test_mcp_e2e.sh) |
| 9 | Deploy successful | Done (revision 00054-pbs, 100% traffic) |
| 10 | No new SA created | Confirmed |

## Stop Rules Compliance
- No new Service Account created
- No Qdrant config/schema changes (only added search/count methods)
- No auth mechanism changes (existing API key auth preserved)
- Reindex is additive only (no data deletion)
