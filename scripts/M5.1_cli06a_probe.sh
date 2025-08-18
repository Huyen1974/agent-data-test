#!/bin/bash
# ID: M5.1-CLI-06a.v2 — Probe PR status (NO bootstrap creation) — decide wait or fix
#
# Context:
# - Root: /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid
# - Repo: Huyen1974/agent-data-test
# - Purpose: Decide whether to keep waiting for CLI-06 or stop and fix.
# - Policy: DO NOT create/modify bootstrap. Read-only to GitHub. Idempotent.
# - Exit code: 0 => keep waiting (CONTINUE_WAIT or MERGE_READY); 1 => stop & fix (STOP_AND_FIX).

set -euo pipefail

CLI_ID="M5.1-CLI-06a.v2"
ROOT="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
REPO="Huyen1974/agent-data-test"
cd "$ROOT"; mkdir -p .ci

log(){ printf "[%s] %s\n" "$CLI_ID" "$*"; }

# A) Require gh auth already available (NO bootstrap creation here)

if ! gh auth status -h github.com >/dev/null 2>&1; then
  log "FAIL: gh not authenticated. Run existing bootstrap manually, e.g.:"
  log 'PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh apply'
  exit 1
fi

# B) Locate the monitoring PR (prefer head: feat/m5-monitoring-workflows-*)

PR_NUM="$(gh pr list --repo "$REPO" --state open --search "head:feat/m5-monitoring-workflows-" --json number -q '.[0].number' 2>/dev/null || true)"
if [ -z "${PR_NUM:-}" ]; then
  PR_NUM="$(gh pr list --repo "$REPO" --state open --sort created --json number -q '.[0].number' 2>/dev/null || true)"
fi
[ -n "${PR_NUM:-}" ] || { log "FAIL: No open PR found"; exit 1; }

# C) Fetch PR status/checks

PR_JSON="$(mktemp)"
gh pr view "$PR_NUM" --repo "$REPO" \
  --json url,number,headRefName,mergeStateStatus,statusCheckRollup > "$PR_JSON"

PR_URL="$(jq -r '.url' "$PR_JSON")"
MERGE_STATE="$(jq -r '.mergeStateStatus // "UNKNOWN"' "$PR_JSON")"
CHECKS_JSON="$(jq -c '[.statusCheckRollup[]? | {name: (.name // "N/A"), result: ((.conclusion // .state // "UNKNOWN") | ascii_upcase)}]' "$PR_JSON")"

ANY_FAIL="$(printf '%s' "$CHECKS_JSON" | jq -r '[.[]|.result] | any(IN(["FAILURE","FAILED","CANCELLED","TIMED_OUT","ACTION_REQUIRED"]))')"
ANY_PEND="$(printf '%s' "$CHECKS_JSON" | jq -r '[.[]|.result] | any(IN(["IN_PROGRESS","QUEUED","PENDING","EXPECTED"]))')"
ALL_SUCC="$(printf '%s' "$CHECKS_JSON" | jq -r 'length as $n | ($n==0) or ([.[]|.result] | all(IN(["SUCCESS","SUCCESSFUL","COMPLETED"])))')"

ADVICE="CONTINUE_WAIT"
if [ "$MERGE_STATE" = "DIRTY" ] || [ "$ANY_FAIL" = "true" ]; then
  ADVICE="STOP_AND_FIX"
elif [ "$ALL_SUCC" = "true" ]; then
  ADVICE="MERGE_READY"
fi

jq -n \
  --arg cli_id "$CLI_ID" \
  --arg pr_url "$PR_URL" \
  --arg merge_state "$MERGE_STATE" \
  --argjson checks "$CHECKS_JSON" \
  --arg advice "$ADVICE" \
'{
  cli_id:$cli_id,
  pr_url:$pr_url,
  merge_state:$merge_state,
  checks:$checks,
  advice:$advice,
  waiting_recommended: ($advice=="CONTINUE_WAIT" or $advice=="MERGE_READY")
}' > .ci/M5.1_cli06a_probe.json

log "PR: $PR_URL"
log "MergeState: $MERGE_STATE"
log "Advice: $ADVICE"

# E) Gate by advice

if jq -e '.waiting_recommended==true' .ci/M5.1_cli06a_probe.json >/dev/null; then
  exit 0
else
  exit 1
fi
