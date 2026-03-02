#!/usr/bin/env bash
# backup-agent-configs.sh — Backup all agent config files to a timestamped folder
# Usage: bash scripts/backup-agent-configs.sh
set -euo pipefail

BACKUP_ROOT="${HOME}/.config/agent-backup"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
MAX_BACKUPS=10

# Config files to backup (source → relative name in backup)
declare -a SOURCES=(
  "${HOME}/.claude.json|claude.json"
  "${HOME}/.codex/config.toml|codex-config.toml"
  "${HOME}/.gemini/settings.template.json|gemini-settings-template.json"
  "${HOME}/Library/Application Support/Claude/claude_desktop_config.json|claude-desktop-config.json"
  "${HOME}/Documents/Manual Deploy/agent-data-test/.mcp.json|agent-data-test-mcp.json"
  "${HOME}/Documents/Manual Deploy/web-test/.mcp.json|web-test-mcp.json"
  "${HOME}/Documents/Manual Deploy/web-test/dot/config/credentials.local.json|credentials-local.json"
)

mkdir -p "${BACKUP_DIR}"

echo "=== Agent Config Backup ==="
echo "Timestamp: ${TIMESTAMP}"
echo "Target: ${BACKUP_DIR}"
echo ""

COPIED=0
SKIPPED=0

for entry in "${SOURCES[@]}"; do
  SRC="${entry%%|*}"
  NAME="${entry##*|}"

  if [[ -f "${SRC}" ]]; then
    cp "${SRC}" "${BACKUP_DIR}/${NAME}"
    HASH=$(shasum -a 256 "${BACKUP_DIR}/${NAME}" | cut -d' ' -f1)
    SIZE=$(wc -c < "${BACKUP_DIR}/${NAME}" | tr -d ' ')
    echo "OK  ${NAME} (${SIZE}B) sha256:${HASH:0:16}..."
    COPIED=$((COPIED + 1))
  else
    echo "SKIP ${NAME} — source not found: ${SRC}"
    SKIPPED=$((SKIPPED + 1))
  fi
done

# Generate checksums file
(cd "${BACKUP_DIR}" && shasum -a 256 * 2>/dev/null > checksums.sha256)

echo ""
echo "Copied: ${COPIED}, Skipped: ${SKIPPED}"
echo "Checksums: ${BACKUP_DIR}/checksums.sha256"

# Prune old backups (keep MAX_BACKUPS most recent)
TOTAL=$(ls -1d "${BACKUP_ROOT}"/20* 2>/dev/null | wc -l | tr -d ' ')
if [[ ${TOTAL} -gt ${MAX_BACKUPS} ]]; then
  PRUNE=$((TOTAL - MAX_BACKUPS))
  echo ""
  echo "Pruning ${PRUNE} old backup(s) (keeping ${MAX_BACKUPS})..."
  ls -1d "${BACKUP_ROOT}"/20* | head -n "${PRUNE}" | while read -r OLD; do
    rm -rf "${OLD}"
    echo "  Removed: $(basename "${OLD}")"
  done
fi

echo ""
echo "=== Backup complete ==="
