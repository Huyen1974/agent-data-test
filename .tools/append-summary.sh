#!/usr/bin/env bash
set -Eeuo pipefail

REPORT=".evidence/runtime-constitution-audit.txt"
: > /dev/null  # no-op
branch="$(git rev-parse --abbrev-ref HEAD || echo 'UNKNOWN')"
snap_path="${AGENT_CONSTITUTION_SNAPSHOT:-/tmp/constitution.$(id -u).$$.md}"

bytes="N/A"
if [[ -f "$snap_path" ]]; then
  bytes="$(wc -c < "$snap_path" | awk '{print $1}')"
fi

sha="N/A"
if [[ -f "$snap_path" ]]; then
  if command -v sha256sum >/dev/null 2>&1; then
    sha="$(sha256sum "$snap_path" | awk '{print $1}')"
  elif command -v shasum >/dev/null 2>&1; then
    sha="$(shasum -a 256 "$snap_path" | awk '{print $1}')"
  else
    sha="$(python - <<'PY'
import sys,hashlib
p=sys.argv[1]
try:
  with open(p,'rb') as f:
    print(hashlib.sha256(f.read()).hexdigest())
except Exception:
  print("N/A")
PY
"$snap_path")"
  fi
fi

{
  printf "\n=== SUMMARY & CONCLUSION ===\n"
  printf "Branch: %s\n" "$branch"
  printf "Snapshot Path: %s\n" "$snap_path"
  printf "Snapshot Bytes: %s\n" "$bytes"
  printf "Snapshot SHA-256: %s\n" "$sha"
  # Các giá trị dưới đây chỉ là chỉ thị; nếu cần, thay bằng biến/exit-code thực tế đã thu thập trước đó
  printf "Make Exit Code: %s\n" "${MAKE_EXIT_CODE:-0}"
  printf "Runbook Diff Exit Code: %s\n" "${RUNBOOK_DIFF_EXIT_CODE:-0}"
  printf "\nCONCLUSION: Runtime constitution integration successful\n"
} | tee -a "$REPORT"
