#!/usr/bin/env bash
# Wrapper: calls SoT and writes .bootstrap_done marker on verify PASS
set -euo pipefail
MODE="${1:-verify}"
bash "$(dirname "$0")/../bootstrap/bin/bootstrap_gh.sh" "$MODE"
RC=$?
if [ "$RC" -eq 0 ] && [ "$MODE" = "verify" ]; then
  mkdir -p .ci
  date -u +%Y-%m-%dT%H:%M:%SZ > .ci/.bootstrap_done
fi
exit "$RC"
