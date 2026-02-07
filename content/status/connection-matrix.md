# Living Status: Connection Matrix

> Which AI connects to what, via which endpoint, using what auth method.

**Last Updated**: 2026-02-06

## AI Agent Connections

| AI Agent | Connection Type | Endpoint | Auth Method | Status |
|----------|----------------|----------|-------------|--------|
| Claude Desktop | MCP STDIO | Local via stdio_server.py | API Key (env) | ACTIVE |
| Claude Desktop | MCP Fallback | Cloud Run URL | API Key + IAM Token | ACTIVE |
| ChatGPT (GPT Actions) | OpenAPI/REST | Cloud Run URL | X-API-Key header | CONFIGURED |
| Google Gemini | Extensions API | Cloud Run URL | X-API-Key header | CONFIGURED |
| Claude Code | Direct HTTP | localhost:8000 | API Key | ACTIVE |

## Connection Details

### Claude Desktop (Primary)
```
Protocol:  MCP (Model Context Protocol) over STDIO
Transport: stdio_server.py spawned as subprocess
Primary:   http://localhost:8000 (local Agent Data)
Fallback:  https://agent-data-test-pfne2mqwja-as.a.run.app (cloud)
Auth:      AGENT_DATA_API_KEY_LOCAL / AGENT_DATA_API_KEY_CLOUD
Config:    ~/Library/Application Support/Claude/claude_desktop_config.json
Mode:      Hybrid (local priority, cloud fallback)
Tools:     8 (search_knowledge, list_documents, get_document, upload_document,
           update_document, delete_document, move_document, ingest_document)
```

### ChatGPT (GPT Actions)
```
Protocol:  OpenAPI REST
Spec:      docs/api/openapi.yaml
Endpoint:  https://agent-data-test-pfne2mqwja-as.a.run.app
Auth:      X-API-Key header (Custom Authentication)
Actions:   searchKnowledge (POST /chat), healthCheck (GET /health),
           getSystemInfo (GET /info), listDocuments (GET /api/docs/tree),
           getDocument (GET /api/docs/file)
Setup:     docs/GPT_ACTIONS_SETUP.md
```

### Google Gemini (Extensions)
```
Protocol:  Vertex AI Extensions / Google AI Studio
Endpoint:  https://agent-data-test-pfne2mqwja-as.a.run.app
Auth:      X-API-Key header
Setup:     docs/GEMINI_EXTENSIONS_SETUP.md
```

## Service-to-Service Connections

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Agent Data API | Firestore | gRPC | Document storage |
| Agent Data API | Qdrant Cloud | HTTPS | Vector search |
| Agent Data API | OpenAI API | HTTPS | Embeddings |
| Agent Data API | Pub/Sub | gRPC | Async task queue |
| Cloud Scheduler | timer_callback | HTTPS | Keep Qdrant warm |
| MCP STDIO | Agent Data API | HTTP | Tool execution |
| MCP HTTP | Agent Data API | HTTP | Tool execution |

## Endpoint Health Check Commands
```bash
# Local Agent Data
curl -s http://localhost:8000/health

# Cloud Agent Data
curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://agent-data-test-pfne2mqwja-as.a.run.app/health

# Local MCP HTTP
curl -s http://localhost:8001/health

# MCP STDIO test
venv/bin/python mcp_server/stdio_server.py --test

# Full test suite
dot/bin/dot-ai-test-all
```

## Troubleshooting

| Issue | Check |
|-------|-------|
| Claude Desktop can't connect | Is local Agent Data running? (`curl localhost:8000/health`) |
| ChatGPT Actions fail | Is Cloud Run healthy? Check IAM and API key |
| MCP tools return errors | Check `stdio_server.py --test` output |
| Hybrid fallback not working | Check both URLs in claude_desktop_config.json |
| 403 on Cloud Run | Identity token expired? Run `gcloud auth login` |
