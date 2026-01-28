# WEB-19G: VecDB Initialization Fix

**Date:** 2026-01-28T08:48:24Z  
**Agent:** Codex

## 1. PROBLEM STATEMENT
- server.py hardcoded `agent_config.vecdb = None`, ignoring env vars
- Result: /chat always returned `qdrant_hits=0` because VecDB never initialized

## 2. CODE CHANGES
### Before (line ~244)
```python
agent_config.vecdb = None  # hardcoded
```

### After
```python
agent_config = AgentDataConfig()
agent_config.vecdb = _init_vecdb_config()
try:
    agent = AgentData(agent_config)
except Exception as exc:
    if _is_vecdb_init_error(exc) and agent_config.vecdb is not None:
        logger.warning(
            "VecDB init failed; retrying without vecdb to avoid startup crash: %s",
            exc,
        )
        agent_config.vecdb = None
        agent = AgentData(agent_config)
    else:
        raise
```

## 3. CI STATUS
| Workflow | Status | Run ID |
|----------|--------|--------|
| Guard Bootstrap Scaffold | ✅ | 21431024172 |
| Semantic Release | ✅ | 21431024191 |
| Pass Gate | ✅ | 21431024413 |
| Agent E2E | ⚠️ SKIPPED | 21430975952 |

## 4. DEPLOYMENT
- Revision: agent-data-test-00019-565
- Status: READY
- SA: chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com
- URL: https://agent-data-test-pfne2mqwja-as.a.run.app

## 5. FUNCTIONAL VERIFICATION
| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| /health | 200 | 200 (healthy) | ✅ |
| /info | 200 | 200 (langroid_version: 0.58.0) | ✅ |
| VecDB logs | No "VecDB not set" | "VecDB init failed... 403" | ⚠️ |
| /ingest | 202 | 202 Accepted | ✅ |
| /chat qdrant_hits | > 0 | 0 | ❌ |

Evidence (logs):
```
2026-01-28 08:40:52 - WARNING - VecDB init failed; retrying without vecdb to avoid startup crash: Unexpected Response: 403 (Forbidden)
```

## 6. VERDICT
- [ ] ✅ KNOWLEDGE HUB FULLY OPERATIONAL
- [x] ⚠️ PARTIAL
- [ ] ❌ BLOCKED

### Notes
- Qdrant returns 403 on VecDB init; Qdrant credentials/allowlist or API access still blocking vector store.
- /ingest accepts requests, but /chat still returns `qdrant_hits=0`.
