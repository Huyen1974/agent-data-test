# Living Status: DOT Tools Registry

> Registry of all DOT (Developer Operations Tools) scripts available.

**Last Updated**: 2026-02-06

## Location
All DOT tools are in: `~/Documents/Manual Deploy/agent-data-test/dot/bin/`

## Available Tools

### dot-ai-start
| Property | Value |
|----------|-------|
| Purpose | Start entire AI infrastructure locally |
| Usage | `dot/bin/dot-ai-start [--skip-tests]` |
| What it does | 1. Starts Agent Data on port 8000, 2. Starts MCP Server on port 8001, 3. Runs verification tests, 4. Shows endpoints and DOT commands |
| Flags | `--skip-tests` — Skip post-start verification |
| Dependencies | Python venv at `venv/bin/python` |
| Logs | `logs/agent_data.log`, `logs/mcp_server.log` |

### dot-ai-stop
| Property | Value |
|----------|-------|
| Purpose | Stop all local AI services |
| Usage | `dot/bin/dot-ai-stop` |
| What it does | Finds processes on ports 8000 and 8001 via `lsof`, kills them with `kill -9` |
| Dependencies | None |

### dot-ai-test-all
| Property | Value |
|----------|-------|
| Purpose | Run comprehensive AI connection tests |
| Usage | `dot/bin/dot-ai-test-all` |
| What it does | Executes `tests/test_ai_connections.py` which runs 9 tests |
| Tests included | Local health, search, MCP HTTP/STDIO, Claude Desktop config, Cloud endpoint, OpenAPI spec |
| Exit code | 0 = all pass, non-zero = failures |

## Quick Reference
```bash
# Start everything
dot/bin/dot-ai-start

# Run tests only
dot/bin/dot-ai-test-all

# Stop everything
dot/bin/dot-ai-stop

# Quick restart
dot/bin/dot-ai-stop && dot/bin/dot-ai-start
```

## Adding New Tools
To add a new DOT tool:
1. Create script in `dot/bin/` with `dot-` prefix
2. Make executable: `chmod +x dot/bin/dot-new-tool`
3. Add entry to this registry document
4. Update Agent Data: `update_document("docs/status/dot-tools-registry.md", ...)`
