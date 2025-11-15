#!/bin/bash
# Agent Data Langroid - Environment Validation Utilities
# Validates agent environments and detects conflicts

set -euo pipefail

# Source shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/bootstrap.sh"

# Validation functions
validate_agent_config() {
    local agent_name="$1"
    local config_file=".agents/$agent_name/runbook.md"

    log_info "Validating configuration for $agent_name..."

    # Check if config file exists
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file missing: $config_file"
        return 1
    fi

    # Validate file permissions
    local perms=$(stat -c "%a" "$config_file" 2>/dev/null || stat -f "%A" "$config_file")
    if [[ "${perms: -1}" != "4" && "${perms: -1}" != "5" && "${perms: -1}" != "6" && "${perms: -1}" != "7" ]]; then
        log_error "Configuration file not readable: $config_file"
        return 1
    fi

    log_success "$agent_name configuration validated"
    return 0
}

detect_environment_conflicts() {
    log_info "Detecting environment variable conflicts..."

    local conflicts_found=0

    # Check for conflicting Google API configurations
    if [[ -n "${GOOGLE_API_KEY:-}" && -n "${GOOGLE_GENAI_USE_GCA:-}" ]]; then
        log_warn "Potential conflict: GOOGLE_API_KEY and GOOGLE_GENAI_USE_GCA both set"
        log_warn "This may cause Gemini CLI to use Vertex AI instead of Google Code Assist"
        conflicts_found=$((conflicts_found + 1))
    fi

    # Check for sandbox environment variables that should be unset
    local sandbox_vars=("GEMINI_SANDBOX" "GEMINI_CLI_SANDBOX" "GEMINI_TOOLS_SANDBOX")
    for var in "${sandbox_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            log_warn "Sandbox variable still set: $var=${!var}"
            log_warn "This may cause Gemini CLI to run in sandbox mode"
            conflicts_found=$((conflicts_found + 1))
        fi
    done

    # Check for multiple agent environment variables
    local agent_vars=(
        "CLAUDE_CODE_PROJECT_ROOT"
        "GOOGLE_GENAI_USE_GCA"
        "CURSOR_CODEX_MODEL"
    )

    local active_agents=()
    for var in "${agent_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            case "$var" in
                CLAUDE_CODE_PROJECT_ROOT) active_agents+=("Claude") ;;
                GOOGLE_GENAI_USE_GCA) active_agents+=("Gemini") ;;
                CURSOR_CODEX_MODEL) active_agents+=("Codex") ;;
            esac
        fi
    done

    if [[ ${#active_agents[@]} -gt 1 ]]; then
        log_warn "Multiple agent environments detected: ${active_agents[*]}"
        log_warn "This may cause environment conflicts between agents"
        conflicts_found=$((conflicts_found + 1))
    fi

    if [[ $conflicts_found -eq 0 ]]; then
        log_success "No environment conflicts detected"
    else
        log_warn "Found $conflicts_found potential conflicts"
    fi

    return $conflicts_found
}

validate_dependencies() {
    local agent_name="$1"

    log_info "Validating dependencies for $agent_name..."

    case "$agent_name" in
        "claude")
            if ! command -v claude &> /dev/null; then
                log_error "Claude Code CLI not found in PATH"
                log_info "Install Claude Code CLI and ensure it's in PATH"
                return 1
            fi
            ;;
        "gemini")
            if ! command -v gemini &> /dev/null; then
                log_error "Gemini CLI not found in PATH"
                log_info "Install Gemini CLI and ensure it's in PATH"
                return 1
            fi
            ;;
        "codex")
            if ! command -v cursor &> /dev/null; then
                log_error "Cursor CLI not found in PATH"
                log_info "Install Cursor CLI and ensure it's in PATH"
                return 1
            fi
            ;;
    esac

    log_success "$agent_name dependencies validated"
    return 0
}

validate_network_connectivity() {
    log_info "Validating network connectivity..."

    # Test GitHub connectivity
    if ! curl -s --max-time 5 "https://api.github.com" >/dev/null; then
        log_error "Cannot reach GitHub API"
        return 1
    fi

    # Test Anthropic API (for Claude)
    if ! curl -s --max-time 5 "https://api.anthropic.com" >/dev/null 2>&1; then
        log_warn "Cannot reach Anthropic API (may be normal if not using Claude)"
    fi

    # Test Google APIs (for Gemini)
    if ! curl -s --max-time 5 "https://generativelanguage.googleapis.com" >/dev/null 2>&1; then
        log_warn "Cannot reach Google Generative Language API (may be normal if not using Gemini)"
    fi

    log_success "Network connectivity validated"
    return 0
}

run_comprehensive_validation() {
    local agent_name="$1"
    local exit_code=0

    log_info "Running comprehensive validation for $agent_name..."

    # Validate agent configuration
    if ! validate_agent_config "$agent_name"; then
        exit_code=1
    fi

    # Detect environment conflicts
    if ! detect_environment_conflicts; then
        exit_code=1
    fi

    # Validate dependencies
    if ! validate_dependencies "$agent_name"; then
        exit_code=1
    fi

    # Validate network connectivity
    if ! validate_network_connectivity; then
        exit_code=1
    fi

    if [[ $exit_code -eq 0 ]]; then
        log_success "All validations passed for $agent_name"
    else
        log_error "Validation failed for $agent_name"
    fi

    return $exit_code
}

# Usage information
show_usage() {
    cat << EOF
Agent Data Langroid - Environment Validation Tool

Usage: $0 <agent_name> [options]

Agents:
  claude    Validate Claude Code environment
  gemini    Validate Gemini CLI environment
  codex     Validate Codex environment
  all       Validate all agent environments

Options:
  --fix     Attempt to fix detected issues
  --verbose Show detailed validation output
  --help    Show this help message

Examples:
  $0 gemini              # Validate Gemini environment
  $0 all --fix          # Validate all agents and fix issues
  $0 claude --verbose   # Validate Claude with detailed output
EOF
}

# Main function
main() {
    local agent_name=""
    local fix_mode=false
    local verbose_mode=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)
                fix_mode=true
                shift
                ;;
            --verbose)
                verbose_mode=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            claude|gemini|codex|all)
                agent_name="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    if [[ -z "$agent_name" ]]; then
        log_error "Agent name required"
        show_usage
        exit 1
    fi

    # Set verbose mode if requested
    if [[ "$verbose_mode" == true ]]; then
        set -x
    fi

    # Run validation
    if [[ "$agent_name" == "all" ]]; then
        local overall_exit=0
        for agent in claude gemini codex; do
            log_info "Validating $agent..."
            if ! run_comprehensive_validation "$agent"; then
                overall_exit=1
            fi
        done
        return $overall_exit
    else
        run_comprehensive_validation "$agent_name"
    fi
}

# Run main if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
