#!/bin/bash
# M5.1-CLI-03 — Audit monitoring workflows (artifact-audit.yml, secrets-audit.yml)
# Context: Verify presence & correctness of monitoring workflows required by plan P-174 on branch main
# Repo: github.com/Huyen1974/agent-data-test
# Safety: Read-only. No pushes, no workflow dispatches. Qdrant remains suspended.

set -euo pipefail

CLI_ID="M5.1-CLI-03"
ROOT="${ROOT:-/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid}"
REPO="${REPO:-Huyen1974/agent-data-test}"
cd "$ROOT"; mkdir -p .ci

log(){ printf "[%s] %s\n" "$CLI_ID" "$*"; }

# —————————————————————————————————————————————————————————————————————————————
# Step A) GitHub CLI Auth Verification (already authenticated per rules)
# —————————————————————————————————————————————————————————————————————————————

log "Verifying GitHub CLI authentication..."

if ! gh auth status -h github.com >/dev/null 2>&1; then
    log "FAIL: gh not authenticated - bootstrap required"
    exit 1
fi

SCOPES_LINE="$(gh api -i /user 2>/dev/null | grep -i '^X-Oauth-Scopes:' | cut -d' ' -f2- | tr -d '\r')"
REQ_SCOPES=("repo" "workflow")
MISSING=""
for s in "${REQ_SCOPES[@]}"; do
    if printf '%s' "$SCOPES_LINE" | grep -qw "$s"; then :; else MISSING="${MISSING:+$MISSING,}$s"; fi
done
if [ -n "$MISSING" ]; then
    log "FAIL: missing required scopes: $MISSING"
    exit 1
fi
log "GH scopes OK: $SCOPES_LINE"

# —————————————————————————————————————————————————————————————————————————————
# Step B) Fetch workflow contents on main
# —————————————————————————————————————————————————————————————————————————————

TMPD="$(mktemp -d)"
RESULT_JSON="$TMPD/result.jsonl"

> "$RESULT_JSON"

# Check each workflow
for WF_DATA in "artifact-audit.yml:0 2 * * *" "secrets-audit.yml:0 3 * * *"; do
    WF="$(echo "$WF_DATA" | cut -d: -f1)"
    REQ_CRON="$(echo "$WF_DATA" | cut -d: -f2-)"

    PATH_ON_REPO=".github/workflows/$WF"
    EXISTS=0 CONTENT="" FILEPATH=""

    if gh api "repos/$REPO/contents/$PATH_ON_REPO?ref=main" >/dev/null 2>&1; then
        RAW="$TMPD/${WF}.json"
        gh api "repos/$REPO/contents/$PATH_ON_REPO?ref=main" > "$RAW"
        FILEPATH="$TMPD/${WF}.yml"
        jq -r ".content" "$RAW" | base64 --decode > "$FILEPATH"
        CONTENT="$(cat "$FILEPATH")"
        EXISTS=1
        log "Found $PATH_ON_REPO"
    else
        log "Missing $PATH_ON_REPO"
    fi
    HAS_CRON=0
    HAS_TZ=0
    HAS_SLACK=0

    if [ $EXISTS -eq 1 ]; then
        # Cron detection
        if printf '%s\n' "$CONTENT" | grep -Eiq "cron:.*'$REQ_CRON'"; then HAS_CRON=1; fi
        # Timezone detection: either a field or a comment containing timeZone: 'UTC'
        if printf '%s\n' "$CONTENT" | grep -Eiq "timeZone:\s*'UTC'"; then HAS_TZ=1;
        elif printf '%s\n' "$CONTENT" | grep -Eiq "#.*timeZone:\s*'UTC'"; then HAS_TZ=1; fi
        # Slack heuristic
        if printf '%s\n' "$CONTENT" | grep -Eiq "slack|SLACK_WEBHOOK|chat\.postMessage|hooks\.slack"; then HAS_SLACK=1; fi
    fi

    jq -n \
        --arg name "$WF" \
        --arg path "$PATH_ON_REPO" \
        --arg req_cron "$REQ_CRON" \
        --argjson exists "$EXISTS" \
        --argjson has_cron "$HAS_CRON" \
        --argjson has_tz "$HAS_TZ" \
        --argjson has_slack "$HAS_SLACK" \
        '{workflow:$name,path:$path,required_cron:$req_cron,exists:($exists==1),has_cron:($has_cron==1),has_timezone_hint:($has_tz==1),has_slack_step:($has_slack==1)}' \
        >> "$RESULT_JSON"
done

# —————————————————————————————————————————————————————————————————————————————
# Step C) Aggregate
# —————————————————————————————————————————————————————————————————————————————

ART_ROW="$(jq -s '.[] | select(.workflow=="artifact-audit.yml")' "$RESULT_JSON")"
SEC_ROW="$(jq -s '.[] | select(.workflow=="secrets-audit.yml")' "$RESULT_JSON")"

PASS_ART="$(printf '%s' "$ART_ROW" | jq -r '(.exists and .has_cron and .has_timezone_hint and .has_slack_step)')"
PASS_SEC="$(printf '%s' "$SEC_ROW" | jq -r '(.exists and .has_cron and .has_timezone_hint and .has_slack_step)')"

jq -n \
    --arg cli_id "$CLI_ID" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg repo "$REPO" \
    --arg scopes "$SCOPES_LINE" \
    --argjson artifacts "${ART_ROW:-null}" \
    --argjson secrets   "${SEC_ROW:-null}" \
    --argjson pass_art "$PASS_ART" \
    --argjson pass_sec "$PASS_SEC" \
    '{
        cli_id:$cli_id,timestamp_utc:$ts,repo:$repo,github:{token_scopes:$scopes},
        artifact_audit:$artifacts,secrets_audit:$secrets,
        summary:{artifact_pass:$pass_art,secrets_pass:$pass_sec,all_pass:($pass_art and $pass_sec)}
    }' > .ci/M5.1_cli03_monitor_audit.json

log "Artifact audit PASS: $PASS_ART"
log "Secrets  audit PASS: $PASS_SEC"

# —————————————————————————————————————————————————————————————————————————————
# Step D) Gate & Self-check
# —————————————————————————————————————————————————————————————————————————————

FAIL=0
jq -e '.summary.all_pass==true' .ci/M5.1_cli03_monitor_audit.json >/dev/null || FAIL=1

if [ $FAIL -ne 0 ]; then
    log "FAIL — see .ci/M5.1_cli03_monitor_audit.json for details."

    # Print quick diffs to guide next step (apply)
    log "Hint: Next use M5.1-CLI-04 to create/fix missing workflows and set schedules/Slack."
    exit 1
fi

log "PASS — Monitoring workflows present & correctly configured."

# Cleanup temp directory
rm -rf "$TMPD"
