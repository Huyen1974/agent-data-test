# Gemini CLI Runbook (GCA/Pro, Non-sandbox)

## OBJECTIVE
Run Gemini CLI like Claude Code for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results. Prefer Google Code Assist (Pro) models.

## PRE-FLIGHT CHECKLIST (quick)
- `gh auth status` → Logged in
- `ssh -T git@github.com` → "Hi <user>!"
- `gemini --version` → CLI installed and on PATH

## STARTUP (canonical, ổn định)
```bash
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
```

## REPORTING
- Nêu nguyên nhân gốc (nếu có), bản vá, log xác minh; link CI nếu liên quan.
