# Antigravity Operational Rules

## Core Principles

### Self-Bootstrap Rule
**On first workspace run, if `artifacts/bootstrap_done.md` does not exist, execute `./scripts/bootstrap_antigravity.sh` before any other task.**

This ensures:
- GitHub PAT is automatically configured from GCP Secret Manager
- Existing bootstrap logic is executed
- Bootstrap completion is marked to prevent re-runs

### Bootstrap Process
1. Check for marker file: `artifacts/bootstrap_done.md`
2. If not present, run: `./scripts/bootstrap_antigravity.sh`
3. The script will:
   - Retrieve GitHub PAT from GCP Secret Manager (`gh_pat_sync_secrets`)
   - Configure Git credentials for HTTPS authentication
   - Execute existing bootstrap logic (if present)
   - Create completion marker

### Operational Guidelines
- Always verify bootstrap completion before starting development tasks
- PAT should be retrieved from GCP Secret Manager, never hardcoded
- Respect existing bootstrap markers to avoid redundant operations
- Log all bootstrap activities to `artifacts/logs/bootstrap_antigravity.log`

### Safety Measures
- Scripts are idempotent (safe to re-run)
- Existing credentials are backed up before modification
- Bootstrap only runs once per workspace initialization
- All operations are logged for auditability

### Integration Points
- GCP Secret Manager: `gh_pat_sync_secrets` in project `github-chatgpt-ggcloud`
- Git Configuration: Uses `~/.git-credentials` for HTTPS auth
- Existing Bootstrap: Calls `tools/bootstrap_gh.sh` and `CLI.POSTBOOT.250.sh` if present
- Marker File: `artifacts/bootstrap_done.md` indicates completion
