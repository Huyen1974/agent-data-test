#!/usr/bin/env bash
set -euo pipefail

# Script to ensure Claude CLI is available and fix broken symlinks
# This script is designed to be called whenever Claude CLI is needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Logging function (simple version for standalone use)
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

log "Ensuring Claude CLI is available..."

LOCAL_BIN_CLAUDE="$HOME/.local/bin/claude"
CURSOR_EXTENSIONS="$HOME/.cursor/extensions"

# Check if Claude extension exists
CLAUDE_EXT_DIR=$(find "$CURSOR_EXTENSIONS" -name "*claude-code*" -type d 2>/dev/null | sort -V | tail -1)

if [ -z "$CLAUDE_EXT_DIR" ]; then
    log "ERROR: No Claude extension found in $CURSOR_EXTENSIONS"
    log "Please ensure Claude Code extension is installed in Cursor/VS Code"
    exit 1
fi

CLAUDE_BINARY="${CLAUDE_EXT_DIR}/resources/native-binary/claude"

if [ ! -f "$CLAUDE_BINARY" ]; then
    log "ERROR: Claude binary not found at: $CLAUDE_BINARY"
    log "The extension may not be properly installed"
    exit 1
fi

# Create .local/bin if it doesn't exist
mkdir -p "$HOME/.local/bin"

# Check if symlink needs updating
if [ -L "$LOCAL_BIN_CLAUDE" ]; then
    CURRENT_TARGET=$(readlink "$LOCAL_BIN_CLAUDE")
    if [ "$CURRENT_TARGET" != "$CLAUDE_BINARY" ]; then
        log "Updating Claude symlink: $CURRENT_TARGET -> $CLAUDE_BINARY"
        ln -sf "$CLAUDE_BINARY" "$LOCAL_BIN_CLAUDE"
    else
        log "Claude symlink is already up to date"
    fi
else
    log "Creating Claude symlink: $CLAUDE_BINARY"
    ln -sf "$CLAUDE_BINARY" "$LOCAL_BIN_CLAUDE"
fi

# Verify the symlink works
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null | head -1 || echo "unknown version")
    log "SUCCESS: Claude CLI is available - $CLAUDE_VERSION"
    exit 0
else
    log "ERROR: Claude CLI symlink created but 'claude' command not found in PATH"
    log "Please ensure $HOME/.local/bin is in your PATH"
    log "You can add it with: export PATH=\"$HOME/.local/bin:\$PATH\""
    exit 1
fi
