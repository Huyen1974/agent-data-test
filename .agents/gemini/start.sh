#!/bin/bash
# Gemini CLI Agent - Startup Script
# Uses shared bootstrap utilities for consistent initialization

set -euo pipefail

# Get script directory and source shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHARED_DIR="$(dirname "$SCRIPT_DIR")/shared"
source "$SHARED_DIR/bootstrap.sh"

AGENT_NAME="gemini"

# Agent-specific configuration
GEMINI_STARTUP_COMMAND='gemini -e none --extensions none --approval-mode auto_edit --allowed-tools run_shell_command,read_file,write_file,search_file_content,web_fetch -m gemini-2.5-pro'

# Initialize agent session
if ! init_agent_session "$AGENT_NAME"; then
    exit 1
fi

# Set Gemini-specific environment variables
export GOOGLE_GENAI_USE_GCA=true
export GEMINI_CLI_MODEL="gemini-2.5-pro"
export GEMINI_CLI_TOOLS="run_shell_command,read_file,write_file,search_file_content,web_fetch"
export GEMINI_CLI_APPROVAL_MODE="auto_edit"
export GEMINI_CLI_EXTENSIONS="none"

# Unset conflicting environment variables
unset GEMINI_SANDBOX GEMINI_CLI_SANDBOX GEMINI_TOOLS_SANDBOX
unset GOOGLE_API_KEY AISTUDIO_API_KEY VERTEX_AI_PROJECT
unset GOOGLE_VERTEX_PROJECT GOOGLE_VERTEX_LOCATION GOOGLE_CLOUD_PROJECT

log_info "Gemini CLI environment configured:"
log_info "  Model: $GEMINI_CLI_MODEL"
log_info "  Tools: $GEMINI_CLI_TOOLS"
log_info "  GCA Mode: $GOOGLE_GENAI_USE_GCA"
log_info "  Extensions: $GEMINI_CLI_EXTENSIONS"

# Start Gemini agent using shared startup function
if ! start_agent "$AGENT_NAME" "$GEMINI_STARTUP_COMMAND"; then
    log_error "Gemini CLI startup failed"
    exit 1
fi
