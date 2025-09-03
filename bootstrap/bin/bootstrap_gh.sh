#!/usr/bin/env bash
# SoT: bootstrap/bin/bootstrap_gh.sh (versioned)
set -euo pipefail
MODE="${1:-verify}"
mkdir -p .ci
LOG=".ci/bootstrap.log"; RUN=".ci/.bootstrap_running"
ts(){ date -u +%FT%TZ; }
trap 'rm -f "$RUN"' EXIT INT TERM HUP; printf "%s\n" "$(ts)" > "$RUN"
if [ -f ".env.bootstrap" ]; then set -a; . ".env.bootstrap"; set +a
elif [ -f "bootstrap/env/.env.bootstrap" ]; then set -a; . "bootstrap/env/.env.bootstrap"; set +a
fi
PROJECT="${PROJECT:-}"; SECRET_NAME="${SECRET_NAME:-}"
{
  echo "== bootstrap:$MODE @ $(ts)"
  for b in git gh ssh; do command -v "$b" >/dev/null || { echo "missing:$b"; exit 2; }; done
  git rev-parse --is-inside-work-tree >/dev/null || { echo "not a git repo"; exit 2; }
  ORI="$(git remote get-url origin 2>/dev/null || true)"; case "$ORI" in *Huyen1974/agent-data-test*|*Huyen1974/agent-data-production*|*Huyen1974/chatgpt-githubnew* ) : ;; *) echo "wrong origin:$ORI"; exit 2;; esac; echo "origin:$ORI"
  ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=3 -T git@github.com >/dev/null 2>&1 || true
  if gh auth status -h github.com >/dev/null 2>&1; then echo "gh:logged-in"; else echo "gh:not-logged-in"; fi
  if [ "$MODE" = "verify" ]; then
    gh auth status -h github.com >/dev/null 2>&1 || { echo "verify:gh not logged-in"; exit 3; }
    echo "verify:PASS" ; exit 0
  fi
  if gh auth status -h github.com >/dev/null 2>&1; then echo "apply:already logged in"; else
    echo "apply:try login via env/secret"
    if [ -n "${GITHUB_TOKEN:-}" ]; then echo "$GITHUB_TOKEN" | gh auth login --with-token
    elif [ -n "${PROJECT:-}" ] && [ -n "${SECRET_NAME:-}" ] && command -v gcloud >/dev/null 2>&1; then
      TOK="$(gcloud secrets versions access latest --secret="$SECRET_NAME" 2>/dev/null || true)"
      [ -n "$TOK" ] && echo "$TOK" | gh auth login --with-token || true
    fi
  fi
  gh auth status -h github.com >/dev/null 2>&1 || { echo "apply:gh login failed"; exit 4; }
  echo "apply:PASS"
} | tee -a "$LOG"
