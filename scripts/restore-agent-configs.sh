#!/usr/bin/env bash
# restore-agent-configs.sh — Restore agent config files from a backup
# Usage: bash scripts/restore-agent-configs.sh [timestamp|latest]
set -euo pipefail

BACKUP_ROOT="${HOME}/.config/agent-backup"

# Determine which backup to restore
TARGET="${1:-latest}"

if [[ "${TARGET}" == "latest" ]]; then
  BACKUP_DIR=$(ls -1d "${BACKUP_ROOT}"/20* 2>/dev/null | tail -1)
  if [[ -z "${BACKUP_DIR}" ]]; then
    echo "ERROR: No backups found in ${BACKUP_ROOT}"
    exit 1
  fi
else
  BACKUP_DIR="${BACKUP_ROOT}/${TARGET}"
fi

if [[ ! -d "${BACKUP_DIR}" ]]; then
  echo "ERROR: Backup directory not found: ${BACKUP_DIR}"
  echo "Available backups:"
  ls -1d "${BACKUP_ROOT}"/20* 2>/dev/null | xargs -I{} basename {} || echo "  (none)"
  exit 1
fi

# Map: backup_name|original_path (portable — no bash 4 associative arrays)
ENTRIES=(
  "claude.json|${HOME}/.claude.json"
  "codex-config.toml|${HOME}/.codex/config.toml"
  "gemini-settings-template.json|${HOME}/.gemini/settings.template.json"
  "claude-desktop-config.json|${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
  "agent-data-test-mcp.json|${HOME}/Documents/Manual Deploy/agent-data-test/.mcp.json"
  "web-test-mcp.json|${HOME}/Documents/Manual Deploy/web-test/.mcp.json"
  "credentials-local.json|${HOME}/Documents/Manual Deploy/web-test/dot/config/credentials.local.json"
)

echo "=== Agent Config Restore ==="
echo "From: ${BACKUP_DIR}"
echo ""

# Verify checksums first
if [[ -f "${BACKUP_DIR}/checksums.sha256" ]]; then
  echo "Verifying checksums..."
  if (cd "${BACKUP_DIR}" && shasum -a 256 -c checksums.sha256 --quiet 2>/dev/null); then
    echo "Checksums: VALID"
  else
    echo "WARNING: Checksum mismatch detected!"
    read -p "Continue anyway? (y/N) " -r
    if [[ ! "${REPLY}" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 1
    fi
  fi
else
  echo "WARNING: No checksums.sha256 found — skipping verification"
fi

echo ""

RESTORED=0
SKIPPED=0

for entry in "${ENTRIES[@]}"; do
  NAME="${entry%%|*}"
  DEST="${entry##*|}"
  SRC="${BACKUP_DIR}/${NAME}"

  if [[ -f "${SRC}" ]]; then
    DEST_DIR=$(dirname "${DEST}")
    mkdir -p "${DEST_DIR}"
    cp "${SRC}" "${DEST}"
    echo "OK  ${NAME} → ${DEST}"
    RESTORED=$((RESTORED + 1))
  else
    echo "SKIP ${NAME} — not in backup"
    SKIPPED=$((SKIPPED + 1))
  fi
done

# Post-restore checksum verification
echo ""
echo "Post-restore verification..."
FAIL=0
for entry in "${ENTRIES[@]}"; do
  NAME="${entry%%|*}"
  DEST="${entry##*|}"
  SRC="${BACKUP_DIR}/${NAME}"
  if [[ -f "${SRC}" && -f "${DEST}" ]]; then
    HASH_SRC=$(shasum -a 256 "${SRC}" | cut -d' ' -f1)
    HASH_DEST=$(shasum -a 256 "${DEST}" | cut -d' ' -f1)
    if [[ "${HASH_SRC}" == "${HASH_DEST}" ]]; then
      echo "  MATCH ${NAME}"
    else
      echo "  FAIL  ${NAME} — hash mismatch!"
      FAIL=1
    fi
  fi
done

echo ""
echo "Restored: ${RESTORED}, Skipped: ${SKIPPED}"
if [[ ${FAIL} -ne 0 ]]; then
  echo "WARNING: Some files did not verify correctly!"
  exit 1
fi
echo "=== Restore complete ==="
