#!/bin/bash
# ID: M5.1-CLI-05 — Push feature branch, open PR (no bootstrap re-creation) & audit PR HEAD

set -euo pipefail

CLI_ID="M5.1-CLI-05"
ROOT="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
REPO_SLUG="Huyen1974/agent-data-test"
cd "$ROOT"; mkdir -p .ci

log(){ printf "[%s] %s\n" "$CLI_ID" "$*"; }

# —————————————————————————————————————————————————————————————————————————————
# Guard: bootstrap must exist & must NOT be recreated/modified
# —————————————————————————————————————————————————————————————————————————————

BOOTSTRAP="scripts/bootstrap_gh.sh"
[ -f "$BOOTSTRAP" ] || { log "FAIL: $BOOTSTRAP must already exist (do NOT create it)."; exit 1; }
chmod +x "$BOOTSTRAP" || true

# Freeze/verify checksum to prevent re-creation/modification across CLIs
CS_FILE=".ci/bootstrap_gh.sha256"
CURR_SHA="$(shasum -a 256 "$BOOTSTRAP" | awk '{print $1}')"
if [ -f "$CS_FILE" ]; then
    PREV_SHA="$(cat "$CS_FILE" | tr -d '\r\n' || true)"
    if [ -n "$PREV_SHA" ] && [ "$PREV_SHA" != "$CURR_SHA" ]; then
        log "FAIL: $BOOTSTRAP checksum changed (attempt to recreate/modify). Aborting."
        exit 1
    fi
else
    printf "%s\n" "$CURR_SHA" > "$CS_FILE"
fi

# —————————————————————————————————————————————————————————————————————————————
# Step A: 3.1 GitHub CLI Auth Bootstrap (verify/apply only; no creation)
# —————————————————————————————————————————————————————————————————————————————

GH_PROJECT="github-chatgpt-ggcloud"
GH_SECRET="gh_pat_sync_secrets"

log "GH bootstrap VERIFY (no changes)…"
PROJECT="$GH_PROJECT" SECRET_NAME="$GH_SECRET" "$BOOTSTRAP" verify || true

if ! gh auth status -h github.com >/dev/null 2>&1; then
    log "GH not authenticated — running APPLY (login keyring)…"
    PROJECT="$GH_PROJECT" SECRET_NAME="$GH_SECRET" "$BOOTSTRAP" apply
    gh auth status -h github.com >/dev/null 2>&1 || { log "FAIL: gh auth unavailable after apply"; exit 1; }
fi

SCOPES_LINE="$(gh api -i /user 2>/dev/null | awk -F': ' 'tolower($1)~/^x-oauth-scopes/ {print $2}' | tr -d '\r')"
for s in repo workflow; do
    echo "$SCOPES_LINE" | tr ',' '\n' | tr -d ' ' | grep -qi "^${s}$" || { log "FAIL: missing GH token scope: ${s}"; exit 1; }
done
log "GH scopes OK: $SCOPES_LINE"

# Ensure bootstrap file was NOT changed by anything above
AFTER_SHA="$(shasum -a 256 "$BOOTSTRAP" | awk '{print $1}')"
[ "$AFTER_SHA" = "$CURR_SHA" ] || { log "FAIL: $BOOTSTRAP changed during CLI. Aborting."; exit 1; }

# —————————————————————————————————————————————————————————————————————————————
# Step B: Determine default and feature branch
# —————————————————————————————————————————————————————————————————————————————

DEF_BRANCH="$(gh repo view "$REPO_SLUG" --json defaultBranchRef -q '.defaultBranchRef.name')"
CUR_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Pick current feature branch if matches pattern; otherwise, pick the most recent 'feat/m5-monitoring-workflows-*'
if printf '%s' "$CUR_BRANCH" | grep -Eq '^feat/m5-monitoring-workflows-'; then
    BRANCH="$CUR_BRANCH"
else
    BRANCH="$(git for-each-ref --sort=-committerdate --format='%(refname:short)' refs/heads | grep -E '^feat/m5-monitoring-workflows-' | head -n1 || true)"
    [ -n "$BRANCH" ] || { log "FAIL: feature branch not found. Run CLI-04 first."; exit 1; }
    git checkout "$BRANCH"
fi
log "Using feature branch: $BRANCH (base: $DEF_BRANCH)"

# —————————————————————————————————————————————————————————————————————————————
# Step C: Assert local workflows exist (do NOT (re)create here)
# —————————————————————————————————————————————————————————————————————————————

for wf in ".github/workflows/artifact-audit.yml" ".github/workflows/secrets-audit.yml"; do
    [ -f "$wf" ] || { log "FAIL: missing $wf locally. Do NOT auto-create here. Re-run CLI-04."; exit 1; }
done

# —————————————————————————————————————————————————————————————————————————————
# Step D: Push branch & open PR (create label if missing)
# —————————————————————————————————————————————————————————————————————————————

git fetch origin "$DEF_BRANCH" --quiet || true
git rebase "origin/$DEF_BRANCH" || true

# Push (idempotent)
git push -u origin "$BRANCH" || true

# Label ensure (idempotent)
if ! gh label list --limit 200 | awk '{print $1}' | grep -qx "merge-to-law"; then
    gh label create "merge-to-law" --color FFD700 --description "Merge-to-Law gate" >/dev/null 2>&1 || true
fi

# Create PR if not exists
PR_JSON="$(mktemp)"
if ! gh pr view --json number,url,headRefName,headRefOid,baseRefName -q . >/dev/null 2>&1; then
    gh pr create \
        --title "P-174: Add monitoring workflows (artifact-audit, secrets-audit)" \
        --body "Implements PLAN P-174: add monitoring workflows with explicit UTC schedules and Slack notify (guarded)." \
        --base "$DEF_BRANCH" --head "$BRANCH" >/dev/null 2>&1 || true
fi

# Fetch PR info (must exist now)
gh pr view --json number,url,headRefName,headRefOid,baseRefName > "$PR_JSON" || { log "FAIL: PR not found after creation."; exit 1; }
PR_URL="$(jq -r '.url' "$PR_JSON")"
PR_HEAD_REF="$(jq -r '.headRefName' "$PR_JSON")"
PR_HEAD_OID="$(jq -r '.headRefOid' "$PR_JSON")"
printf '{"cli_id":"%s","pr_url":"%s","head_ref":"%s","head_oid":"%s"}\n' "$CLI_ID" "$PR_URL" "$PR_HEAD_REF" "$PR_HEAD_OID" > .ci/M5.1_cli05_pr.json
log "PR: $PR_URL"
log "PR head: $PR_HEAD_REF ($PR_HEAD_OID)"

# —————————————————————————————————————————————————————————————————————————————
# Step E: Remote audit on PR HEAD (not on main)
# —————————————————————————————————————————————————————————————————————————————

TMPD="$(mktemp -d)"
RESULTS="$TMPD/audit.jsonl"; > "$RESULTS"

audit_one(){
    _wf="$1"; _cron="$2"
    _path=".github/workflows/${_wf}"
    _raw="$TMPD/${_wf}.json"
    if gh api "repos/${REPO_SLUG}/contents/${_path}?ref=${PR_HEAD_REF}" > "$_raw" 2>/dev/null; then
        _yml="$TMPD/${_wf}.yml"
        jq -r ".content" "$_raw" | base64 --decode > "$_yml"
        _content="$(cat "$_yml")"
        _exists=1
        _has_cron=0; _has_tz=0; _has_slack=0
        printf '%s' "$_content" | grep -Eiq "cron:\s*'${_cron}'" && _has_cron=1
        printf '%s' "$_content" | grep -Eiq "timeZone:\s*'UTC'|#\s*timeZone:\s*'UTC'|#.*UTC\s+daily" && _has_tz=1
        printf '%s' "$_content" | grep -Eiq "SLACK_WEBHOOK|slack|chat.postMessage|hooks.slack" && _has_slack=1
    else
        _exists=0; _has_cron=0; _has_tz=0; _has_slack=0
    fi
    jq -n --arg wf "$_wf" --argjson ex "$_exists" --argjson c "$_has_cron" --argjson tz "$_has_tz" --argjson sl "$_has_slack" \
        '{workflow:$wf,exists:($ex==1),has_cron:($c==1),has_timezone_hint:($tz==1),has_slack_step:($sl==1)}'
}

audit_one "artifact-audit.yml" "0 2 \* \* \*" >> "$RESULTS"
audit_one "secrets-audit.yml"  "0 3 \* \* \*" >> "$RESULTS"

ART_ROW="$(jq -s '.[0]' "$RESULTS")"
SEC_ROW="$(jq -s '.[1]' "$RESULTS")"
PASS_ART="$(printf '%s' "$ART_ROW" | jq -r '(.exists and .has_cron and .has_timezone_hint and .has_slack_step)')"
PASS_SEC="$(printf '%s' "$SEC_ROW" | jq -r '(.exists and .has_cron and .has_timezone_hint and .has_slack_step)')"

jq -n \
    --arg cli_id "$CLI_ID" \
    --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg repo "$REPO_SLUG" \
    --arg pr "$PR_URL" \
    --arg head "$PR_HEAD_REF" \
    --arg scopes "$SCOPES_LINE" \
    --argjson artifact "$ART_ROW" \
    --argjson secrets  "$SEC_ROW" \
    --argjson pass_art "$PASS_ART" \
    --argjson pass_sec "$PASS_SEC" \
    '{
        cli_id:$cli_id,timestamp_utc:$ts,repo:$repo,pr_url:$pr,head_ref:$head,github:{token_scopes:$scopes},
        artifact_audit:$artifact,secrets_audit:$secrets,
        summary:{artifact_pass:$pass_art,secrets_pass:$pass_sec,all_pass:($pass_art and $pass_sec)}
    }' > .ci/M5.1_cli05_pr_audit.json

log "PR-HEAD Artifact audit PASS: $PASS_ART"
log "PR-HEAD Secrets  audit PASS: $PASS_SEC"

# —————————————————————————————————————————————————————————————————————————————
# Gate & Self-check
# —————————————————————————————————————————————————————————————————————————————

FAIL=0
jq -e '.pr_url|length>0' .ci/M5.1_cli05_pr.json >/dev/null || FAIL=1
jq -e '.summary.all_pass==true' .ci/M5.1_cli05_pr_audit.json >/dev/null || FAIL=1

if [ $FAIL -ne 0 ]; then
    log "FAIL — See .ci/M5.1_cli05_pr.json and .ci/M5.1_cli05_pr_audit.json"
    log "Hint: ensure branch pushed and PR created; re-run after fixes."
    exit 1
fi

log "PASS — PR created and PR-HEAD audit succeeded. Next: wait for CI green, then run CLI-06 to merge and re-audit on main."
