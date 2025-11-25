#!/usr/bin/env bash
# === POST-REBOOT / NEW-SESSION QUICKCHECK ===
set -Eeuo pipefail
export PROJECT="${PROJECT:-github-chatgpt-ggcloud}"
export SECRET_NAME="${SECRET_NAME:-gh_pat_sync_secrets}"
set +e
bash tools/bootstrap_gh.sh verify
RC=$?
set -e
if [ $RC -ne 0 ]; then
  bash tools/bootstrap_gh.sh apply
  bash tools/bootstrap_gh.sh verify
fi
bash scripts/sop_bootstrap_check.sh
MARKER=".ci/.bootstrap_done"; PASS="false"
[ -f .ci/sop_bootstrap_check/summary.json ] && PASS="$(jq -r '.pass' .ci/sop_bootstrap_check/summary.json 2>/dev/null || echo false)"
echo "=== DoD Snapshot ==="
[ -f "$MARKER" ] && echo "marker: present @ $(cat "$MARKER")" || echo "marker: missing"
echo "sop.pass: $PASS"
gh auth status -h github.com >/dev/null 2>&1 && echo "gh: logged-in" || echo "gh: not-logged-in"

# Ensure Claude CLI is available (fix broken symlinks from extension updates)
[ -x scripts/ensure_claude_cli.sh ] && scripts/ensure_claude_cli.sh >/dev/null 2>&1
