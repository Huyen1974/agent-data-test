# Gemini CLI Runbook (GCA/Pro, Non-sandbox)

## OBJECTIVE
Run Gemini CLI like Claude Code for this repo: analyze code, run safe shells, edit files with approval, work ONLY on feature branches, and produce verifiable results. Prefer Google Code Assist (Pro) models.

## STARTUP (canonical)
- Env: `export GOOGLE_GENAI_USE_GCA=true` (không dùng GOOGLE_API_KEY/Vertex).
- Start:
  source ~/.zshrc && ./CLI.POSTBOOT.250.sh && export GOOGLE_GENAI_USE_GCA=true && \
  gemini -e none --extensions none --approval-mode auto_edit \
  --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch \
  -m gemini-2.5-pro
- Nếu prompt OAuth → hoàn tất đăng nhập trình duyệt rồi tiếp tục.

## CONSTRAINTS
- Chỉ làm việc trên feature branch; không commit trực tiếp lên `main`.
- Không chỉnh dotfiles hệ thống nếu chưa được duyệt.
- Không thay lockfiles trừ khi nhiệm vụ yêu cầu rõ.
- Hỏi trước khi thao tác phá huỷ (rm -rf, force push…).
- Tuân thủ `.pre-commit-config.yaml`.

## ENVIRONMENT
- Python tooling: dùng venv Python 3.11.x (ví dụ `.cienv`).
- Lint/format qua: `pre-commit run --all-files`.
- Bỏ qua local dev dirs: `.genkit/`, `.lintenv/`, `tools/ai/`.

## ALLOWED TOOLS
- `run_shell_command`, `read_file`, `write_file`, `search_file_content`, `web_fetch`.
- Git/GitHub: cho phép status/commit/push trên feature branch; xin duyệt khi push.

## SUCCESS CRITERIA
- One-shot smoke test in ra đúng `OK`.
- Header phiên tương tác có `gemini-2.5-pro` và **không** có "sandbox".
- Nếu có chỉnh code: pre-commit pass.
- Commit gọn, conventional, không đổi lockfile khi không cần.
- Báo cáo nêu "đã thay gì/ vì sao/ log xác minh".

## ERROR HANDLING
- 429/quota: xác nhận `GOOGLE_GENAI_USE_GCA=true`, retry 1 lần; nếu còn, báo rõ hướng xử lý.
- Auth gh/ssh: yêu cầu thêm PAT/SSH key nếu thiếu, không làm hành động đặc quyền khi chưa có quyền.
- Mismatch Python: ưu tiên 3.11 venv; không cài system-wide.

## REPORTING
- Nêu nguyên nhân gốc (nếu có), bản vá, cách xác minh/nhật ký; link CI nếu liên quan.
