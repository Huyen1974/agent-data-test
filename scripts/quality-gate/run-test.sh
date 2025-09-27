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
  jest)
    echo "[quality-gate] Simulating Jest run"
    ;;
  cypress)
    echo "[quality-gate] Simulating Cypress run"
    ;;
  playwright)
    echo "[quality-gate] Simulating Playwright run"
    ;;
  lighthouse)
    echo "[quality-gate] Simulating Lighthouse run"
    ;;
  axe|axe-core)
    echo "[quality-gate] Simulating axe-core run"
    ;;
  script|bash)
    echo "[quality-gate] Simulating custom script run"
    ;;
  *)
    echo "[quality-gate] Unknown tool '$tool'; treating as informational" >&2
    ;;
 esac

# If external command execution is needed, the matrix command should be customised.
# Default behaviour is success with exit code 0.
exit 0
