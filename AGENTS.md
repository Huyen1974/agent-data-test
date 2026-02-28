# AGENTS.md — Multi-Agent MCP Configuration

> **⛔ FIRST: `search_knowledge('operating rules SSOT')` before any work.**

## Overview

Three AI agents share the same MCP server for knowledge-base CRUD. This file defines the shared protocol, tool inventory, and enforcement layers.

## Agents

| Agent | IDE | Transport | Config File |
|-------|-----|-----------|-------------|
| Claude Code | Terminal / VS Code | stdio | `.mcp.json` |
| Claude Desktop | Desktop app | stdio | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| OpenAI Codex | Terminal | stdio | `.codex/config.toml` |

All agents connect to the **same MCP server** (`mcp_server/stdio_server.py`) which proxies to VPS Agent Data API.

## MCP Server

- **Entry point**: `mcp_server/stdio_server.py`
- **Transport**: stdio (stdin/stdout JSON-RPC)
- **Backend**: VPS Agent Data API at `https://vps.incomexsaigoncorp.vn/api`
- **Fallback**: Hybrid — tries local first, then cloud
- **Auth**: `X-API-Key` header + optional `gcloud auth print-identity-token` for Cloud Run

## Tools (11)

### Read Tools (5)
1. **`search_knowledge`** — Semantic/RAG search. Input: `query` (string). Returns relevant docs + sources.
2. **`list_documents`** — List by prefix. Input: `path` (string, optional). Returns document IDs + tags.
3. **`get_document`** — Truncated content + related docs via vector search. Input: `document_id`. Use for reading/reference.
4. **`get_document_for_rewrite`** — Full content. Input: `path`. Use ONLY when rewriting entire document.
5. **`batch_read`** — Read multiple docs. Input: `paths` (array, max 20), `full` (boolean). Returns all contents.

### Write Tools (6)
6. **`upload_document`** — Create new doc. Input: `path`, `content`, optional `title`, `tags`.
7. **`update_document`** — Replace content. Input: `path`, `content`, optional `title`, `tags`.
8. **`patch_document`** — Find-and-replace. Input: `path`, `old_str`, `new_str`. Returns 409 if ambiguous.
9. **`delete_document`** — Delete doc. Input: `path`.
10. **`move_document`** — Move to new parent. Input: `path`, `new_path`. Use `root` for top level.
11. **`ingest_document`** — Ingest from URI. Input: `source` (GCS URI or URL).

## Enforcement Layers

### Layer 1: Pre-push Hook (TD-019)
`.githooks/pre-push` blocks direct push to `main`. Requires feature branch + PR workflow.
```
git config core.hooksPath .githooks
```

### Layer 2: Embedding Cost Filter (TD-018)
`agent_data/directus_sync.py` — `_SYNC_PREFIXES = ("knowledge/",)` ensures only knowledge docs trigger Directus sync and embedding. Operations docs (`operations/*`) are excluded.

### Layer 3: CLAUDE.md Rules
6 mandatory rules loaded at session start. Agents must call `search_knowledge('operating rules SSOT')` before any work.

### Layer 4: MCP-Only CRUD
All document operations go through MCP tools. No raw HTTP, no direct DB access. This ensures consistent auth, logging, and vector sync.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `AGENT_DATA_URL` | Primary API endpoint (default: `http://localhost:8000`) |
| `AGENT_DATA_URL_CLOUD` | Cloud fallback endpoint |
| `AGENT_DATA_API_KEY` | API key for X-API-Key header |
| `AGENT_DATA_API_KEY_LOCAL` | Local-specific API key |
| `AGENT_DATA_API_KEY_CLOUD` | Cloud-specific API key |
| `AGENT_DATA_PREFER` | `local` or `cloud` preference |

---

## Quick-Task Protocol — Tac vu nho, quy trinh gon

### Phan loai tac vu

| Loai | Vi du | Quy trinh |
|------|-------|-----------|
| **Quick** | Tao comment, upload 1 file, doc data, patch 1 doan | Goi MCP tool truc tiep → bao ket qua 1 dong |
| **Standard** | Fix bug, them feature nho, seed data, sua config | Branch → commit → CI → merge → verify |
| **Mission** | Audit, tich hop moi, refactor, multi-phase | Full mission template + verify checklist |

### Quick-Task: Goi truc tiep, khong ceremony

Khi nhan yeu cau don gian (tao comment, upload doc, doc data):

1. **KHONG can** khao sat schema truoc (tru lan dau dung collection moi)
2. **KHONG can** full verify chain — confirm ket qua 1 buoc la du
3. **KHONG can** tao report file
4. **Goi MCP tool truc tiep** → tra ket qua ngan gon

Vi du Quick-Task — tao comment:
```
directus_create_item(collection="task_comments", data={
  "task_id": 7,
  "content": "Noi dung comment",
  "action": "comment"
})
→ Tra: "Comment #ID tao thanh cong tren task 7"
```

Vi du Quick-Task — upload document:
```
upload_document(path="knowledge/...", content="# Title\n...")
→ Tra: "Document tao tai path X, revision 1"
```

### Khi nao PHAI dung full process

- Thay doi schema Directus
- Sua code (bat ky .ts/.vue/.py file)
- Thay doi infrastructure/config
- Tao hoac sua nhieu items cung luc (>5)
- Bat ky thay doi nao can CI/CD

### Common Quick-Task references

| Task | Tool | Key fields |
|------|------|------------|
| Comment tren task | `directus_create_item("task_comments", {...})` | task_id, content, action="comment" |
| Upload knowledge doc | `upload_document(path, content)` | path theo KS-LAW 4 folders |
| Patch document | `patch_document(path, old_str, new_str)` | exact match old_str |
| Search knowledge | `search_knowledge("query")` | — |
| Doc Directus items | `directus_get_items(collection, fields, limit)` | tasks dung `name` (khong phai title) |
