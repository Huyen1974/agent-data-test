#!/bin/bash
# Agent Data Langroid - Shared Bootstrap Utilities
# Provides common initialization functions for all agents

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Environment validation functions
validate_environment() {
    local agent_name="$1"

    log_info "Validating environment for $agent_name..."

    # Check if we're in the correct project directory
    if [[ ! -f "CLI.POSTBOOT.250.sh" ]]; then
        log_error "Not in project root directory. Please cd to project root."
        return 1
    fi

    # Check if bootstrap has been run
    if [[ ! -f ".ci/.bootstrap_done" ]]; then
        log_warn "Bootstrap not completed. Running bootstrap..."
        if ! ./CLI.POSTBOOT.250.sh; then
            log_error "Bootstrap failed"
            return 1
        fi
    fi

    # Check GitHub authentication
    if ! gh auth status >/dev/null 2>&1; then
        log_error "GitHub authentication not configured"
        return 1
    fi

    log_success "Environment validation passed for $agent_name"
    return 0
}

# Environment cleanup function
cleanup_environment() {
    local agent_name="$1"

    log_info "Cleaning up environment after $agent_name session..."

    # Unset agent-specific environment variables
    case "$agent_name" in
        "claude")
            unset CLAUDE_CODE_PROJECT_ROOT
            unset CLAUDE_CODE_MODEL
            unset CLAUDE_CODE_TOOLS
            unset CLAUDE_CODE_APPROVAL_MODE
            ;;
        "gemini")
            unset GOOGLE_GENAI_USE_GCA
            unset GEMINI_CLI_MODEL
            unset GEMINI_CLI_TOOLS
            unset GEMINI_CLI_APPROVAL_MODE
            unset GEMINI_CLI_EXTENSIONS
            ;;
        "codex")
            unset CURSOR_CODEX_MODEL
            unset CURSOR_CODEX_TOOLS
            unset CURSOR_CODEX_PROJECT
            unset CURSOR_CODEX_APPROVAL_MODE
            ;;
    esac

    # Clean up any temporary files
    find /tmp -name "agent_${agent_name}_*" -type f -mtime +1 -delete 2>/dev/null || true

    log_success "Environment cleanup completed for $agent_name"
}

# Agent startup wrapper
start_agent() {
    local agent_name="$1"
    local startup_command="$2"

    log_info "Starting $agent_name agent..."

    # Validate environment
    if ! validate_environment "$agent_name"; then
        log_error "Environment validation failed. Aborting $agent_name startup."
        return 1
    fi

    # Set session start marker
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" > "/tmp/agent_${agent_name}_session_start"

    # Execute startup command
    log_info "Executing startup command for $agent_name"
    if eval "$startup_command"; then
        log_success "$agent_name session completed successfully"
    else
        local exit_code=$?
        log_error "$agent_name session failed with exit code $exit_code"
        return $exit_code
    fi

    # Cleanup environment
    cleanup_environment "$agent_name"

    # Remove session marker
    rm -f "/tmp/agent_${agent_name}_session_start"
}

# Check if agent is already running
is_agent_running() {
    local agent_name="$1"
    local session_file="/tmp/agent_${agent_name}_session_start"

    if [[ -f "$session_file" ]]; then
        local start_time=$(cat "$session_file")
        log_warn "$agent_name session already active since $start_time"
        return 0
    else
        return 1
    fi
}

# Get current branch and validate
validate_branch() {
    local current_branch=$(git branch --show-current)

    if [[ "$current_branch" == "main" ]]; then
        log_error "Cannot start agent on main branch. Please switch to a feature branch."
        log_info "Create a feature branch: git checkout -b feature/your-feature-name"
        return 1
    fi

    log_info "Working on branch: $current_branch"
    return 0
}

# Main initialization function
init_agent_session() {
    local agent_name="$1"

    log_info "Initializing $agent_name session..."

    # Check if agent is already running
    if is_agent_running "$agent_name"; then
        read -p "Agent session already active. Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Agent startup cancelled by user"
            return 1
        fi
    fi

    # Validate branch
    if ! validate_branch; then
        return 1
    fi

    log_success "$agent_name session initialization complete"
    return 0
}
