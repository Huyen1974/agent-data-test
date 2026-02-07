# Playbook: Infrastructure Change

> Use this playbook for any GCP, deployment, or infrastructure modification.

## Before Starting

### Load Context Packs
- [ ] `governance` — SA rules and hybrid principle
- [ ] `infrastructure` — Service inventory and endpoints
- [ ] `current-sprint` — Current context

### Pre-flight Checks
- [ ] Confirm the change is in scope of the current ticket
- [ ] Verify: NOT creating new Service Accounts (GC-LAW 1.3)
- [ ] Verify: NOT removing cloud config when adding local (hybrid rule)
- [ ] Check current Cloud Run revision: `gcloud run revisions list --service=agent-data-test --region=asia-southeast1 --limit=3`
- [ ] Note current revision name for rollback reference

## Hybrid Config Changes

### Rules (NON-NEGOTIABLE)
1. Both local and cloud URLs must always be configured
2. Local is priority, cloud is fallback
3. Both API keys must be present
4. Changes to one endpoint must NOT break the other

### Config File: claude_desktop_config.json
Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

Required env vars:
- `AGENT_DATA_URL` — Local endpoint (http://localhost:8000)
- `AGENT_DATA_URL_CLOUD` — Cloud endpoint
- `AGENT_DATA_API_KEY_LOCAL` — Local API key
- `AGENT_DATA_API_KEY_CLOUD` — Cloud API key
- `AGENT_DATA_PREFER` — "local" (always)

## Cloud Run Deployment

### Pre-deploy
- [ ] Run local tests: `dot-ai-test-all`
- [ ] Verify Dockerfile builds locally: `docker build -t test .`
- [ ] Check for secrets/env vars needed in Cloud Run

### Deploy
```bash
gcloud run deploy agent-data-test \
  --source . \
  --region asia-southeast1 \
  --service-account chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com \
  --allow-unauthenticated=no \
  --memory 512Mi \
  --timeout 300
```

### Post-deploy Verification
- [ ] Health check: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://agent-data-test-pfne2mqwja-as.a.run.app/health`
- [ ] Info endpoint: same URL with `/info`
- [ ] CRUD test with slash paths (create, update, delete)
- [ ] Compare behavior with local endpoint

### Rollback (if needed)
```bash
# List revisions
gcloud run revisions list --service=agent-data-test --region=asia-southeast1 --limit=5

# Route 100% to previous revision
gcloud run services update-traffic agent-data-test \
  --region=asia-southeast1 \
  --to-revisions PREVIOUS_REVISION=100
```

## Secret Manager Changes
- [ ] NEVER log secret values
- [ ] Update via: `gcloud secrets versions add SECRET_NAME --data-file=- <<< "value"`
- [ ] Verify: `gcloud secrets versions access latest --secret=SECRET_NAME`
- [ ] Update Cloud Run env if secret reference changed

## After Change

### Documentation
- [ ] Write session report to `docs/operations/sessions/`
- [ ] Update `docs/status/system-inventory.md` if service changed
- [ ] Update `docs/status/connection-matrix.md` if endpoints changed
- [ ] Update relevant context packs if architecture changed

### Verification
- [ ] Local endpoint works: `curl http://localhost:8000/health`
- [ ] Cloud endpoint works: `curl -H "Auth..." https://.../health`
- [ ] MCP tools work (both read and write)
- [ ] Hybrid fallback works: stop local → verify cloud still responds

## Red Flags (STOP immediately)
- "I need to create a new Service Account" → STOP. GC-LAW 1.3 violation
- "I'll just remove the cloud config" → STOP. Hybrid rule violation
- "The deployment failed, let me force push" → STOP. Check logs first
- "I need to modify IAM permissions" → STOP. Confirm with user first
