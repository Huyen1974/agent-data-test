# SESSION REPORT: WEB-50 — Kiến trúc Thông tin v3

## Status: COMPLETED
**Date**: 2026-02-06
**Branch**: main

---

## Tổng quan

Phiên WEB-50 thực hiện "đóng băng" Kiến trúc Thông tin v3 cho Agent Data — biến nó từ kho tài liệu phẳng thành hệ thống tri thức 3 tầng có cấu trúc, tối ưu cho AI.

**Kết quả cuối cùng:**
- 98 documents trong Firestore KB
- 8 MCP tools (3 read + 5 write) hoạt động trên cả local và cloud
- V3 structure hoàn chỉnh với 3 tầng + cross-cutting documents
- MCP protocol endpoints nhúng trong Cloud Run (không cần service riêng)
- 33 documents cũ đã migrate vào V3

---

## Missions thực hiện

| Mission | Mục tiêu | Kết quả | Files Modified |
|---------|----------|---------|----------------|
| WEB-50A | Bổ sung MCP Write Tools | 5 write tools thêm vào MCP server (8 total) | mcp_server/server.py, stdio_server.py |
| WEB-50B | Fix slash paths + V3 folder structure | `_fs_key()` + `{doc_id:path}`, 19 V3 folders | agent_data/server.py |
| WEB-50C | Hybrid config + Context Packs + Playbooks | 13 documents created, hybrid fallback | stdio_server.py, server.py, claude_desktop_config.json |
| WEB-50D | Fix MCP data visibility | Root cause: GitHub vs Firestore endpoints. Added `/kb/list` + `/kb/get/` | agent_data/server.py, mcp_server/*.py |
| WEB-50E | Fix Cloud connector + Migration | MCP protocol trên Cloud Run, 33 docs migrated | agent_data/server.py, scripts/migrate_v3.py |
| WEB-50F | Fix list/get default + OpenAPI + Session report | Default prefix "docs", OpenAPI v2.0.0 | agent_data/server.py, docs/api/openapi.yaml |

---

## Quyết định quan trọng

### 1. Kiến trúc Thông tin v3 — 3 Tầng + Cross-cutting
```
Tầng 1: Foundation  → docs/foundation/ (constitution, laws, architecture)
Tầng 2: Plans       → docs/plans/ (blueprints, sprints, specs, processes)
Tầng 3: Operations  → docs/operations/ (sessions, research, decisions, lessons)
Cross-cutting:      → context-packs/, playbooks/, status/, discussions/, templates/
```

### 2. Agent Data = Trung tâm tri thức duy nhất
- TẤT CẢ AI agents (Claude, GPT, Gemini) đều kết nối qua Agent Data
- Firestore KB là nguồn dữ liệu chính (shared giữa local + cloud)
- GitHub docs (`/api/docs/tree`) là nguồn phụ (repo files)

### 3. Nguyên tắc Hybrid bắt buộc
```
Services: Local (priority) → Cloud (fallback)
Data: Cloud Firestore (ONE source, shared by local + cloud)
Config: LUÔN giữ cả 2 đường, KHÔNG BAO GIỜ chỉ 1 path
```

### 4. MCP endpoints nhúng trong server chính
- Không tạo Cloud Run service riêng cho MCP
- `/mcp` và `/mcp/tools/{name}` thêm trực tiếp vào agent_data/server.py
- Tools dispatch đến internal functions (không proxy HTTP)

### 5. SSOT = Tầng 1 (Foundation) only
- Hiến pháp + Luật nằm trong `docs/foundation/`
- Mọi thứ khác (blueprints, specs, processes, etc.) vào Agent Data KB

---

## 7 Cơ chế v3

| # | Cơ chế | Trạng thái | Documents |
|---|--------|------------|-----------|
| 1 | Context Packs | ✅ DONE | 6 packs (governance, agent-data, web-frontend, infrastructure, directus, current-sprint) |
| 2 | Handoff Documents | ⏳ Future | Session reports serve as handoff |
| 3 | Playbooks | ✅ DONE | 4 playbooks (assembly, infrastructure, investigation, integration) |
| 4 | Living Status | ✅ DONE | 3 docs (system-inventory, dot-tools-registry, connection-matrix) |
| 5 | RAG Injection | ✅ Working | Via POST /chat (langroid + Qdrant) |
| 6 | Active Triggers | ⏳ Next | Webhook/event-driven updates |
| 7 | Manager View | ⏳ Future | Dashboard for human oversight |

---

## Bài học kinh nghiệm

### 1. MCP tools đọc sai endpoint
**Vấn đề**: `list_documents` gọi `/api/docs/tree` (GitHub) thay vì Firestore KB.
**Bài học**: Phải verify E2E từ cloud endpoint, không chỉ local. MCP dispatch cần test riêng.

### 2. Config chỉ local, thiếu cloud fallback
**Vấn đề**: claude_desktop_config.json ban đầu chỉ có cloud URL.
**Bài học**: LUÔN giữ cả local + cloud. Nguyên tắc hybrid là bắt buộc.

### 3. Agent báo PASS nhưng data chỉ trên local
**Vấn đề**: Data tạo trên local OK, nhưng cloud MCP tools trả kết quả khác.
**Bài học**: Verify từ CLOUD endpoint. Local và cloud chia sẻ cùng Firestore, nhưng MCP tools có thể dispatch sai.

### 4. Cloud Run OOM và revision caching
**Vấn đề**: 512Mi OOM cho langroid. Deploy không auto-route traffic.
**Bài học**: Luôn dùng 1Gi. Sau deploy, kiểm tra revision + manual `update-traffic` nếu cần.

### 5. SSL certificate trên macOS Python venv
**Vấn đề**: urllib có SSL cert issues. Scripts migration fail.
**Bài học**: Dùng httpx thay vì urllib cho HTTPS calls.

---

## Trạng thái kết thúc phiên

### Documents
| Category | Count |
|----------|-------|
| V3 folders + READMEs | 34 |
| Context Packs | 6 |
| Playbooks | 4 |
| Status docs | 3 |
| Templates | 3 |
| Session reports | 5 |
| Migrated docs | 34 |
| Other (old flat IDs) | 6 |
| Migration log | 1 |
| **Total** | **98** |

### MCP Tools
| Tool | Type | Cloud Status |
|------|------|-------------|
| search_knowledge | Read | ✅ Working |
| list_documents | Read | ✅ Fixed (WEB-50D/F) |
| get_document | Read | ✅ Fixed (WEB-50D/F) |
| upload_document | Write | ✅ Working |
| update_document | Write | ✅ Working |
| delete_document | Write | ✅ Working |
| move_document | Write | ✅ Working |
| ingest_document | Write | ✅ Working |

### Endpoints
| Endpoint | Purpose | Status |
|----------|---------|--------|
| POST /chat | RAG search | ✅ |
| GET /kb/list | List KB documents | ✅ New (WEB-50D) |
| GET /kb/get/{doc_id} | Get KB document | ✅ New (WEB-50D) |
| GET /mcp | MCP tool discovery | ✅ New (WEB-50E) |
| POST /mcp/tools/{name} | MCP tool execution | ✅ New (WEB-50E) |
| POST /documents | Create document | ✅ |
| PUT /documents/{id} | Update document | ✅ |
| DELETE /documents/{id} | Delete document | ✅ |

### Cloud Run
- Service: `agent-data-test`
- Region: `asia-southeast1`
- Memory: 1Gi
- Revision: 00052+ (WEB-50F deploy)
- SA: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com`

---

## Việc tiếp theo (Giai đoạn 4)

1. **Discussion System**: Cho AI handoff giữa các sessions
2. **Active Triggers**: Webhook/events tự động cập nhật documents
3. **Kestra Integration**: Kết nối workflow engine
4. **Manager View**: Dashboard cho human oversight
5. **Claude.ai connector auth**: Cần giải quyết IAM auth cho Claude.ai connector

---

## Files Modified (tổng hợp WEB-50A→F)

| File | Missions | Description |
|------|----------|-------------|
| agent_data/server.py | 50B, 50D, 50E, 50F | Slash fix, /kb/ endpoints, MCP protocol, default prefix |
| mcp_server/stdio_server.py | 50A, 50C, 50D | Write tools, hybrid config, /kb/ endpoints |
| mcp_server/server.py | 50A, 50C, 50D | Same as stdio for HTTP MCP |
| docs/api/openapi.yaml | 50F | Added /kb/, /mcp endpoints |
| scripts/upload_content.py | 50C | Batch upload 13 content docs |
| scripts/migrate_v3.py | 50E | Migrate 33 old docs to V3 |
| content/context-packs/*.md | 50C, 50E | 6 context packs |
| content/playbooks/*.md | 50C | 4 playbooks |
| content/status/*.md | 50C | 3 status docs |

## Governance Compliance
- ✅ No new Service Accounts (GC-LAW §1.3)
- ✅ Hybrid config maintained (local + cloud)
- ✅ No new UI components
- ✅ Existing code extended, not replaced
- ✅ All changes verified E2E on cloud
