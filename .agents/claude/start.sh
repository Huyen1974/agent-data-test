#!/bin/bash
# Claude Code Agent - Startup Script
# Uses shared bootstrap utilities for consistent initialization

set -euo pipefail

# Get script directory and source shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$(dirname "$SCRIPT_DIR")/shared"
source "$SHARED_DIR/bootstrap.sh"

AGENT_NAME="claude"

# Agent-specific configuration
CLAUDE_STARTUP_COMMAND='claude code --model "$CLAUDE_CODE_MODEL" --tools "$CLAUDE_CODE_TOOLS" --approval-mode "$CLAUDE_CODE_APPROVAL_MODE"'

# Initialize agent session
if ! init_agent_session "$AGENT_NAME"; then
    exit 1
fi

# Set Claude-specific environment variables
export CLAUDE_CODE_PROJECT_ROOT="$(pwd)"
export CLAUDE_CODE_MODEL="claude-3-5-sonnet-20241022"
export CLAUDE_CODE_TOOLS="read_file,write_file,run_shell_command,search_file_content"
export CLAUDE_CODE_APPROVAL_MODE="auto_edit"

log_info "Claude Code environment configured:"
log_info "  Model: $CLAUDE_CODE_MODEL"
log_info "  Tools: $CLAUDE_CODE_TOOLS"
log_info "  Approval Mode: $CLAUDE_CODE_APPROVAL_MODE"

# Start Claude agent using shared startup function
if ! start_agent "$AGENT_NAME" "$CLAUDE_STARTUP_COMMAND"; then
    log_error "Claude Code startup failed"
    exit 1
fi
