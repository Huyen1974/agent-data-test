#!/bin/bash
# Gemini CLI Agent - Startup Script
# Canonical startup matching runbook exactly

set -euo pipefail \
&& cd "$(git rev-parse --show-toplevel)" \
&& source ~/.zshrc || true \
&& ./CLI.POSTBOOT.250.sh || true \
&& export GOOGLE_GENAI_USE_GCA=true \
&& unset GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX GEMINI_TOOL_SANDBOX GEMINI_EXTENSIONS_SANDBOX \
          GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT \
&& export AGENT_CONSTITUTION_PATH="docs/constitution/CONSTITUTION.md" \
&& export AGENT_CONSTITUTION_SECTIONS="${AGENT_CONSTITUTION_SECTIONS:-VII,IX}" \
&& export AGENT_CONSTITUTION_SNAPSHOT="/tmp/constitution.$(id -u).$$.md" \
&& source .agents/shared/constitution_runtime.sh || exit 12 \
&& const_build_snapshot "$AGENT_CONSTITUTION_PATH" "$AGENT_CONSTITUTION_SECTIONS" "$AGENT_CONSTITUTION_SNAPSHOT" \
&& [[ -s "$AGENT_CONSTITUTION_SNAPSHOT" ]] || { echo "ERROR: Snapshot empty or missing" >&2; exit 13; } \
&& export AGENT_CONSTITUTION_SHA="$(const_sha256 < "$AGENT_CONSTITUTION_SNAPSHOT")" \
&& [[ "${#AGENT_CONSTITUTION_SHA}" -eq 64 ]] || { echo "ERROR: Invalid SHA-256 length" >&2; exit 14; } \
&& const_banner \
&& const_checklist \
&& exec gemini -e none --extensions none --approval-mode auto_edit \
   --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
   -m gemini-2.5-pro
