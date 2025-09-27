# ADC Migration Plan

## Secret Inventory
- **OPENAI_API_KEY** → Secret Manager `openai-api-key-sg`
- **QDRANT_API_KEY** → Secret Manager `Qdrant_agent_data_N1D8R2vC0_5`
- **QDRANT_MGMT_KEY** → Secret Manager `Qdrant_cloud_management_key`

## Target Files & Changes
- `agent_data/vector_store.py`
  - Use `gcp_secrets.get_secret` to fetch OpenAI and Qdrant API keys.
  - Keep optional environment overrides for local/dev workflows.
- `functions/manage_qdrant/main.py`
  - Load Qdrant management key via Secret Manager with cached fallback.
  - Fail fast when ADC access is unavailable.
- `scripts/check_orphan_vectors.py`
  - Retrieve Qdrant API key via ADC helper for CI diagnostics.
- `scripts/orphan_vector_check.py`
  - Resolve Qdrant API key via ADC helper.
- `verify_adc.sh`
  - New script to confirm ADC secret retrieval end-to-end.

## ADC-Compatible Code Snippets
```python
from gcp_secrets import get_secret, SecretAccessError

try:
    openai_key = get_secret("openai-api-key-sg")
except SecretAccessError as exc:
    raise RuntimeError(f"OpenAI key unavailable: {exc}")
```

```python
mgmt_key = get_secret(
    os.getenv("QDRANT_MGMT_KEY_SECRET_NAME", "Qdrant_cloud_management_key")
)
```

## Required IAM Roles
- `roles/secretmanager.secretAccessor` on project `github-chatgpt-ggcloud` for runtime principals (Cloud Functions, CI, developer ADC).
- `roles/secretmanager.viewer` for read-only diagnostics accounts (optional).

## Verification Checklist
- [x] Run `./verify_adc.sh` and confirm all secrets report `PASS` (latest run passed).
- [ ] Execute `pytest` to ensure unit tests pass with ADC-based loaders mocked. *(Blocked: host Python 3.13 ships x86_64-only `pydantic_core`; reinstall arm64 wheel before rerun.)*
- [ ] Validate Cursor/dev shells pick up secrets via cached helper (no gcloud on login).
- [ ] Document rollback: restore `agent_data/vector_store.py`, `functions/manage_qdrant/main.py`, ADC helper modules from backup if needed.

## Rollback Plan
1. Restore backups from `zsh_backup_20250926_113657/after_A3_start/` or git history.
2. Remove `gcp_secrets.py` and references if reverting to ENV-only mode.
3. Delete `verify_adc.sh` and update documentation accordingly.
