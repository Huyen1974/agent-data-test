#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <tool> <test-id> [--simulate-fail]" >&2
  exit 2
fi

tool="$1"
test_id="$2"
shift 2

simulate_fail=0
while (( "$#" )); do
  case "$1" in
    --simulate-fail)
      simulate_fail=1
      ;;
    *)
      echo "[quality-gate] Ignoring unknown argument: $1" >&2
      ;;
  esac
  shift
done

echo "[quality-gate] Running tool='$tool' for test='$test_id'"
timestamp=$(date --iso-8601=seconds)
echo "[quality-gate] Timestamp: $timestamp"

tool_binary=$(command -v "$tool" || true)
if [ -z "$tool_binary" ]; then
  echo "[quality-gate] Tool '$tool' is not installed on runner; simulating execution" >&2
else
  echo "[quality-gate] Found tool binary at $tool_binary"
fi

if [ "$simulate_fail" -eq 1 ]; then
  echo "[quality-gate] Simulating FAILURE for non-blocking test '$test_id'" >&2
  exit 1
fi

echo "[quality-gate] Simulating SUCCESS for test '$test_id'"
exit 0
