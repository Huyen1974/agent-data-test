# Context Pack: Agent Data

> Load this pack for any task involving the Agent Data knowledge base API.

## Purpose
Complete API reference for the Agent Data service — the central knowledge hub.

## Prerequisites
- Agent Data running locally (port 8000) or available on Cloud Run
- API key for write operations

## Base URLs
| Environment | URL | API Key Source |
|-------------|-----|---------------|
| Local | `http://localhost:8000` | `test-key-local` (env: API_KEY) |
| Cloud | `https://agent-data-test-pfne2mqwja-as.a.run.app` | Secret Manager: `agent-data-api-key` |

## Authentication
- **Read endpoints**: No auth required (local) / IAM token required (cloud)
- **Write endpoints**: `X-API-Key` header required
- **Cloud Run**: Also needs `Authorization: Bearer <identity-token>` header

## MCP Tools (8 total)

### Read Tools (3)
| Tool | Description | Endpoint |
|------|-------------|----------|
| `search_knowledge` | RAG semantic search | POST /chat |
| `list_documents` | List docs in tree | GET /api/docs/tree |
| `get_document` | Get document content | GET /api/docs/file |

### Write Tools (5) — Require API Key
| Tool | Description | Endpoint |
|------|-------------|----------|
| `upload_document` | Create new document | POST /documents |
| `update_document` | Update existing doc | PUT /documents/{id:path} |
| `delete_document` | Soft-delete document | DELETE /documents/{id:path} |
| `move_document` | Move doc to new parent | POST /documents/{id:path}/move |
| `ingest_document` | Ingest from GCS/URL | POST /ingest |

## API Endpoints Detail

### POST /chat (Search/RAG)
```json
// Request
{"message": "search query in natural language"}

// Response
{
  "response": "AI-generated answer",
  "content": "same as response",
  "context": [{"document_id": "...", "snippet": "...", "score": 0.9}],
  "usage": {"latency_ms": 150, "qdrant_hits": 3}
}
```

### POST /documents (Create)
```json
// Request
{
  "document_id": "docs/context-packs/governance.md",
  "parent_id": "docs/context-packs",
  "content": {"mime_type": "text/markdown", "body": "# Content here"},
  "metadata": {"title": "Governance Pack", "tags": ["context-pack"]}
}

// Response
{"id": "docs/context-packs/governance.md", "status": "created", "revision": 1}
```

### PUT /documents/{doc_id:path} (Update)
```json
// Request
{
  "document_id": "docs/context-packs/governance.md",
  "patch": {"content": {"mime_type": "text/markdown", "body": "# Updated"}},
  "update_mask": ["content"]
}

// Response
{"id": "...", "status": "updated", "revision": 2}
```

### DELETE /documents/{doc_id:path} (Soft Delete)
```
// Response
{"id": "...", "status": "deleted", "revision": 3}
```

## Slash Path Support
- Document IDs can contain slashes: `docs/foundation/constitution.md`
- FastAPI route uses `{doc_id:path}` to capture full path
- Firestore key encoding: `docs/test/file` → `docs__test__file` (via `_fs_key()`)
- Both slash paths and flat IDs work (backward compatible)

## V3 Directory Structure
```
docs/
├── foundation/          # Constitutional documents
│   ├── constitution/    # Core constitution
│   ├── laws/           # GC-LAW rules
│   └── architecture/   # System architecture decisions
├── plans/              # Forward-looking documents
│   ├── blueprints/     # Feature blueprints
│   ├── sprints/        # Sprint plans
│   ├── processes/      # Process definitions
│   └── specs/          # Technical specifications
├── operations/         # Execution records
│   ├── sessions/       # Work session reports
│   ├── research/       # Investigation reports
│   ├── decisions/      # ADR records
│   └── lessons/        # Lessons learned
├── context-packs/      # AI onboarding packs (THIS!)
├── playbooks/          # Step-by-step procedures
├── status/             # Living status documents
├── discussions/        # Ongoing discussions
└── templates/          # Document templates
```

## Vector Search (Qdrant)
- Documents are auto-synced to Qdrant on create/update
- Collection: `{APP_ENV}_documents` (e.g., `development_documents`)
- Embeddings via OpenAI
- `vector_status` field tracks sync state: pending → synced/error/skipped

## OpenAPI Spec
Location: `docs/api/openapi.yaml`
- Version: 3.1.0
- Servers: localhost:8000 and Cloud Run URL

## Related Documents
- `docs/context-packs/infrastructure.md` — GCP infrastructure details
- `docs/api/openapi.yaml` — Full OpenAPI specification
- `docs/templates/session-report.md` — Template for session reports
