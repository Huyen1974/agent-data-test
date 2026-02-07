# MCP Connector Guide - Agent Data

Connect Claude, GPT, Gemini, and other AI clients to the Agent Data knowledge base.

## Quick Start

### 1. Start Services

```bash
# From web-test directory
./dot/bin/dot-agent-up
```

### 2. Verify Services

```bash
./dot/bin/dot-agent-status
```

Expected output:
```
Agent Data (8000): RUNNING
MCP Server (8001): RUNNING
  Tools: ['search_knowledge', 'list_documents', 'get_document']
  Agent Data connection: connected
```

### 3. Stop Services

```bash
./dot/bin/dot-agent-down
```

---

## Connecting AI Clients

### Claude Desktop (MCP Native)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-data": {
      "command": "curl",
      "args": ["-N", "http://localhost:8001/mcp/sse"]
    }
  }
}
```

Or use HTTP transport:

```json
{
  "mcpServers": {
    "agent-data": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

After adding, restart Claude Desktop. You'll see 3 new tools:
- `search_knowledge` - Semantic search in knowledge base
- `list_documents` - List available documents
- `get_document` - Get specific document content

### Claude.ai MCP Connector

1. Go to Claude Settings → Connectors
2. Add new connector:
   - **Name**: Agent Data
   - **URL**: `http://localhost:8001/mcp`
3. Save and test with a query

### ChatGPT Custom Actions

1. Go to GPT Editor → Configure → Actions
2. Add new action with this OpenAPI schema:

```yaml
openapi: 3.0.0
info:
  title: Agent Data MCP
  version: 1.0.0
servers:
  - url: http://localhost:8001
paths:
  /mcp/tools/search_knowledge:
    post:
      operationId: searchKnowledge
      summary: Search the knowledge base
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                  description: Search query
              required:
                - query
      responses:
        '200':
          description: Search results
```

### Gemini / Other AI

Use REST API directly:

```bash
# Search knowledge base
curl -X POST http://localhost:8001/mcp/tools/search_knowledge \
  -H "Content-Type: application/json" \
  -d '{"query": "your search query"}'

# List documents
curl -X POST http://localhost:8001/mcp/tools/list_documents \
  -H "Content-Type: application/json" \
  -d '{}'

# Get specific document
curl -X POST http://localhost:8001/mcp/tools/get_document \
  -H "Content-Type: application/json" \
  -d '{"document_id": "doc-id-here"}'
```

---

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Quick reference |
| `/mcp` | GET | Server info & tools list |
| `/mcp/tools/search_knowledge` | POST | Semantic RAG search |
| `/mcp/tools/list_documents` | POST | List documents |
| `/mcp/tools/get_document` | POST | Get document content |
| `/mcp/sse` | GET | SSE stream for MCP protocol |
| `/health` | GET | Health check with connectivity |

### Tool: search_knowledge

Search the knowledge base using semantic/RAG query.

**Request:**
```json
{
  "query": "What are the system principles?",
  "limit": 5
}
```

**Response:**
```json
{
  "result": {
    "response": "...",
    "content": "...",
    "context": [
      {
        "document_id": "doc-123",
        "snippet": "...",
        "score": 0.95,
        "metadata": {...}
      }
    ],
    "usage": {
      "latency_ms": 150,
      "qdrant_hits": 3
    }
  }
}
```

### Tool: list_documents

List available documents with optional path filter.

**Request:**
```json
{
  "path": "docs/"
}
```

### Tool: get_document

Get full content of a specific document.

**Request:**
```json
{
  "document_id": "governance/constitution.md"
}
```

---

## Troubleshooting

### Port already in use

```bash
# Stop all services
./dot/bin/dot-agent-down

# Wait a moment, then restart
./dot/bin/dot-agent-up
```

### Check logs

```bash
# Agent Data logs
tail -f /tmp/agent-data.log

# MCP Server logs
tail -f /tmp/mcp-server.log
```

### Connection refused

1. Verify services are running:
   ```bash
   ./dot/bin/dot-agent-status
   ```

2. Check if ports are accessible:
   ```bash
   curl http://localhost:8000/info
   curl http://localhost:8001/health
   ```

3. Check firewall settings if connecting from another device

### MCP tools not appearing in Claude

1. Verify MCP server returns tools:
   ```bash
   curl http://localhost:8001/mcp | jq '.tools[].name'
   ```

2. Restart Claude Desktop after config changes

3. Check Claude Desktop logs for MCP errors

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude/GPT/    │────▶│   MCP Server    │────▶│   Agent Data    │
│  Gemini Client  │     │   (port 8001)   │     │   (port 8000)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                        │
                               │                        ▼
                               │                ┌───────────────┐
                               │                │ Qdrant Cloud  │
                               │                │ (Vector DB)   │
                               │                └───────────────┘
                               │                        │
                               └────────────────────────┘
```

The MCP Server acts as a protocol translator, exposing Agent Data capabilities through the MCP standard that AI clients understand.
