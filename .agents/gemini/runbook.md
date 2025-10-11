# Gemini CLI Runbook (GCA/Pro, Non-sandbox)

## OBJECTIVE
Run Gemini CLI like Claude Code for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results. Prefer Google Code Assist (Pro) models.

## PRE-FLIGHT CHECKLIST (quick)
- `gh auth status` → Logged in
- `ssh -T git@github.com` → "Hi <user>!"
- `echo $GOOGLE_GENAI_USE_GCA` → `true`
- Python tooling in venv **3.11.x** (không cài system-wide)

## STARTUP (canonical, ổn định)
```bash
set -euo pipefail \
&& cd "$(git rev-parse --show-toplevel)" \
&& source ~/.zshrc || true \
&& ./CLI.POSTBOOT.250.sh || true \
&& export GOOGLE_GENAI_USE_GCA=true \
&& unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT \
&& exec gemini -e none --extensions none --approval-mode auto_edit \
   --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
   -m gemini-2.5-pro
```

Start script tương đương (idempotent): `./tools/ai/gemini-start.sh` phải khớp 100% với lệnh dài trên.

## EXPECTED SETTINGS (~/.gemini/settings.json)
```json
{
  "models": { "default": "gemini-2.5-pro" },
  "tools": { "sandbox": null },
  "approvals": { "mode": "auto_edit" },
  "general": { "checkpointing": { "enabled": false } }
}
```

## CONSTRAINTS
- Chỉ làm việc trên feature branch; không commit trực tiếp lên `main`.
- Không sửa dotfiles hệ thống nếu chưa được duyệt.
- Không đổi lockfiles trừ khi nhiệm vụ yêu cầu rõ.
- Hỏi trước khi thao tác phá huỷ (rm -rf, force push…).
- Tuân thủ `.pre-commit-config.yaml`.

## ENVIRONMENT
- Python tooling: venv 3.11.x (ví dụ `.cienv`); tránh PEP 668 lỗi cài global.
- Lint/format: `pre-commit run --all-files`.
- Bỏ qua local dev dirs: `.genkit/`, `.lintenv/`, `tools/ai/` (đảm bảo script không bị ignore).

## ALLOWED TOOLS
- `run_shell_command`, `read_file`, `write_file`, `search_file_content`, `web_fetch`.
- Git/GitHub: cho phép status/commit/push trên feature branch; xin duyệt khi push/force-push.

## VERIFICATION / SMOKE TESTS

### One-shot:
```bash
GOOGLE_GENAI_USE_GCA=true gemini -e none --extensions none -m gemini-2.5-pro -p "Reply with just: OK"
```
Kỳ vọng: in đúng `OK`.

### Interactive:
```bash
GOOGLE_GENAI_USE_GCA=true gemini -e none --extensions none \
  --approval-mode auto_edit \
  --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
  -m gemini-2.5-pro
```
Header phải có `gemini-2.5-pro` và **không** có "sandbox".

### Tool checks trong phiên:
- `git status` (run_shell_command)
- Tạo `/tmp/gemini_write_test.txt` (write_file + cat)
- `search_file_content` trên chuỗi có thật
- `web_fetch https://example.com` (200)

## ERROR HANDLING
- **429/quota**: xác nhận `GOOGLE_GENAI_USE_GCA=true`, retry 1 lần; nếu còn, báo quota/account.
- **OAuth**: nếu prompt, đăng nhập trình duyệt rồi tiếp tục; nếu treo, `rm -rf ~/.gemini` và đăng nhập lại.
- **Auth gh/ssh**: yêu cầu PAT/SSH key nếu thiếu; không làm hành động đặc quyền khi chưa có quyền.
- **Python mismatch/PEP 668**: dùng venv 3.11.x; tránh cài global; cân nhắc pipx/pyenv khi cần.

## NOTES (Cursor integration)
Nếu gặp "No installer is available … Gemini CLI Companion": không chặn CLI; `--extensions none` là đủ. Extension chỉ giúp tích hợp IDE, có thể cài sau.

## ROLLBACK / RESET
- Reset đăng nhập/cấu hình: `rm -rf ~/.gemini`, đăng nhập lại GCA.
- Reset environment: `unset GOOGLE_GENAI_USE_GCA` và các biến liên quan.

## REPORTING
- Nêu nguyên nhân gốc (nếu có), bản vá, log xác minh; link CI nếu liên quan.
- Commit gọn, conventional, không đổi lockfile khi không cần.
