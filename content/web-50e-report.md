# [WEB-50E] Session Report: Fix MCP Cloud Connector + Content Update + Migration

## Status: COMPLETED
## Date: 2026-02-06

## Objective
1. Fix Claude.ai MCP connector (can't see data on cloud)
2. Update 3 context packs with corrected content
3. Migrate 33 old GitHub docs into V3 Firestore KB structure

---

## Part A: MCP Cloud Connector Fix

### Root Cause Analysis

**Architecture Discovery:**
- Only ONE Cloud Run service: `agent-data-test` (no `agent-data-mcp` service)
- The MCP HTTP server (`mcp_server/server.py`) runs ONLY locally on port 8001
- Dockerfile copies only `agent_data/` — MCP server code is NOT in the container
- Claude.ai connector had NO MCP endpoints to connect to on Cloud Run

**Connector URLs documented in `docs/MCP_CONNECTOR_GUIDE.md`:**
| Client | URL | Issue |
|--------|-----|-------|
| Claude Desktop | stdio via stdio_server.py | Works (local) |
| Claude.ai | http://localhost:8001/mcp | Can't reach localhost from cloud |
| ChatGPT | OpenAPI spec → Cloud Run | Missing /kb/ endpoints in spec |
| Gemini | OpenAPI spec → Cloud Run | Same as ChatGPT |

### Fix: Added MCP Protocol Endpoints to agent_data/server.py

Instead of deploying a separate MCP service, added MCP endpoints directly to the main server:

- `GET /mcp` — Returns server info + 8 tool definitions
- `POST /mcp/tools/{tool_name}` — Dispatches to internal functions (no HTTP proxy)

Tool dispatch calls existing functions directly:
| MCP Tool | Internal Function |
|----------|------------------|
| search_knowledge | `query_knowledge()` (POST /chat handler) |
| list_documents | `list_kb_documents()` (GET /kb/list handler) |
| get_document | `get_kb_document()` (GET /kb/get handler) |
| upload_document | `create_document()` (POST /documents handler) |
| update_document | `update_document()` (PUT /documents handler) |
| delete_document | `delete_document()` (DELETE /documents handler) |
| move_document | `move_document()` (POST /documents/move handler) |
| ingest_document | `ingest()` (POST /ingest handler) |

### Deployment
- Deployed revision `00051-twq` (1Gi memory)
- Routed 100% traffic to new revision
- Note: `gcloud run deploy` created new revision but didn't auto-route traffic — had to manually `update-traffic`

### Verification
| Check | Result |
|-------|--------|
| GET /mcp returns 8 tools | PASS |
| POST /mcp/tools/list_documents | PASS — 6 context packs visible |
| POST /mcp/tools/get_document | PASS — governance.md content returned |
| MCP endpoint on Cloud Run URL | PASS — https://agent-data-test-pfne2mqwja-as.a.run.app/mcp |

**Claude.ai connector URL should be set to:**
`https://agent-data-test-pfne2mqwja-as.a.run.app/mcp`

---

## Part B: Context Pack Updates

### B1: agent-data.md (rev 3)
- Fixed MCP read tool endpoints: `/api/docs/tree` → `/kb/list`, `/api/docs/file` → `/kb/get/{doc_id}`
- Added note about legacy endpoints still working for GitHub docs
- Added MCP Protocol Endpoints section with Cloud Run connector URL

### B2: governance.md (rev 6)
- Enhanced Hybrid Principle section with data-specific clarification:
  - Local SERVICES → Cloud SERVICES (fallback)
  - Cloud for DATA (Firestore, Qdrant, GCS) — ONE SOURCE shared by local + cloud
  - Added: "Local and Cloud Run share the SAME Firestore (github-chatgpt-ggcloud)"

### B3: current-sprint.md (rev 3)
- Updated WEB-50A through 50E status (all DONE except 50E in progress)
- Added Key Fixes section (WEB-50D/E)
- Updated V3 Architecture progress (6 packs, 4 playbooks, 3 status docs)
- Updated blockers and key decisions

---

## Part C: Document Migration

### Migration Summary
| Category | Old Location | New V3 Location | Count |
|----------|-------------|-----------------|-------|
| Constitution | docs/ssot/ | docs/foundation/constitution/ | 1 |
| Laws | docs/ssot/ | docs/foundation/laws/ | 1 |
| Blueprints | docs/dev/blueprints/ | docs/plans/blueprints/ | 12 |
| Investigations | docs/dev/investigations/ | docs/operations/research/ | 6 |
| Reports | docs/dev/reports/ | docs/operations/sessions/ | 1 |
| SSOT specs | docs/dev/ssot/ | docs/plans/specs/ | 3 |
| SSOT processes | docs/dev/ssot/ | docs/plans/processes/ | 3 |
| SSOT sprint | docs/dev/ssot/ | docs/plans/sprints/ | 1 |
| Ops processes | docs/ops/ | docs/plans/processes/ | 3 |
| Ops specs | docs/ops/ | docs/plans/specs/ | 2 |
| Ops sessions | docs/ops/ | docs/operations/sessions/ | 1 |
| **Total** | | | **33 + 1 log** |

### Results
- **33/33 migrated** (1 initial timeout → confirmed created via 409 CONFLICT)
- Migration log uploaded to `docs/archive/migration-log.md`
- Original documents NOT deleted (backward compatible)
- All migrated docs tagged with `["migrated", "v3"]`

### Final KB Statistics
- **Total documents: 97** (was 62 before migration)
- V3 structure populated: blueprints (14), processes (7), specs (7), research (8), sessions (6)

---

## Files Modified
- `agent_data/server.py` — Added MCP protocol endpoints (`/mcp`, `/mcp/tools/{name}`) + `Request` import
- `content/context-packs/agent-data.md` — Fixed endpoint references, added MCP protocol section
- `content/context-packs/governance.md` — Enhanced Hybrid Principle with data clarification
- `content/context-packs/current-sprint.md` — Updated sprint progress through WEB-50E

## Files Created
- `scripts/migrate_v3.py` — Migration script (old GitHub docs → V3 Firestore KB)
- `content/migration-log.md` — Migration log with old→new path mapping
- `content/web-50e-report.md` — This report

## Cloud Run Revision History (WEB-50 series)
| Revision | Date | Content |
|----------|------|---------|
| 00049-xzp | 09:29 UTC | Slash fix + /kb/ endpoints |
| 00050-q86 | 09:53 UTC | /kb/ endpoints (traffic routed manually) |
| 00051-twq | 10:14 UTC | + MCP protocol endpoints (traffic routed manually) |

## Issues Found
1. **Cloud Run deploy doesn't auto-route to new revision** — must manually `gcloud run services update-traffic --to-revisions=REVISION=100`
2. **Python venv urllib lacks SSL certs** — migration script failed with `SSL: CERTIFICATE_VERIFY_FAILED` using urllib; fixed by switching to httpx
3. **Large document timeout** — agency-os-e1.md (218K chars) timed out on upload but was actually created (confirmed via 409)

## Governance Compliance
- No new Service Accounts (GC-LAW 1.3)
- Hybrid config maintained (local + cloud)
- No new UI components
- Original documents preserved (backward compatible)
- MCP endpoints added to existing server (No Code New principle — extended, not replaced)

## Next Steps
1. Configure Claude.ai connector to use: `https://agent-data-test-pfne2mqwja-as.a.run.app/mcp`
2. Update OpenAPI spec (`docs/api/openapi.yaml`) with new /kb/ and /mcp endpoints
3. Clean up old Cloud Run revisions (00048, 00049, slash-fix)
4. Proceed to WEB-50F: Discussions system + Active Triggers
