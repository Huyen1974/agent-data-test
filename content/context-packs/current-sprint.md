# Context Pack: Current Sprint

> Load this pack to understand what's happening NOW and what's next.

## Purpose
Living document tracking current sprint objectives, completed work, and blockers.

**Last Updated**: 2026-02-06 (WEB-50F — session complete)

## Current Objective: Information Architecture v3
Transform Agent Data from flat document store into a structured 3-tier knowledge system with AI-optimized access patterns.

## Sprint Progress

### Completed
| Ticket | Description | Status |
|--------|-------------|--------|
| WEB-50A | Add 5 MCP write tools to MCP server | DONE |
| WEB-50B | Slash fix (`{doc_id:path}` + `_fs_key()`) + V3 folder structure (19 folders + 3 templates) | DONE |
| WEB-50C | Hybrid config + Context Packs + Playbooks + Living Status Docs | DONE |
| WEB-50D | Fix MCP data visibility — root cause: tools used GitHub API not Firestore. Added `/kb/list` + `/kb/get/` endpoints | DONE |
| WEB-50E | Fix MCP Cloud connector — added MCP protocol endpoints to Cloud Run. Updated context packs. Document migration. | DONE |
| WEB-50F | Fix list/get default prefix. OpenAPI v2.0.0 with /kb/ + /mcp endpoints. WEB-50 session report. | DONE |

### Key Fixes (WEB-50D/E/F)
- MCP tools now use `/kb/list` and `/kb/get/{doc_id}` (Firestore KB) instead of `/api/docs/tree` (GitHub)
- Cloud Run serves MCP protocol directly via `/mcp` and `/mcp/tools/{name}`
- Default list_documents prefix = "docs" (shows V3 structure)
- OpenAPI spec v2.0.0 includes /kb/, /mcp endpoints
- Claude.ai connector URL: `https://agent-data-test-pfne2mqwja-as.a.run.app/mcp`
- 98 documents total in KB (V3 + migrated + reports)

### Next Up
| Ticket | Description | Dependencies |
|--------|-------------|-------------|
| WEB-51+ | Discussions system + Active Triggers | WEB-50 complete |
| WEB-52+ | Manager View + RAG Injection enhancements | V3 structure populated |

## V3 Architecture (7 Mechanisms)
1. **Context Packs** — AI onboarding documents (DONE: 6 packs)
2. **Handoff Documents** — Session-to-session continuity (future)
3. **Playbooks** — Step-by-step procedures (DONE: 4 playbooks)
4. **Living Status Documents** — Auto-updated system state (DONE: 3 docs)
5. **RAG Injection** — Vector search for knowledge retrieval (partially working)
6. **Active Triggers** — Event-driven document updates (next sprint)
7. **Manager View** — Dashboard for human oversight (future)

## V3 Structure (3 Tiers)
```
Tier 1: Foundation  → docs/foundation/ (constitution, laws, architecture)
Tier 2: Plans       → docs/plans/ (blueprints, sprints, specs)
Tier 3: Operations  → docs/operations/ (sessions, research, decisions)
Cross-cutting:      → context-packs, playbooks, status, discussions, templates
```

## Key Decisions Made
- Slash paths in document IDs: Use `_fs_key()` encoding for Firestore
- Hybrid config: Local priority with cloud fallback (NEVER single-path)
- No new code: Use existing Agency OS + Directus + Agent Data
- Single SA: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com`
- MCP endpoints added directly to agent_data/server.py (no separate MCP Cloud Run service)
- Local and Cloud share same Firestore — data is always in sync

## Current Blockers
- Qdrant vector sync depends on OpenAI API key being set
- Claude.ai connector needs manual reconfiguration to point to cloud URL

## How to Continue This Sprint
1. Load context packs: governance + current-sprint + agent-data
2. Check task board for next ticket
3. Follow relevant playbook for the task type
4. Write session report to `docs/operations/sessions/`
5. Update this document with progress

## Related Documents
- `docs/context-packs/governance.md` — Rules and constraints
- `docs/context-packs/agent-data.md` — API reference
- `docs/operations/sessions/` — Session reports
