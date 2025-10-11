# Gemini CLI Runbook (GCA/Pro, Non-sandbox)

## OBJECTIVE
Run Gemini CLI like Claude Code for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results. Prefer Google Code Assist (Pro) models.

> **Quick Start (copy-paste)**
> ```bash
> set -euo pipefail \
> && cd "$(git rev-parse --show-toplevel)" \
> && source ~/.zshrc || true \
> && ./CLI.POSTBOOT.250.sh || true \
> && export GOOGLE_GENAI_USE_GCA=true \
> && unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT \
> && exec gemini -e none --extensions none --approval-mode auto_edit \
>    --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
>    -m gemini-2.5-pro
> ```
> Or run script: `.agents/gemini/start.sh`

## PRE-FLIGHT CHECKLIST (quick)
- `gh auth status` → Logged in
- `ssh -T git@github.com` → "Hi <user>!"
- `echo $GOOGLE_GENAI_USE_GCA` → `true`
- Python tooling in venv **3.11.x** (không cài system-wide)
- `gemini --version` → CLI installed and on PATH
- `test -x .agents/gemini/start.sh` → start script is executable (else: `git update-index --chmod=+x .agents/gemini/start.sh`)

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

Start script tương đương (idempotent): `.agents/gemini/start.sh` phải khớp 100% với lệnh dài trên.

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
- Không chạy lệnh phá huỷ (rm -rf, force-push, reset --hard) nếu **không có phê duyệt rõ ràng** trong chat.
- Tuân thủ `.pre-commit-config.yaml`.

## ENVIRONMENT
- Python tooling: venv 3.11.x (ví dụ `.cienv`); tránh PEP 668 lỗi cài global.
- Lint/format: `pre-commit run --all-files`.
- Bỏ qua local dev dirs: `.genkit/`, `.lintenv/`, `tools/ai/` (đảm bảo script không bị ignore).
- Đảm bảo thư mục **.agents/** KHÔNG bị ignore trong `.gitignore` (để runbook & start script được commit).

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

- Header check: đảm bảo dòng đầu phiên có `gemini-2.5-pro` và **không** chứa từ "sandbox". Nếu có "sandbox", xem lại `~/.gemini/settings.json` ("sandbox": null) và cờ `-e none`.

## ERROR HANDLING
- **OAuth**: nếu prompt → đăng nhập trình duyệt rồi tiếp tục; nếu treo hoặc lỗi "stale session", chạy `rm -rf ~/.gemini` rồi chạy lại lệnh STARTUP để đăng nhập GCA mới.
- **Cursor extension warning** ("No installer is available … Gemini CLI Companion"): KHÔNG chặn CLI; `--extensions none` là đủ. Có thể cài sau để tích hợp IDE.

## ROLLBACK / RESET
- Reset đăng nhập/cấu hình: `rm -rf ~/.gemini`, đăng nhập lại GCA.
- Reset environment: `unset GOOGLE_GENAI_USE_GCA` và các biến liên quan.

## REPORTING
- Nêu nguyên nhân gốc (nếu có), bản vá, log xác minh; link CI nếu liên quan.
- Commit gọn, conventional, không đổi lockfile khi không cần.
