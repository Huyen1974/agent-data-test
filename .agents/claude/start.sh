#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source ~/.zshrc || true
./CLI.POSTBOOT.250.sh || true
export CLAUDE_CODE_MODEL="${CLAUDE_CODE_MODEL:-claude-3-5-sonnet-20241022}"
export CLAUDE_CODE_TOOLS="${CLAUDE_CODE_TOOLS:-read_file,write_file,run_shell_command,search_file_content}"
exec claude code --model "$CLAUDE_CODE_MODEL" --allowed-tools "$CLAUDE_CODE_TOOLS"
