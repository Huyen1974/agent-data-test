#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source ~/.zshrc || true
./CLI.POSTBOOT.250.sh || true
export GOOGLE_GENAI_USE_GCA=true
unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT
exec gemini -e none --extensions none --approval-mode auto_edit --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch -m gemini-2.5-pro
