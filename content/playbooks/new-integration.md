# Playbook: New Integration

> Use this playbook when connecting a new external service or API.

## Before Starting

### Load Context Packs
- [ ] `governance` — No-code-new and SA rules
- [ ] `infrastructure` — Existing services inventory
- [ ] `directus` — Check if Directus handles this already

### Pre-flight Questions
- [ ] Does Directus already provide this capability? (Check Flows, Extensions)
- [ ] Does Agent Data already expose this data? (Check MCP tools)
- [ ] Is there an Agency OS component for this?
- [ ] Do we ACTUALLY need a new integration, or can existing services handle it?

**If the answer to any above is YES → use existing, don't integrate new.**

## Integration Assessment

### Step 1: Evaluate Necessity
| Question | Answer |
|----------|--------|
| What does this integration provide? | |
| Can Directus Flows handle it? | YES/NO |
| Can Agent Data API handle it? | YES/NO |
| Is new code required? | YES/NO (should be NO) |
| What's the maintenance cost? | |

### Step 2: Choose Pattern
Priority order:
1. **Directus Flow** — Webhook/schedule triggers, API calls, no code
2. **Agent Data endpoint** — If it's a knowledge/document operation
3. **Cloud Function** — Only if async processing is required
4. **Custom code** — LAST RESORT, requires explicit approval

### Step 3: Authentication
- [ ] Can we use existing SA? (`chatgpt-deployer@...`)
- [ ] Store credentials in Secret Manager (NEVER in code/env files)
- [ ] Test auth locally before deploying

## Implementation

### For Directus Flow Integration
1. Open Directus Admin → Settings → Flows
2. Create trigger (webhook, schedule, or event)
3. Add operations (HTTP request, transform, condition)
4. Test flow execution
5. Document in `docs/status/connection-matrix.md`

### For Agent Data Integration
1. Check if existing MCP tool handles the use case
2. If not, add endpoint to `agent_data/server.py`
3. Add corresponding MCP tool to `mcp_server/stdio_server.py`
4. Deploy both local and cloud (hybrid!)
5. Test via both endpoints

### For Cloud Function (Rare)
1. Check if Cloud Scheduler + existing endpoint works instead
2. Write minimal function code
3. Deploy with existing SA
4. Add to system inventory

## Testing Checklist
- [ ] Works locally (http://localhost:...)
- [ ] Works on cloud (https://...a.run.app)
- [ ] Error handling for service downtime
- [ ] Hybrid fallback if applicable
- [ ] No secrets exposed in logs or responses

## After Integration

### Documentation Required
- [ ] Update `docs/status/system-inventory.md`
- [ ] Update `docs/status/connection-matrix.md`
- [ ] Update relevant context pack
- [ ] Write session report

### Monitoring
- [ ] Health check endpoint exists for the integration
- [ ] Error logging is in place
- [ ] Metrics/Prometheus counters if applicable

## Red Flags
- "I need to create a new Service Account" → STOP (GC-LAW 1.3)
- "I need to install a new framework" → Almost certainly wrong
- "I need to write a custom OAuth flow" → Use Directus auth
- "This needs a new database" → Use Firestore/Directus collections
- "I need to set up a new Docker container" → Check existing services
