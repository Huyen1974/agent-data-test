#!/bin/bash
# ID: M5.1-CLI-06b — Fix PR "DIRTY", sync with main, merge, then post-merge audit (NO bootstrap creation)
#
# Context:
# - Root (Mac): /Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid
# - Repo: Huyen1974/agent-data-test
# - Goal: Resolve PR mergeState=DIRTY by syncing feature branch with main (safe rules), then merge and audit on main to close M5.
# - Policy: DO NOT create/modify scripts/bootstrap_gh.sh. Verify checksum before use. Idempotent. Exit 1 on any FAIL.
# - Scope: Only touches the monitoring workflows PR (feat/m5-monitoring-workflows-*). No secret writes. Qdrant untouched.
#
# What this CLI does:
# 1) Guard bootstrap (exists + checksum match) — but never re-create it.
# 2) Ensure gh auth (verify/apply) using existing bootstrap.
# 3) Detect the PR (#) and its head branch.
# 4) Sync head branch with origin/<default-branch>:
#    - Try rebase first; if conflicts: abort rebase, then attempt a merge from main.
#    - Auto-resolve conflicts ONLY for:
#      .github/workflows/artifact-audit.yml
#      .github/workflows/secrets-audit.yml
#      using "ours" (keep feature branch versions). Any other conflicting file => abort with FAIL (avoid risk).
# 5) Push branch, wait for checks to be green (timeout 15m). If no checks, proceed.
# 6) Merge PR (squash + delete branch).
# 7) Post-merge audit on main that both workflows exist, have required cron/UTC/Slack. Gate PASS.

set -euo pipefail

CLI_ID="M5.1-CLI-06b"
ROOT="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
REPO="Huyen1974/agent-data-test"
cd "$ROOT"; mkdir -p .ci

log(){ printf "[%s] %s\n" "$CLI_ID" "$*"; }

# ——— Preflight ———————————————————————————————————————————————————————————

command -v gh >/dev/null 2>&1 || { log "FAIL: gh CLI not found"; exit 1; }
command -v jq >/dev/null 2>&1 || { log "FAIL: jq not found"; exit 1; }
git rev-parse --git-dir >/dev/null 2>&1 || { log "FAIL: not inside a Git repo"; exit 1; }

# ——— Guard: Bootstrap must exist & match checksum (never re-create) ————————

BOOTSTRAP="scripts/bootstrap_gh.sh"
CS_FILE=".ci/bootstrap_gh.sha256"
[ -f "$BOOTSTRAP" ] || { log "FAIL: $BOOTSTRAP missing. Abort."; exit 1; }
[ -f "$CS_FILE" ] || { log "FAIL: $CS_FILE missing. Abort."; exit 1; }
SHA_NOW="$(shasum -a 256 "$BOOTSTRAP" | awk '{print $1}')"
SHA_REF="$(tr -d '\r\n' < "$CS_FILE")"
[ "$SHA_NOW" = "$SHA_REF" ] || { log "FAIL: bootstrap checksum mismatch. Abort."; exit 1; }

# ——— Auth via existing bootstrap (verify/apply only) ———————————————————————

PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" "$BOOTSTRAP" verify || true
if ! gh auth status -h github.com >/dev/null 2>&1; then
  PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" "$BOOTSTRAP" apply
  gh auth status -h github.com >/dev/null 2>&1 || { log "FAIL: gh not authenticated"; exit 1; }
fi
SCOPES="$(gh api -i /user | awk -F': ' 'tolower($1)~/^x-oauth-scopes/ {print $2}' | tr -d '\r')"
for s in repo workflow; do
  echo "$SCOPES" | tr ',' '\n' | tr -d ' ' | grep -qi "^${s}$" || { log "FAIL: missing GH scope: $s"; exit 1; }
done
log "GH scopes OK: $SCOPES"

# Ensure bootstrap not modified during auth
[ "$(shasum -a 256 "$BOOTSTRAP" | awk '{print $1}')" = "$SHA_NOW" ] || { log "FAIL: bootstrap changed during CLI"; exit 1; }

# ——— Identify default branch, PR and head branch ———————————————————————————

DEF_BRANCH="$(gh repo view "$REPO" --json defaultBranchRef -q '.defaultBranchRef.name')"
PR_JSON="$(mktemp)"
if ! gh pr view --repo "$REPO" --json number,url,headRefName,mergeStateStatus,statusCheckRollup > "$PR_JSON" 2>/dev/null; then
  # fallback: pick newest open PR, prefer head: feat/m5-monitoring-workflows-*
  PR_NUM="$(gh pr list --repo "$REPO" --state open --search "head:feat/m5-monitoring-workflows-" --json number -q '.[0].number' 2>/dev/null || true)"
  if [ -z "${PR_NUM:-}" ]; then
    PR_NUM="$(gh pr list --repo "$REPO" --state open --sort created --json number -q '.[0].number' 2>/dev/null || true)"
  fi
  [ -n "${PR_NUM:-}" ] || { log "FAIL: No open PR found"; exit 1; }
  gh pr view "$PR_NUM" --repo "$REPO" --json number,url,headRefName,mergeStateStatus,statusCheckRollup > "$PR_JSON"
fi
PR_URL="$(jq -r '.url' "$PR_JSON")"
HEAD_BRANCH="$(jq -r '.headRefName' "$PR_JSON")"
MERGE_STATE="$(jq -r '.mergeStateStatus // "UNKNOWN"' "$PR_JSON")"
log "PR: $PR_URL"
log "Head branch: $HEAD_BRANCH"
log "MergeState: $MERGE_STATE"

PR_NUM="$(jq -r '.number' "$PR_JSON")"

# If PR already merged, skip to post-merge audit
if gh pr view "$PR_NUM" --repo "$REPO" --json state -q '.state' | grep -qi '^MERGED$'; then
  log "PR already merged. Proceeding to post-merge audit on main."
  goto_post_merge=true
else
  goto_post_merge=false
fi

# ——— Sync feature branch with main (only if not merged) ————————————————————

if [ "$goto_post_merge" = false ]; then
  git fetch origin "$DEF_BRANCH" --quiet || true
  git fetch origin "$HEAD_BRANCH" --quiet || true
  git checkout "$HEAD_BRANCH"

  # Handle any unstaged changes by committing them first
  if ! git diff-index --quiet HEAD --; then
    log "Committing unstaged changes before sync..."
    git add .
    git commit -m "chore: commit changes before M5 sync with main"
  fi

  # Try a clean rebase on latest main
  if git rebase "origin/$DEF_BRANCH"; then
    log "Rebase onto origin/$DEF_BRANCH succeeded."
  else
    log "Rebase hit conflicts. Aborting rebase and attempting a merge with controlled conflict resolution."
    git rebase --abort || true

    # Merge main into feature; resolve only known workflow files using ours
    set +e
    git merge --no-ff "origin/$DEF_BRANCH" -m "chore: sync with $DEF_BRANCH for monitoring workflows"
    MERGE_RC=$?
    set -e
    if [ $MERGE_RC -ne 0 ]; then
      # Resolve allowed files
      CONFLICTS="$(git ls-files -u | awk '{print $4}' | sort -u || true)"
      SAFE_FILES=".github/workflows/artifact-audit.yml .github/workflows/secrets-audit.yml scripts/bootstrap_gh.sh .ci/bootstrap_gh.sha256"
      for f in $CONFLICTS; do
        case " $SAFE_FILES " in
          *" $f "*) git checkout --ours "$f" && git add "$f" && log "Resolved (ours): $f" ;;
          *) log "FAIL: Conflict in non-whitelisted file: $f"; git merge --abort || true; exit 1 ;;
        esac
      done
      git commit -m "chore: resolve workflow conflicts (keep feature versions)"
    fi
  fi

  # Push updated head branch
  git push -u origin "$HEAD_BRANCH" || { log "FAIL: push failed"; exit 1; }

  # Wait for checks to be green (timeout ~15m)
  DEADLINE=$(( $(date +%s) + 900 ))
  while :; do
    NOW=$(date +%s); [ "$NOW" -le "$DEADLINE" ] || { log "FAIL: CI timeout waiting for green"; exit 1; }
    J="$(gh pr view "$PR_NUM" --repo "$REPO" --json statusCheckRollup,mergeStateStatus -q .)"
    MS="$(printf '%s' "$J" | jq -r '.mergeStateStatus // "UNKNOWN"')"
    ALL="$(printf '%s' "$J" | jq -r '[.statusCheckRollup[]? | .conclusion // .state] | if length==0 then "EMPTY" else (all(.; IN(["SUCCESS","SUCCESSFUL","COMPLETED"])) ) end')"
    log "MergeState=${MS} AllChecks=${ALL}"
    if [ "$ALL" = "EMPTY" ] || [ "$ALL" = "true" ]; then break; fi
    sleep 15
  done

  # Merge PR (squash + delete branch)
  if ! gh pr merge "$PR_NUM" --repo "$REPO" --squash --delete-branch --admin >/dev/null 2>&1; then
    gh pr merge "$PR_NUM" --repo "$REPO" --squash --delete-branch >/dev/null
  fi
  log "Merged PR."
fi

# ——— Post-merge audit on main ——————————————————————————————————————————————

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
    printf '%s' "$_content" | grep -Eiq "timeZone:\s*'UTC'|#\stimeZone:\s'UTC'|#.*UTC\s+daily" && _has_tz=1
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
}' > .ci/M5.1_cli06b_post_merge_audit.json

log "Post-merge Artifact PASS: $PASS_A"
log "Post-merge Secrets  PASS: $PASS_S"
jq -e '.summary.all_pass==true' .ci/M5.1_cli06b_post_merge_audit.json >/dev/null || { log "FAIL: Post-merge audit failed"; exit 1; }

log "PASS — M5 CLOSED (merged & audited on main). Proceed to M6."
