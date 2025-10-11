#!/usr/bin/env bash
set -euo pipefail

# 1. Về thư mục gốc của repo
cd "$(git rev-parse --show-toplevel)"

# 2. Chạy bootstrap chuẩn (đảm bảo môi trường sẵn sàng)
./CLI.POSTBOOT.250.sh || true

# 3. Thiết lập đăng nhập Google Code Assist (Pro)
export GOOGLE_GENAI_USE_GCA=true
unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX

# 4. Chạy Gemini CLI với model Pro ổn định, không sandbox
exec gemini -e none --extensions none --approval-mode auto_edit --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch -m gemini-2.5-pro
