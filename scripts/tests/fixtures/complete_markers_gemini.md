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

<!-- BEGIN:CONSTITUTION:CURSOR_MGMT (auto-generated; do not edit)
source=docs/constitution/CONSTITUTION.md
section=VII
commit=a1b2c3d4e5f6
generated=2025-01-12 10:30:45 UTC
source_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
-->
## Điều VII – Quản lý Cursor
| ID | Principle | Description |
| --- | --- | --- |
| HP-CS-01 | Autonomous Execution | Execute to completion; stop only on blocking errors. |
| HP-CS-02 | Mandatory Verification & Fixes | Khi CI thất bại, Cursor được phép tự động sửa lỗi và thử lại tối đa 2 lần. Sau lần thứ 2 nếu vẫn thất bại, quy trình sẽ dừng lại và thông báo cho Owner. |
| HP-CS-03 | Rule Preservation | No delete/modify rules unless explicit prompt. |
| HP-CS-04 | PR Description Autogeneration | Cursor prepend summary table to PR description. |
| HP-CS-05 | Phân tách Quyền Ghi Secrets | • Các runner CI/CD thông thường (chạy test, build tại các repo con như agent-data-test) bị cấm tuyệt đối quyền secrets:write.<br><br> • Chỉ duy nhất quy trình đồng bộ secrets tự động (nếu có) mới được cấp quyền secrets:write để cập nhật secrets. |
<!-- END:CONSTITUTION:CURSOR_MGMT -->

## REPORTING
- Nêu nguyên nhân gốc (nếu có), bản vá, log xác minh; link CI nếu liên quan.
