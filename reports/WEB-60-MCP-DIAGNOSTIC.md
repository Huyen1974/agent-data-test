# WEB-60: MCP Connection Diagnostic Tool

**Date**: 2026-02-05
**Status**: COMPLETE

## Executive Summary

Created `dot-mcp-diagnose` tool for automatic MCP connection diagnostics and fixed configuration inconsistency.

## Problem Identified

WEB-59c had inconsistent paths:
- Python: `agent-data-langroid/venv`
- Script: `agent-data-test/mcp_server`

This could cause module import issues.

## Solution

Fixed config to use consistent paths from `agent-data-test`:
- Python: `/Users/nmhuyen/Documents/Manual Deploy/agent-data-test/venv/bin/python`
- Script: `/Users/nmhuyen/Documents/Manual Deploy/agent-data-test/mcp_server/stdio_server.py`

## Diagnostic Output (BEFORE Fix)

```
═══════════════════════════════════════════════════
MCP CONNECTION DIAGNOSTIC
═══════════════════════════════════════════════════

1. Config File:
───────────────
{
    "mcpServers": {
        "agent-data": {
            "command": "/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/venv/bin/python",
            "args": [
                "/Users/nmhuyen/Documents/Manual Deploy/agent-data-test/mcp_server/stdio_server.py"
            ],
            ...
        }
    }
}

4. Path Consistency Check:
──────────────────────────
⚠️  Mixed paths:
   Python: agent-data-langroid
   Script: agent-data-test
```

## Changes Made

1. Updated `claude_desktop_config.json`:
   - Changed Python path from `agent-data-langroid` to `agent-data-test`
   - All paths now consistent within `agent-data-test`

2. Created `dot-mcp-diagnose` tool with 8 checks:
   - Config file validity
   - Python path exists
   - Script path exists
   - Path consistency
   - MCP server test execution
   - Agent Data health
   - Claude Desktop status
   - Recent MCP errors

3. Fixed script bugs:
   - Proper quoting for paths with spaces
   - Correct path consistency logic

## Diagnostic Output (AFTER Fix)

```
═══════════════════════════════════════════════════
MCP CONNECTION DIAGNOSTIC
═══════════════════════════════════════════════════

1. Config File:
───────────────
{
    "mcpServers": {
        "agent-data": {
            "command": "/Users/nmhuyen/Documents/Manual Deploy/agent-data-test/venv/bin/python",
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

2. Python Path Check:
─────────────────────
✅ Python exists: /Users/nmhuyen/Documents/Manual Deploy/agent-data-test/venv/bin/python
Python 3.11.6

3. Script Path Check:
─────────────────────
✅ Script exists: /Users/nmhuyen/Documents/Manual Deploy/agent-data-test/mcp_server/stdio_server.py

4. Path Consistency Check:
──────────────────────────
✅ Consistent: Both in /Users/nmhuyen/Documents/Manual Deploy/agent-data-test

5. Test Script Execution:
─────────────────────────
✅ MCP Server Test PASSED
Tools available: 3

6. Agent Data Health:
─────────────────────
✅ Agent Data: {"status":"healthy","version":"0.1.0","langroid_available":true}

7. Claude Desktop Status:
─────────────────────────
✅ Claude Desktop running (PID: 14951)

8. Recent MCP Errors (last 2 min):
──────────────────────────────────
✅ No MCP errors found

═══════════════════════════════════════════════════
SUMMARY:
═══════════════════════════════════════════════════
✅ ALL CHECKS PASSED
═══════════════════════════════════════════════════
```

## Success Criteria Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | dot-mcp-diagnose created & executable | ✅ PASS |
| 2 | All diagnostic checks ✅ (no ❌) | ✅ PASS |
| 3 | Config JSON valid with consistent paths | ✅ PASS |
| 4 | --test PASS with "Test completed successfully" | ✅ PASS |
| 5 | Agent Data health: {"status":"healthy"} | ✅ PASS |
| 6 | Claude Desktop running | ✅ PASS |

## Files Created/Modified

| File | Action |
|------|--------|
| `agent-data-langroid/dot/bin/dot-mcp-diagnose` | Created |
| `~/Library/.../claude_desktop_config.json` | Updated |
| `reports/WEB-60-MCP-DIAGNOSTIC.md` | Created |

## Usage

```bash
# Run diagnostic
dot-mcp-diagnose

# Or with full path
/Users/nmhuyen/Documents/Manual\ Deploy/agent-data-langroid/dot/bin/dot-mcp-diagnose
```

## Final Status

**ALL GREEN** - No remaining issues.
