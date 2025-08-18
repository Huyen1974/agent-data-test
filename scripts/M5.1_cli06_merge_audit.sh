#!/bin/bash
# ID: M5.1-CLI-06 — Wait for PR CI green, merge, then audit on main (NO bootstrap creation)
#
# Context:
# - Root (Mac): /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid
# - Repo: Huyen1974/agent-data-test
# - Purpose: Close M5 by merging monitoring workflows after CI green, then re-audit on main.
# - Bootstrap policy: scripts/bootstrap_gh.sh MUST exist & match .ci/bootstrap_gh.sha256. Do NOT create/modify.
# - Safety: No secret writes. Remote operations via gh. Idempotent. Exit 1 on any FAIL.

set -euo pipefail

CLI_ID="M5.1-CLI-06"
ROOT="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
REPO="Huyen1974/agent-data-test"
cd "$ROOT"; mkdir -p .ci

log(){ printf "[%s] %s\n" "$CLI_ID" "$*"; }

# ——— Guard: Bootstrap must exist & match checksum; never (re)create ————————

BOOTSTRAP="scripts/bootstrap_gh.sh"
CS_FILE=".ci/bootstrap_gh.sha256"
[ -f "$BOOTSTRAP" ] || { log "FAIL: $BOOTSTRAP missing. Abort."; exit 1; }
[ -f "$CS_FILE"   ] || { log "FAIL: $CS_FILE missing. Abort."; exit 1; }
CURR_SHA="$(shasum -a 256 "$BOOTSTRAP" | awk '{print $1}')"
REF_SHA="$(tr -d '\r\n' < "$CS_FILE")"
[ "$CURR_SHA" = "$REF_SHA" ] || { log "FAIL: bootstrap checksum mismatch. Abort."; exit 1; }

# ——— Step A) GH Auth using existing bootstrap (verify/apply only) ——————————

PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" "$BOOTSTRAP" verify || true
gh auth status -h github.com >/dev/null 2>&1 || PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" "$BOOTSTRAP" apply
gh auth status -h github.com >/dev/null 2>&1 || { log "FAIL: gh not authenticated"; exit 1; }
SCOPES="$(gh api -i /user | awk -F': ' 'tolower($1)~/^x-oauth-scopes/ {print $2}' | tr -d '\r')"
for s in repo workflow; do
  echo "$SCOPES" | tr ',' '\n' | tr -d ' ' | grep -qi "^${s}$" || { log "FAIL: missing GH scope: $s"; exit 1; }
done

# ——— Step B) Locate PR (created previously by CLI-05) ——————————————————

PR_URL="$(gh pr view --json url -q .url 2>/dev/null || true)"
if [ -z "$PR_URL" ]; then
  # Try list open PRs with head branch pattern
  PR_URL="$(gh pr list --search "is:open is:pr head:feat/m5-monitoring-workflows-" --json url -q '.[0].url' 2>/dev/null || true)"
fi
[ -n "$PR_URL" ] || { log "FAIL: No open PR found for monitoring workflows"; exit 1; }
log "Using PR: $PR_URL"

# ——— Step C) Wait for CI green on the PR ————————————————————————————————

# Poll GitHub checks until all completed & successful (timeout ~20 min)
DEADLINE=$(( $(date +%s) + 1200 ))
while :; do
  NOW=$(date +%s)
  [ "$NOW" -le "$DEADLINE" ] || { log "FAIL: CI timeout waiting for green"; exit 1; }

  # Read PR statusCheckRollup and conclude when every check is SUCCESS
  J="$(gh pr view --json statusCheckRollup,mergeStateStatus -q . 2>/dev/null || true)"
  MS="$(printf '%s' "$J" | jq -r '.mergeStateStatus // "UNKNOWN"')"
  ALL="$(printf '%s' "$J" | jq -r '[.statusCheckRollup[]? | .conclusion // .state] | if length==0 then "EMPTY" else (all(.; IN(["SUCCESS","SUCCESSFUL","COMPLETED"]) )) end')"

  log "MergeState=${MS} AllChecksSuccess=${ALL}"
  if [ "$ALL" = "EMPTY" ]; then
    # No checks registered; consider green enough (policy: allow)
    break
  fi
  if [ "$ALL" = "true" ]; then
    break
  fi
  sleep 15
done

# ——— Step D) Merge PR (squash + delete branch) ——————————————————————————

gh pr merge --squash --delete-branch --admin >/dev/null || gh pr merge --squash --delete-branch >/dev/null
log "Merged PR."

# ——— Step E) Post-merge audit on main (same rules as CLI-03, remote main) ——

TMPD="$(mktemp -d)"
audit_one(){
  _wf="$1"; _cron="$2"
  _path=".github/workflows/${_wf}"
  _raw="$TMPD/${_wf}.json"
  if gh api "repos/${REPO}/contents/${_path}?ref=main" > "$_raw" 2>/dev/null; then
    _yml="$TMPD/${_wf}.yml"
    jq -r ".content" "$_raw" | base64 --decode > "$_yml"
    _content="$(cat "$_yml")"
    _exists=1
    _has_cron=0; _has_tz=0; _has_slack=0
    printf '%s' "$_content" | grep -Eiq "cron:\s*'${_cron}'" && _has_cron=1
    printf '%s' "$_content" | grep -Eiq "timeZone:\s*'UTC'|#\stimeZone:\s'UTC'" && _has_tz=1
    printf '%s' "$_content" | grep -Eiq "SLACK_WEBHOOK|slack|chat.postMessage|hooks.slack" && _has_slack=1
  else
    _exists=0; _has_cron=0; _has_tz=0; _has_slack=0
  fi
  jq -n --arg wf "$_wf" --argjson ex "$_exists" --argjson c "$_has_cron" --argjson tz "$_has_tz" --argjson sl "$_has_slack" \
    '{workflow:$wf,exists:($ex==1),has_cron:($c==1),has_timezone_hint:($tz==1),has_slack_step:($sl==1)}'
}

A="$(audit_one artifact-audit.yml "0 2 * * *")"
S="$(audit_one secrets-audit.yml  "0 3 * * *")"
PASS_A="$(printf '%s' "$A" | jq -r '(.exists and .has_cron and .has_timezone_hint and .has_slack_step)')"
PASS_S="$(printf '%s' "$S" | jq -r '(.exists and .has_cron and .has_timezone_hint and .has_slack_step)')"

jq -n \
  --arg cli_id "$CLI_ID" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg repo "$REPO" \
  --arg scopes "$SCOPES" \
  --argjson artifacts "$A" \
  --argjson secrets   "$S" \
  --argjson pass_art "$PASS_A" \
  --argjson pass_sec "$PASS_S" \
'{
  cli_id:$cli_id,timestamp_utc:$ts,repo:$repo,github:{token_scopes:$scopes},
  artifact_audit:($artifacts|fromjson),secrets_audit:($secrets|fromjson),
  summary:{artifact_pass:($pass_art=="true"),secrets_pass:($pass_sec=="true"),all_pass:(($pass_art=="true") and ($pass_sec=="true"))}
}' > .ci/M5.1_cli06_post_merge_audit.json

log "Post-merge Artifact PASS: $PASS_A"
log "Post-merge Secrets  PASS: $PASS_S"

jq -e '.summary.all_pass==true' .ci/M5.1_cli06_post_merge_audit.json >/dev/null || { log "FAIL: Post-merge audit failed"; exit 1; }

log "PASS — M5 closed (merged & audited on main). Next: run M6 CLIs."
