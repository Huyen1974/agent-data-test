#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source ~/.zshrc || true
./CLI.POSTBOOT.250.sh || true
export CLAUDE_CODE_MODEL="${CLAUDE_CODE_MODEL:-claude-3-5-sonnet-20241022}"
export CLAUDE_CODE_TOOLS="${CLAUDE_CODE_TOOLS:-read_file,write_file,run_shell_command,search_file_content}"

export AGENT_CONSTITUTION_PATH="docs/constitution/CONSTITUTION.md"
export AGENT_CONSTITUTION_SECTIONS="${AGENT_CONSTITUTION_SECTIONS:-VII,IX}"
export AGENT_CONSTITUTION_SNAPSHOT="/tmp/constitution.$(id -u).$$.md"

source .agents/shared/constitution_runtime.sh || exit 12

const_build_snapshot "$AGENT_CONSTITUTION_PATH" "$AGENT_CONSTITUTION_SECTIONS" "$AGENT_CONSTITUTION_SNAPSHOT"
[[ -s "$AGENT_CONSTITUTION_SNAPSHOT" ]] || { echo "ERROR: Snapshot empty or missing" >&2; exit 13; }
export AGENT_CONSTITUTION_SHA="$(const_sha256 < "$AGENT_CONSTITUTION_SNAPSHOT")"
[[ "${#AGENT_CONSTITUTION_SHA}" -eq 64 ]] || { echo "ERROR: Invalid SHA-256 length" >&2; exit 14; }

const_banner
const_checklist

exec claude code --model "$CLAUDE_CODE_MODEL" --allowed-tools "$CLAUDE_CODE_TOOLS"
