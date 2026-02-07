# WEB-59: MCP STDIO Transport for Claude Desktop

**Date**: 2026-02-04
**Status**: COMPLETE

## Executive Summary

Created and verified MCP Server with STDIO transport for native Claude Desktop integration. The stdio transport is required by Claude Desktop (HTTP/SSE is not supported).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude Desktop                        │
│                         │                                │
│                    [stdio pipe]                          │
│                         │                                │
│              ┌──────────▼──────────┐                    │
│              │   stdio_server.py   │                    │
│              │   (MCP SDK stdio)   │                    │
│              └──────────┬──────────┘                    │
└─────────────────────────┼───────────────────────────────┘
                          │ HTTP
                          ▼
                ┌─────────────────┐
                │   Agent Data    │
                │  (localhost:    │
                │     8000)       │
                └─────────────────┘
```

## Implementation

### 1. MCP STDIO Server (`mcp_server/stdio_server.py`)

Uses official MCP SDK with stdio transport:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("agent-data")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name="search_knowledge", ...),
        Tool(name="list_documents", ...),
        Tool(name="get_document", ...),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Calls Agent Data HTTP API
    ...

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, ...)
```

### 2. Claude Desktop Configuration

Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-data": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_server.stdio_server"],
      "env": {
        "AGENT_DATA_URL": "http://localhost:8000"
      }
    }
  }
}
```

### 3. Test Mode

Added `--test` flag for verification without running full server:

```bash
python mcp_server/stdio_server.py --test
```

Output:
```
MCP STDIO Server Test
=====================
Agent Data URL: http://localhost:8000
Tools available: 3
  - search_knowledge: Search the knowledge base using semantic/RAG query...
  - list_documents: List available documents in the knowledge base...
  - get_document: Get full content of a specific document by its ID...
Agent Data connection: OK
=====================
Test completed successfully!
```

## Tools Available in Claude Desktop

| Tool | Description |
|------|-------------|
| `search_knowledge` | Semantic RAG search across knowledge base |
| `list_documents` | List documents with optional path filter |
| `get_document` | Retrieve full document by ID |

## DOT Tool Created

- `dot-mcp-stdio-restart` - Restart Claude Desktop with MCP verification

## Verification Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | stdio_server.py exists | PASS |
| 2 | Uses official MCP SDK | PASS |
| 3 | --test flag works | PASS |
| 4 | Claude config has mcpServers | PASS |
| 5 | Agent Data connection OK | PASS |
| 6 | 3 tools registered | PASS |
| 7 | dot-mcp-stdio-restart created | PASS |

## Files Created/Modified

| File | Action |
|------|--------|
| `mcp_server/stdio_server.py` | Created (STDIO MCP server) |
| `claude_desktop_config.json` | Updated (mcpServers config) |
| `dot/bin/dot-mcp-stdio-restart` | Created (restart tool) |
| `reports/WEB-59-MCP-STDIO.md` | Created (this report) |

## Usage

### Quick Start

```bash
# 1. Start Agent Data
dot-agent-up

# 2. Test MCP server
python mcp_server/stdio_server.py --test

# 3. Restart Claude Desktop
dot-mcp-stdio-restart --verify
```

### Using in Claude Desktop

After restart, look for the hammer icon (🔨) in the chat input area. Click it to see available MCP tools:
- search_knowledge
- list_documents
- get_document

### Example Queries

In Claude Desktop chat:
- "Search my knowledge base for Terraform IaC"
- "List all documents"
- "Get the constitution document"

## Troubleshooting

### Tools not appearing
1. Check `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Ensure Agent Data is running: `curl http://localhost:8000/info`
3. Restart Claude Desktop: `dot-mcp-stdio-restart`

### Connection errors
1. Verify Agent Data is running on port 8000
2. Check `AGENT_DATA_URL` environment variable in config
3. Test with: `python mcp_server/stdio_server.py --test`

## Summary

STDIO transport is now the primary method for Claude Desktop MCP integration. The HTTP MCP server (port 8001) remains available for other clients (ChatGPT Actions, Gemini, etc.) but Claude Desktop exclusively uses the stdio transport through `stdio_server.py`.
