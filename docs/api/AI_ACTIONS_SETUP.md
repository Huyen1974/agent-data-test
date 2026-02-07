# AI Actions Setup Guide

## Overview

This guide explains how to connect various AI platforms to the Agent Data knowledge base.

## Endpoints

| Environment | URL |
|-------------|-----|
| Local | http://localhost:8000 |
| Cloud Run | https://agent-data-test-pfne2mqwja-as.a.run.app |

---

## Claude (MCP Protocol)

### Claude Desktop

1. Ensure MCP Server is running:
   ```bash
   ./dot/bin/dot-agent-up
   ```

2. Config file location: `~/Library/Application Support/Claude/claude_desktop_config.json`

3. Required configuration:
   ```json
   {
     "mcpServers": {
       "agent-data": {
         "url": "http://localhost:8001/mcp"
       }
     }
   }
   ```

4. Restart Claude Desktop

5. Test with prompt: "Use agent-data to search for system principles"

### Claude Code CLI

Uses MCP automatically when configured. Test with:
```bash
./dot/bin/dot-mcp-verify
```

---

## Gemini (Google AI Studio)

### Setup Steps

1. Go to https://aistudio.google.com
2. Create new Gem or use Custom Instructions
3. Navigate to Actions → Add Action
4. Import OpenAPI spec:
   - Upload `openapi.yaml` file, OR
   - Paste the content directly
5. Set server URL to Cloud Run endpoint
6. Configure authentication if needed

### Test Prompts

- "Search for information about system constitution"
- "What documents are in the knowledge base?"

---

## ChatGPT (OpenAI GPTs)

### Setup Steps

1. Go to https://chat.openai.com
2. Navigate to: Explore → Create a GPT
3. Click Configure → Actions
4. Click "Create new action"
5. Import schema from `openapi.yaml`
6. Set server URL: `https://agent-data-test-pfne2mqwja-as.a.run.app`
7. Save and test

### Test Prompts

- "Search the knowledge base for infrastructure guidelines"
- "Get system health status"

---

## CLI Agents (Agent First)

All agents can use DOT tools directly:

```bash
# Search knowledge base
./dot/bin/dot-knowledge-search "your query here"

# Get system info
./dot/bin/dot-knowledge-info

# Ingest new document
./dot/bin/dot-knowledge-ingest gs://bucket/path/to/file.pdf

# Verify all connections
./dot/bin/dot-ai-connect-all
```

---

## Verification Checklist

| Platform | Test Command | Expected |
|----------|--------------|----------|
| Claude Desktop | MCP tools visible | 3 tools listed |
| MCP Server | `curl localhost:8001/mcp` | JSON response |
| Agent Data | `curl localhost:8000/info` | Version info |
| Gemini | Action test | Search results |
| ChatGPT | GPT action test | Search results |

---

## Troubleshooting

### MCP Server not responding

```bash
./dot/bin/dot-agent-down
./dot/bin/dot-agent-up
./dot/bin/dot-mcp-verify
```

### Claude Desktop not showing tools

1. Verify config file exists and is valid JSON
2. Restart Claude Desktop completely
3. Check MCP server logs: `tail -f /tmp/mcp-server.log`

### Search returns no results

1. Verify Qdrant connection: `curl localhost:8000/info`
2. Check collection exists with documents
3. Try different query terms
