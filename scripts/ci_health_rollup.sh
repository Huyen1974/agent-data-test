#!/bin/bash
set -euo pipefail

# CI Health Rollup Script v1
# Analyzes CI workflows, fetches failed logs, and performs UBLA audit

ID="CI-HEALTH-ROLLUP-v1"
REPO="Huyen1974/agent-data-test"
ROOT="$HOME/agent-data-test"

echo "## $ID :: start"

# Check required commands
command -v gh >/dev/null || { echo "gh not found"; exit 90; }
command -v jq >/dev/null || { echo "jq not found"; exit 91; }

# Navigate to repository and update
cd "$ROOT"
git fetch origin --prune
git checkout main
git pull --ff-only

# [A] Summarize CI for 3 main workflows on main (last 10 runs)
WFKS=(
  ".github/workflows/lint-only.yml|Lint Only"
  ".github/workflows/pass-gate.yml|Pass Gate"
  ".github/workflows/terraform-apply-gated.yml|Terraform Apply (GATED)"
)

echo "### [A] CI summary (last 10 on main)"
for pair in "${WFKS[@]}"; do
  WF="${pair%%|*}"
  WN="${pair##*|}"
  echo "-- $WN ($WF)"
  gh run list -R "$REPO" --workflow "$(basename "$WF")" --branch main -L 10 \
    --json databaseId,createdAt,event,headBranch,status,conclusion,url \
    -q ".[] | [.databaseId,.createdAt,.event,.headBranch,.status, (.conclusion//\"null\"),.url] | @tsv" \
    | sed -n "1,10p" || true
done

# [B] Fetch detailed logs for all failed runs in last 5 runs of 3 workflows
echo "### [B] Fetch failed job logs (up to last 5 runs per workflow)"
LOGD="$ROOT/governance/logs/ci"
mkdir -p "$LOGD"

for pair in "${WFKS[@]}"; do
  WF="${pair%%|*}"
  runs=$(gh run list -R "$REPO" --workflow "$(basename "$WF")" --branch main -L 5 \
    --json databaseId,conclusion | jq -r ".[] | select(.conclusion==\"failure\") | .databaseId" || true)

  for rid in $runs; do
    echo "[B] failed run: $rid — saving failed-step logs"
    gh run view -R "$REPO" "$rid" --log-failed > "$LOGD/run_${rid}_failed.log" || true
    echo "  saved: $LOGD/run_${rid}_failed.log (tail)"
    tail -n 80 "$LOGD/run_${rid}_failed.log" || true
  done
done

# [C] Verify fallback JSON-key condition in workflow on main
TMPD="$(mktemp -d)"
RAW="$TMPD/wf.json"
WF_TF=".github/workflows/terraform-apply-gated.yml"

gh api "repos/$REPO/contents/$WF_TF?ref=main" > "$RAW"
jq -r ".content" "$RAW" | base64 --decode > "$TMPD/wf.yml"

FALLBACK_IF_LINE="$(awk "/Fallback authentication \\(JSON key\\)/{p=1;next} p&&/^[[:space:]]*if:/{print;exit}" "$TMPD/wf.yml" || true)"

OK_FALLBACK=0
if [[ "$FALLBACK_IF_LINE" == *"outcome != 'success'"* && "$FALLBACK_IF_LINE" == *"HAS_KEY == 'true'"* ]]; then
  OK_FALLBACK=1
fi

echo "### [C] FALLBACK_IF_LINE: $FALLBACK_IF_LINE"
echo "### [C] OK_FALLBACK=$OK_FALLBACK"

# [D] Get latest PLAN on main (workflow_dispatch), audit UBLA and save artifact
echo "### [D] Latest PLAN on main (workflow_dispatch) + UBLA audit"

RID="$(gh run list -R "$REPO" --workflow "$(basename "$WF_TF")" --branch main -L 20 \
  --json databaseId,createdAt,event,headBranch \
  | jq -r "map(select(.event==\"workflow_dispatch\" and .headBranch==\"main\")) | sort_by(.createdAt) | (.[-1].databaseId // \"\")")"

if [ -n "$RID" ]; then
  echo "[D] RUN_ID=$RID"
  OUT="$ROOT/governance/artifacts/run_${RID}"
  mkdir -p "$OUT"

  gh run download -R "$REPO" "$RID" -n tfplan-text -D "$OUT" || true

  if [ -s "$OUT/tfplan.txt" ]; then
    SUM="$(grep -E "Plan: [0-9]+ to add, [0-9]+ to change, [0-9]+ to destroy" -m1 "$OUT/tfplan.txt" || true)"
    FTT="$(grep -Ec "uniform_bucket_level_access\\s*=\\s*false\\s*->\\s*true" "$OUT/tfplan.txt" || true)"
    TTF="$(grep -Ec "uniform_bucket_level_access\\s*=\\s*true\\s*->\\s*false" "$OUT/tfplan.txt" || true)"

    echo "[D] PLAN_SUMMARY=$SUM"
    echo "[D] UBLA_FALSE_TO_TRUE=$FTT  UBLA_TRUE_TO_FALSE=$TTF"

    if [ "${TTF:-0}" -eq 0 ]; then
      echo "[D] UBLA_HARDENING_OK"
    else
      echo "[D] UBLA_HARDENING_FAIL"
    fi
  else
    echo "[D] MISSING tfplan.txt for RUN $RID"
  fi
else
  echo "[D] NO workflow_dispatch PLAN run found on main"
fi

# Cleanup temporary directory
rm -rf "$TMPD"

echo "## $ID :: done"
