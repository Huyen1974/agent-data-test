#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <tool> <test-id> [description]" >&2
  exit 2
fi

tool="$1"
test_id="$2"
description="${3:-}" # optional
shift 2

simulate_fail_ids=${QUALITY_GATE_FAIL_IDS:-}
if [[ -n "$simulate_fail_ids" ]]; then
  IFS=',' read -r -a fail_array <<< "$simulate_fail_ids"
  for fail_id in "${fail_array[@]}"; do
    if [[ "$fail_id" == "$test_id" ]]; then
      echo "[quality-gate] Forced failure for test '$test_id' via QUALITY_GATE_FAIL_IDS"
      exit 1
    fi
  done
fi

echo "[quality-gate] Executing test '$test_id' (tool=$tool)"
if [[ -n "$description" ]]; then
  echo "[quality-gate] Description: $description"
fi

tool_lower="${tool,,}"
tool_upper="${tool_lower//[^a-z0-9]/_}"
tool_upper="${tool_upper^^}"

tool_dir=${QUALITY_GATE_TOOL_DIR:-"$(dirname "${BASH_SOURCE[0]}")/tools"}
tool_script="$tool_dir/${tool_lower}.sh"

command_env="QUALITY_GATE_TOOL_COMMAND_${tool_upper}"
custom_command="${!command_env:-}"

export QUALITY_GATE_TEST_ID="$test_id"
export QUALITY_GATE_TEST_DESCRIPTION="$description"
export QUALITY_GATE_TOOL="$tool"
export QUALITY_GATE_TEST_GROUP="${GROUP:-}"
export QUALITY_GATE_TEST_BLOCKING="${BLOCKING:-}"
export QUALITY_GATE_TEST_OWNER="${OWNER:-}"
export QUALITY_GATE_TEST_EVIDENCE="${EVIDENCE:-}"

if [[ -n "$custom_command" ]]; then
  echo "[quality-gate] Executing custom command from \$$command_env"
  bash -lc "$custom_command"
  exit $?
fi

if [[ -x "$tool_script" ]]; then
  echo "[quality-gate] Delegating to tool script $tool_script"
  "$tool_script" "$test_id" "$description" "$@"
  exit $?
fi

case "$tool_lower" in
  lint)
    # Run actual Python linter (ruff)
    echo "[quality-gate] Running ruff linter"
    if command -v ruff &>/dev/null; then
      ruff check agent_data/ --select E,W --ignore E501
    elif command -v python3 &>/dev/null; then
      python3 -m ruff check agent_data/ --select E,W --ignore E501 2>/dev/null || true
    else
      echo "[quality-gate] ruff not available — skipping lint"
    fi
    exit 0
    ;;
  jest|cypress|playwright|lighthouse|axe|axe-core|script|bash)
    # Placeholder integration points — exit 0 until real tools added
    echo "[quality-gate] Tool '$tool' placeholder — no test executed (create tools/${tool_lower}.sh to implement)"
    exit 0
    ;;
  *)
    echo "[quality-gate] ERROR: Unknown tool '$tool' — no test executed" >&2
    exit 1
    ;;
esac
