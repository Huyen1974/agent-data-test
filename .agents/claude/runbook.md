# Claude Code Runbook (Stable, Non-destructive)

## OBJECTIVE
Run Claude Code CLI like Gemini CLI for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results. Use Claude 3.5 Sonnet model.

## PRE-FLIGHT CHECKLIST (quick)
- `gh auth status` → Logged in
- `ssh -T git@github.com` → "Hi <user>!"
- `claude --version` → CLI installed and on PATH
- `test -x .agents/claude/start.sh` → start script is executable (else: `git update-index --chmod=+x .agents/claude/start.sh`)

## STARTUP (canonical, ổn định)
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
source ~/.zshrc || true
./CLI.POSTBOOT.250.sh || true
export CLAUDE_CODE_MODEL="${CLAUDE_CODE_MODEL:-claude-3-5-sonnet-20241022}"
export CLAUDE_CODE_TOOLS="${CLAUDE_CODE_TOOLS:-read_file,write_file,run_shell_command,search_file_content}"
exec claude code --model "$CLAUDE_CODE_MODEL" --allowed-tools "$CLAUDE_CODE_TOOLS"
```

Start script tương đương (idempotent): `.agents/claude/start.sh` phải khớp 100% với lệnh dài trên.

## ENVIRONMENT
- Python tooling: venv 3.11.x (ví dụ `.cienv`); tránh PEP 668 lỗi cài global.
- Lint/format: `pre-commit run --all-files`.
- Bỏ qua local dev dirs: `.genkit/`, `.lintenv/`, `tools/ai/` (đảm bảo script không bị ignore).
- Đảm bảo thư mục **.agents/** KHÔNG bị ignore trong `.gitignore` (để runbook & start script được commit).

## CONSTRAINTS
- Chỉ làm việc trên feature branch; không commit trực tiếp lên `main`.
- Không sửa dotfiles hệ thống nếu chưa được duyệt.
- Không đổi lockfiles trừ khi nhiệm vụ yêu cầu rõ.
- Hỏi trước khi thao tác phá huỷ (rm -rf, force push…).
- Không chạy lệnh phá huỷ (rm -rf, force-push, reset --hard) nếu **không có phê duyệt rõ ràng** trong chat.
- Tuân thủ `.pre-commit-config.yaml`.

## ALLOWED TOOLS
- `read_file`, `write_file`, `run_shell_command`, `search_file_content`.
- Git/GitHub: cho phép status/commit/push trên feature branch; xin duyệt khi push/force-push.

## VERIFICATION / SMOKE TESTS

### One-shot:
```bash
claude --version
```
Kỳ vọng: in ra version number.

### Help:
```bash
claude code --help
```
Kỳ vọng: hiển thị usage information.

### Interactive header check:
```bash
.agents/claude/start.sh
```
Header phải có `claude-3-5-sonnet-20241022`; thoát sạch sau khi verify.

### Tool checks trong phiên:
- `git status` (run_shell_command)
- Tạo `/tmp/claude_write_test.txt` (write_file + cat)
- `search_file_content` trên chuỗi có thật
- `web_fetch https://example.com` (200)

## ERROR HANDLING
- **Authentication**: nếu prompt login, hoàn tất trong browser rồi tiếp tục; nếu treo, terminate và restart.
- **Network**: verify internet connection; retry failed operations.
- **Rate limiting**: respect quotas; implement exponential backoff.
- **Missing dependencies**: ensure claude CLI is installed and in PATH.

## NOTES (Cursor integration)
Nếu gặp extension prompts, có thể skip; CLI hoạt động độc lập.

## ROLLBACK / RESET
- Reset environment: `unset CLAUDE_CODE_*`
- Clear session: terminate claude processes
- Re-auth: `claude auth login` if needed


<!-- BEGIN:CONSTITUTION:CURSOR_MGMT (auto-generated; do not edit)
source=docs/constitution/CONSTITUTION.md
section=CURSOR_MGMT
commit=8af9753
generated=2025-10-13 02:58:01 UTC
source_sha256=52688078763bb3b67eb103e13b84fa4951436d304548cf250a519cb88e8f8dc0
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
- Commit gọn, conventional, không đổi lockfile khi không cần.
