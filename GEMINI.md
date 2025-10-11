# Gemini CLI Runbook — GCA/Pro (Non-Sandbox)

## OBJECTIVE
Chạy Gemini CLI *như Claude Code* trong repo này: phân tích mã, chạy shell an toàn, chỉnh file có phê duyệt, chỉ làm trên feature branch, báo cáo có bằng chứng. Ưu tiên Google Code Assist (Pro).

## PRE-FLIGHT CHECKLIST (nhanh)
- ✅ `gh auth status` = Logged in
- ✅ `ssh -T git@github.com` = "Hi <user>!"
- ✅ GCA: `echo $GOOGLE_GENAI_USE_GCA` → `true`
- ✅ Python: dùng venv **3.11.x** cho tooling (không cài system-wide)

## STARTUP (canonical, dài cho chắc)
```bash
set -euo pipefail \
&& source ~/.zshrc || true \
&& ./CLI.POSTBOOT.250.sh || true \
&& export GOOGLE_GENAI_USE_GCA=true \
&& unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT \
&& gemini -e none --extensions none --approval-mode auto_edit \
   --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
   -m gemini-2.5-pro
```

Start script trong repo (idempotent):

`./tools/ai/gemini-start.sh` phải chạy tương đương y hệt lệnh dài trên (không sandbox, GCA, cùng flags).

## EXPECTED SETTINGS (~/.gemini/settings.json)
{
  "models": { "default": "gemini-2.5-pro" },
  "tools": { "sandbox": null },
  "approvals": { "mode": "auto_edit" },
  "general": { "checkpointing": { "enabled": false } }
}

## ALLOWED TOOLS

run_shell_command, read_file, write_file, search_file_content, web_fetch

Git/GitHub: chỉ trên feature branch, xin duyệt khi push/force-push.

## CONSTRAINTS

Không commit trực tiếp lên main.

Không đổi lockfiles trừ khi nhiệm vụ yêu cầu rõ.

Không sửa dotfiles hệ thống nếu chưa được duyệt.

Tuân thủ .pre-commit-config.yaml; nếu chỉnh code, phải pass pre-commit.

## VERIFICATION (copy & chạy)

One-shot smoke test (mong đợi in đúng "OK"):

GOOGLE_GENAI_USE_GCA=true gemini -e none --extensions none -m gemini-2.5-pro -p "Reply with just: OK"


Interactive header (mong đợi không có chữ "sandbox"):

GOOGLE_GENAI_USE_GCA=true gemini -e none --extensions none \
  --approval-mode auto_edit \
  --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
  -m gemini-2.5-pro


Tool sanity (trong phiên):

git status, gh auth status, ssh -T git@github.com

write_file("/tmp/g.txt","hello") + tail -n1 /tmp/g.txt → hello

search_file_content("bootstrap:verify")

web_fetch("https://example.com") → 200

## SUCCESS CRITERIA

One-shot test in đúng OK, không 429.

Header hiển thị gemini-2.5-pro, không "sandbox".

Nếu có chỉnh code → pre-commit pass.

Commit message kiểu conventional, báo cáo nêu rõ thay đổi & log xác minh.

## ERROR HANDLING

429/quota → xác nhận GOOGLE_GENAI_USE_GCA=true, retry 1 lần; nếu còn, báo hướng xử lý/quota.

Python/venv mismatch → dùng Python 3.11 venv, không cài global.

Thiếu quyền gh/ssh → yêu cầu người dùng cung cấp PAT/SSH trước khi thực hiện hành động đặc quyền.

## ROLLBACK
git restore --staged --worktree GEMINI.md tools/ai/gemini-start.sh || true
git checkout -- GEMINI.md tools/ai/gemini-start.sh || true
rm -rf ~/.gemini  # reset settings, đăng nhập GCA lại khi cần
