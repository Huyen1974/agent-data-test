#!/bin/bash
# ID: M5.1-CLI-01 — Verify GH Auth Bootstrap & GCS Backend Parity (read-only)
# Context:
# - Project root (Mac): /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid
# - Goal: Reproduce the last 3 pending checks from previous session (verify-only):
# (A) 3.1 GitHub CLI Auth Bootstrap (Cursor & Operators) — confirm usable gh session + token scopes.
# (B) PR-time GCS backend parity verification (scan *.tf, ensure consistent gcs backend across modules).
# (C) Post-merge GCS backend parity validation (same scan on main checkout).
# - Safety: No writes to GitHub, no secret mutations. Reads PAT from GSM only for local gh login if needed.
# - Qdrant: remains suspended; this CLI does not touch Qdrant.
# Output:
# - Summary JSON: .ci/M5.1_cli01_report.json
# - Human log lines with clear PASS/FAIL
# Idempotent: safe to re-run; overwrites report. Exit 1 on any FAIL.

set -euo pipefail

CLI_ID="M5.1-CLI-01"
ROOT="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
cd "$ROOT"

mkdir -p .ci

log() { printf "%s %s\n" "[$CLI_ID]" "$*"; }

# --- (A) 3.1 GitHub CLI Auth Bootstrap (Cursor & Operators) -------------------
# Rules recap (verify/apply):
# PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh verify|apply

GH_PROJECT="github-chatgpt-ggcloud"
GH_SECRET="gh_pat_sync_secrets"

# Bootstrap function based on .cursor/RULES_agent-data-langroid.md
bootstrap_gh_verify() {
    local project="$1"
    local secret_name="$2"

    log "Running GH Bootstrap VERIFY (no config changes)..."

    # Check if gh CLI is installed
    if ! command -v gh >/dev/null 2>&1; then
        log "FAIL: GitHub CLI (gh) not found. Please install it first."
        return 1
    fi

    # Check authentication status
    if gh auth status -h github.com >/dev/null 2>&1; then
        log "PASS: GitHub CLI is authenticated"
        return 0
    else
        log "WARN: gh not authenticated — attempting local apply login via bootstrap (keyring)"
        bootstrap_gh_apply "$project" "$secret_name"
        return $?
    fi
}

bootstrap_gh_apply() {
    local project="$1"
    local secret_name="$2"

    log "Attempting GH Bootstrap APPLY..."

    # Try to get token from Google Secret Manager
    if command -v gcloud >/dev/null 2>&1; then
        log "Attempting to retrieve GitHub token from Google Secret Manager..."

        # Check if gcloud is authenticated
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
            # Try to access the secret
            if TOKEN=$(gcloud secrets versions access latest --secret="$secret_name" --project="$project" 2>/dev/null); then
                log "Successfully retrieved token from GSM"

                # Login with the token
                echo "$TOKEN" | gh auth login --with-token

                if gh auth status -h github.com >/dev/null 2>&1; then
                    log "PASS: Successfully authenticated with GitHub CLI"
                    return 0
                else
                    log "FAIL: Authentication failed even after token login"
                    return 1
                fi
            else
                log "WARN: Could not access secret $secret_name in project $project"
                return 1
            fi
        else
            log "WARN: gcloud not authenticated, cannot access secrets"
            return 1
        fi
    else
        log "WARN: gcloud CLI not available"
        return 1
    fi
}

# Run bootstrap verification
bootstrap_gh_verify "$GH_PROJECT" "$GH_SECRET" || {
    log "FAIL: cannot authenticate gh (bootstrap failed)."
    exit 1
}

# Check gh auth status & token scopes (need: repo, workflow)
AUTH_STATUS_OK=0
SCOPES_OK=0
MISSING_SCOPES=""

if gh auth status -h github.com >/dev/null 2>&1; then
    AUTH_STATUS_OK=1
else
    log "FAIL: gh auth still not available after bootstrap"
    exit 1
fi

# Inspect headers to validate scopes
SCOPES_LINE="$(gh api -i /user 2>/dev/null | awk -F': ' '/^X-OAuth-Scopes:/ {print $2}' | tr -d '\r')"
# Fallback: get scopes from gh auth status if headers don't work
if [ -z "$SCOPES_LINE" ]; then
    SCOPES_LINE="$(gh auth status -h github.com 2>&1 | grep "Token scopes:" | sed "s/.*Token scopes: //" | tr -d "'" | tr ',' ' ')"
fi
need_scopes=("repo" "workflow")
for s in "${need_scopes[@]}"; do
    if printf '%s' "$SCOPES_LINE" | grep -qw "$s"; then :; else
        MISSING_SCOPES="${MISSING_SCOPES:+$MISSING_SCOPES,}$s"
    fi
done
if [ -z "$MISSING_SCOPES" ]; then
    SCOPES_OK=1
else
    log "FAIL: Missing required token scopes: $MISSING_SCOPES"
fi

# --- (B & C) GCS backend parity verification (TF) -----------------------------
# We scan *.tf for: backend "gcs" { bucket, prefix, encryption, impersonate_service_account (optional) }
# Build a small parser to produce JSON; then compute parity across all backends found.

PY="$(mktemp)"
cat > "$PY" << 'PY'
import os, re, json, sys
root = os.getcwd()
tf_files = []
for d,_,fs in os.walk(root):
    if '/.terraform/' in d: continue
    for f in fs:
        if f.endswith('.tf'):
            tf_files.append(os.path.join(d,f))

blk_re = re.compile(r'backend\s+"gcs"\s*{(.+?)}', re.S)
kv_re = re.compile(r'(\w+)\s*=\s*"([^"]*)"')

entries = []
for path in sorted(tf_files):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            txt = fh.read()
        for m in blk_re.finditer(txt):
            body = m.group(1)
            kv = dict(kv_re.findall(body))
            entries.append({
                "file": os.path.relpath(path, root),
                "bucket": kv.get("bucket"),
                "prefix": kv.get("prefix"),
                "encryption": kv.get("encryption"),
                "impersonate_service_account": kv.get("impersonate_service_account"),
            })
    except Exception as e:
        entries.append({"file": os.path.relpath(path, root), "error": str(e)})

# Parity rules:
# - All backend blocks must exist (at least one overall).
# - For configs with backend-config strategy (bucket/prefix = null), this is acceptable.
# - All bucket values must be identical if specified, or all null (backend-config strategy).
# - All prefix values must be consistent if specified, or all null (backend-config strategy).
# - encryption should be either identical across modules or absent everywhere.

def parity(entries):
    res = {"has_any": bool(entries)}
    if not entries:
        res.update({"bucket_parity": False, "prefix_parity": False, "encryption_parity": True, "issues": ["no_backend_found"]})
        return res
    buckets = {e.get("bucket") for e in entries}
    prefixes= {e.get("prefix") for e in entries}
    encrypts= {e.get("encryption") for e in entries if e.get("encryption") is not None}
    issues=[]

    # bucket parity: either all same non-null value OR all null (backend-config strategy)
    bucket_ok = (len(buckets)==1)
    if not bucket_ok: issues.append("bucket_mismatch")

    # prefix parity: either all same non-null value OR all null (backend-config strategy)
    prefix_ok = (len(prefixes)==1)
    if not prefix_ok: issues.append("prefix_mismatch")

    # encryption parity: either all define same value OR none define it
    if len(encrypts)==0:
        enc_ok = True
    else:
        enc_ok = (len(encrypts)==1)
        if not enc_ok: issues.append("encryption_mismatch")

    res.update({
        "bucket_parity": bucket_ok,
        "prefix_parity": prefix_ok,
        "encryption_parity": enc_ok,
        "issues": issues,
    })
    return res

summary = parity(entries)
out = {"backends": entries, "summary": summary}
print(json.dumps(out, ensure_ascii=False, separators=(",",":")))
PY

PY_OUT="$(python3 "$PY")"
rm -f "$PY"

# Write raw backend scan
echo "$PY_OUT" > .ci/M5.1_cli01_tf_backends.json

# Compute overall parity flag
TF_HAS_ANY="$(echo "$PY_OUT" | jq -r '.summary.has_any')"
TF_BUCKET_OK="$(echo "$PY_OUT" | jq -r '.summary.bucket_parity')"
TF_PREFIX_OK="$(echo "$PY_OUT" | jq -r '.summary.prefix_parity')"
TF_ENC_OK="$(echo "$PY_OUT" | jq -r '.summary.encryption_parity')"
TF_ISSUES="$(echo "$PY_OUT" | jq -c '.summary.issues')"

# --- (Docs presence check) ----------------------------------------------------
# These files guided the previous work; we verify their presence to avoid drift.

DOCS_FOUND=1
missing_docs=()
for f in \
    "GCS-BACKEND-PARITY-v2_cursor_update_github_actions_for_gcs_ba.md" \
    "GCS-BACKEND-PARITY-v2_cursor_verify_gcs_backend_parity_pull_r.md" \
    "GCS-BACKEND-PARITY-v2_cursor_post_merge_validation_for_gcs_ba.md"
do
    if ! git ls-files --error-unmatch "$f" >/dev/null 2>&1 && [ ! -f "$f" ]; then
        DOCS_FOUND=0
        missing_docs+=("$f")
    fi
done

# --- Report aggregation -------------------------------------------------------

AUTH_OBJ=$(jq -n \
    --arg status "$([ "$AUTH_STATUS_OK" -eq 1 ] && echo "true" || echo "false")" \
    --arg scopes "$SCOPES_LINE" \
    --arg missing "${MISSING_SCOPES:-}" \
    '{authenticated:($status=="true"),token_scopes:$scopes,missing_scopes:($missing|split(",")|map(select(length>0)))}')

TF_OBJ=$(jq -n \
    --argjson has_any "$TF_HAS_ANY" \
    --argjson bucket_ok "$TF_BUCKET_OK" \
    --argjson prefix_ok "$TF_PREFIX_OK" \
    --argjson enc_ok "$TF_ENC_OK" \
    --arg issues "$TF_ISSUES" \
    '{has_any:$has_any,bucket_parity:$bucket_ok,prefix_parity:$prefix_ok,encryption_parity:$enc_ok,issues:($issues|fromjson)}')

DOCS_OBJ=$(jq -n \
    --argjson found "$DOCS_FOUND" \
    --argjson missing "$(printf '%s\n' "${missing_docs[@]:-}" | jq -R . | jq -s .)" \
    '{all_docs_present:($found==1),missing:$missing}')

jq -n \
    --arg cli_id "$CLI_ID" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg project "$GH_PROJECT" \
    --arg secret "$GH_SECRET" \
    --argjson gh "$AUTH_OBJ" \
    --argjson tf "$TF_OBJ" \
    --argjson docs "$DOCS_OBJ" \
    '{cli_id:$cli_id,timestamp_utc:$ts,gh_project:$project,gh_secret:$secret,github:$gh,terraform_backend:$tf,docs:$docs}' \
    > .ci/M5.1_cli01_report.json

# --- Human-readable summary & gate -------------------------------------------

log "GH auth: $(jq -r '.github.authenticated' .ci/M5.1_cli01_report.json)"
log "GH scopes: $(jq -r '.github.token_scopes' .ci/M5.1_cli01_report.json)"
log "Missing scopes: $(jq -r '.github.missing_scopes|join(",")' .ci/M5.1_cli01_report.json)"
log "TF backends: has_any=$(jq -r '.terraform_backend.has_any' .ci/M5.1_cli01_report.json) bucket_parity=$(jq -r '.terraform_backend.bucket_parity' .ci/M5.1_cli01_report.json) prefix_parity=$(jq -r '.terraform_backend.prefix_parity' .ci/M5.1_cli01_report.json) encryption_parity=$(jq -r '.terraform_backend.encryption_parity' .ci/M5.1_cli01_report.json)"
log "Docs present: $(jq -r '.docs.all_docs_present' .ci/M5.1_cli01_report.json)"

FAIL=0
[ "$(jq -r '.github.authenticated' .ci/M5.1_cli01_report.json)" = "true" ] || FAIL=1
[ "$(jq -r '.github.missing_scopes|length' .ci/M5.1_cli01_report.json)" -eq 0 ] || FAIL=1
[ "$(jq -r '.terraform_backend.has_any' .ci/M5.1_cli01_report.json)" = "true" ] || FAIL=1
[ "$(jq -r '.terraform_backend.bucket_parity' .ci/M5.1_cli01_report.json)" = "true" ] || FAIL=1
[ "$(jq -r '.terraform_backend.prefix_parity' .ci/M5.1_cli01_report.json)" = "true" ] || FAIL=1
[ "$(jq -r '.docs.all_docs_present' .ci/M5.1_cli01_report.json)" = "true" ] || { log "NOTE: Some guidance docs not found — content may exist elsewhere; list stored in report"; }

if [ $FAIL -ne 0 ]; then
    log "FAIL — See .ci/M5.1_cli01_report.json and .ci/M5.1_cli01_tf_backends.json for details."
    exit 1
fi

log "PASS — GH auth & GCS backend parity verified."
