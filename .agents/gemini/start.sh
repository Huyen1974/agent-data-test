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
&& exec gemini -e none --extensions none --approval-mode auto_edit \
   --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
   -m gemini-2.5-pro
