# WEB-59c: Fix Claude Desktop MCP với Venv Python

**Date**: 2026-02-05
**Status**: COMPLETE

## Problem

Claude Desktop báo "Server disconnected" vì config đang dùng đường dẫn không đúng hoặc thiếu thư viện.

## Root Cause

Script chạy với Python thiếu thư viện MCP → ModuleNotFoundError → Crash → Disconnected

## Solution

Sử dụng venv Python với đường dẫn tuyệt đối:
- **Venv Python**: `/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/venv/bin/python`
- **MCP Server**: `/Users/nmhuyen/Documents/Manual Deploy/agent-data-test/mcp_server/stdio_server.py`

## Verification Results

### Task 1: Path Verification

```
✓ Venv Python: /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/venv/bin/python
✓ MCP Server: /Users/nmhuyen/Documents/Manual Deploy/agent-data-test/mcp_server/stdio_server.py
```

### Task 2: MCP Server Test

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

### Task 3: Claude Desktop Config

```json
{
  "mcpServers": {
    "agent-data": {
      "command": "/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/venv/bin/python",
      "args": [
        "/Users/nmhuyen/Documents/Manual Deploy/agent-data-test/mcp_server/stdio_server.py"
      ],
      "env": {
        "AGENT_DATA_URL": "http://localhost:8000",
        "PYTHONPATH": "/Users/nmhuyen/Documents/Manual Deploy/agent-data-test"
      }
    }
  },
  "preferences": {
    "quickEntryDictationShortcut": "capslock",
    "sidebarMode": "chat"
  }
}
```

JSON validation: **PASS**

### Task 4: Claude Desktop Restart

```
Claude Desktop is running
PIDs: 13068, 14214, 14215
```

### Task 5: Agent Data Health

```json
{"status":"healthy","version":"0.1.0","langroid_available":true}
```

## Success Criteria Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | Path venv/bin/python tồn tại | ✅ PASS |
| 2 | Path stdio_server.py tồn tại | ✅ PASS |
| 3 | `--test` chạy thành công | ✅ PASS |
| 4 | JSON config hợp lệ | ✅ PASS |
| 5 | Claude Desktop restart | ✅ PASS |
| 6 | Agent Data health OK | ✅ PASS |

## Files Modified

| File | Action |
|------|--------|
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Updated |
| `~/Library/Application Support/Claude/claude_desktop_config.json.backup` | Created |
| `reports/WEB-59c-MCP-VENV-FIX.md` | Created |

## Key Changes

1. **Changed venv**: `agent-data-test/venv` → `agent-data-langroid/venv`
2. **Added absolute path to script**: Instead of `-m mcp_server.stdio_server`
3. **Added PYTHONPATH**: Ensures proper module resolution

## Notes

- Both venvs have MCP package installed
- agent-data-langroid's venv can run agent-data-test's stdio_server.py
- Configuration uses absolute paths to avoid working directory issues
