# Gemini CLI Setup for Agent-Data-Langroid

## OBJECTIVE

Stabilize "Gemini CLI like Claude Code" on this repo, using Google Code Assist (Pro), non-sandbox, idempotent, safe.

Make Gemini CLI behave like Claude Code: can analyze repo, run safe shell, edit files with approval, work only on feature branches, and report results.

Prefer GCA (Pro) models; default model gemini-2.5-pro. Disable sandbox.

Provide a single long start command (no alias dependency) and an idempotent script inside repo to start Gemini reliably.

## CONSTRAINTS

- No changes on main directly. Work in current feature branch.
- Don't modify global system files without explicit confirmation; prefer repo-contained scripts.
- Don't change lockfiles unless necessary.
- Ask approval before any destructive command.
- Keep changes minimal, commit messages conventional.
- Work only on feature branches.

## CAPABILITIES

- Analyze repository structure and code
- Run safe shell commands with approval
- Edit files with user approval
- Work on feature branches only
- Report results and changes
- Use Google Code Assist (Pro) models
- Default to gemini-2.5-pro model
- Non-sandbox environment

## SUCCESS CRITERIA

- All smoke tests pass (show outputs).
- Start command and script run cleanly after macOS reboot (idempotent).
- Gemini session header shows gemini-2.5-pro and no "sandbox".
- No edits to global dotfiles unless approved.
- CLI one-shot test returns "OK"
- Interactive test returns "OK"

## SAFETY

- Never switch to sandbox unless explicitly requested.
- Ask approval before destructive commands.
- Error handling for OAuth, quotas, and resource exhaustion.
- If OAuth needed, prompt user to complete browser login, then auto-continue.
- If RESOURCE_EXHAUSTED/429, verify GOOGLE_GENAI_USE_GCA=true, retry once; if persists, print actionable note (quota/account).
