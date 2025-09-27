#!/bin/bash
# Verify that ADC can read required secrets via google-cloud-secret-manager.
set -euo pipefail

PROJECT_ID_ENV=${PROJECT_ID:-}
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-${GCP_PROJECT:-${PROJECT_ID_ENV:-github-chatgpt-ggcloud}}}
export PROJECT_ID="$PROJECT_ID"

printf 'Verifying Secret Manager access with project=%s\n' "$PROJECT_ID"

python3 - <<'PY'
import os
import sys

from gcp_secrets import SecretAccessError, clear_secret_cache, get_secret

secrets = [
    ("OPENAI_API", os.getenv("OPENAI_API_SECRET_NAME", "openai-api-key-sg")),
    ("QDRANT_API", os.getenv("QDRANT_API_SECRET_NAME", "Qdrant_agent_data_N1D8R2vC0_5")),
    ("QDRANT_MGMT", os.getenv("QDRANT_MGMT_KEY_SECRET_NAME", "Qdrant_cloud_management_key")),
]

exit_code = 0
for label, secret_name in secrets:
    try:
        value = get_secret(secret_name)
    except SecretAccessError as exc:
        print(f"[FAIL] {label} -> {secret_name}: {exc}")
        exit_code = 1
    else:
        redacted_len = len(value)
        print(f"[PASS] {label} -> {secret_name} (length={redacted_len})")
    finally:
        clear_secret_cache()

sys.exit(exit_code)
PY
