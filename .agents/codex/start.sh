#!/bin/bash
# Codex Agent - Startup Script
# Uses shared bootstrap utilities for consistent initialization

set -euo pipefail

# Get script directory and source shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$(dirname "$SCRIPT_DIR")/shared"
source "$SHARED_DIR/bootstrap.sh"

AGENT_NAME="codex"

# Agent-specific configuration
CODEX_STARTUP_COMMAND='cursor --codex --model "$CURSOR_CODEX_MODEL" --tools "$CURSOR_CODEX_TOOLS" --approval-mode "$CURSOR_CODEX_APPROVAL_MODE"'

# Initialize agent session
if ! init_agent_session "$AGENT_NAME"; then
    exit 1
fi

# Set Codex-specific environment variables
export CURSOR_CODEX_MODEL="gpt-4"
export CURSOR_CODEX_TOOLS="read_file,write_file,run_shell_command"
export CURSOR_CODEX_PROJECT="$(pwd)"
export CURSOR_CODEX_APPROVAL_MODE="auto_edit"

log_info "Codex environment configured:"
log_info "  Model: $CURSOR_CODEX_MODEL"
log_info "  Tools: $CURSOR_CODEX_TOOLS"
log_info "  Project: $CURSOR_CODEX_PROJECT"
log_info "  Approval Mode: $CURSOR_CODEX_APPROVAL_MODE"

# Start Codex agent using shared startup function
if ! start_agent "$AGENT_NAME" "$CODEX_STARTUP_COMMAND"; then
    log_error "Codex startup failed"
    exit 1
fi
