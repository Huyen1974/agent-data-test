# Context Pack: Current Sprint

> Load this pack to understand what's happening NOW and what's next.

## Purpose
Living document tracking current sprint objectives, completed work, and blockers.

**Last Updated**: 2026-02-06 (WEB-50C session)

## Current Objective: Information Architecture v3
Transform Agent Data from flat document store into a structured 3-tier knowledge system with AI-optimized access patterns.

## Sprint Progress

### Completed
| Ticket | Description | Status |
|--------|-------------|--------|
| WEB-50A | Add 5 MCP write tools to MCP server | DONE |
| WEB-50B | Slash fix (`{doc_id:path}` + `_fs_key()`) + V3 folder structure (19 folders + 3 templates) | DONE |
| WEB-50C | Hybrid config + Context Packs + Playbooks + Living Status Docs | IN PROGRESS |

### In Progress
- **WEB-50C**: This session
  - Part A: Hybrid MCP config (local priority, cloud fallback) — DONE
  - Part B: Slash fix verified end-to-end (Create→Update→Delete) — DONE
  - Part C: Context Packs, Playbooks, Living Status Docs — IN PROGRESS

### Next Up
| Ticket | Description | Dependencies |
|--------|-------------|-------------|
| WEB-50D | Discussions system + Active Triggers | WEB-50C context packs |
| WEB-51+ | Manager View + RAG Injection enhancements | V3 structure populated |

## V3 Architecture (7 Mechanisms)
1. **Context Packs** — AI onboarding documents (this sprint)
2. **Handoff Documents** — Session-to-session continuity
3. **Playbooks** — Step-by-step procedures (this sprint)
4. **Living Status Documents** — Auto-updated system state (this sprint)
5. **RAG Injection** — Vector search for knowledge retrieval
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

## Current Blockers
- Cloud Run needs redeployment for slash fix (in progress during WEB-50C)
- Qdrant vector sync depends on OpenAI API key being set

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
