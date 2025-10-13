#!/usr/bin/env bash
# Constitution Equivalence Verifier
# Verifies that injected constitution content matches source exactly

set -Eeuo pipefail
IFS=$'\n\t'

# UTF-8 for Unicode handling
export LC_ALL=${LC_ALL:-C.UTF-8} LANG=${LANG:-C.UTF-8}

# Error trap for debugging
trap 'echo "ERR ${BASH_SOURCE[0]}:$LINENO: $BASH_COMMAND" >&2; exit 97' ERR

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Configuration
CONSTITUTION_SRC="${CONSTITUTION_SRC:-docs/constitution/CONSTITUTION.md}"
DEFAULT_SECTIONS="$(cat scripts/constitution.sections 2>/dev/null || echo "VII:CURSOR_MGMT")"
SECTIONS="${SECTIONS:-$DEFAULT_SECTIONS}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; }

# Validate source file
if [[ ! -f "$CONSTITUTION_SRC" ]]; then
    log_error "Constitution source not found: $CONSTITUTION_SRC"
    exit 1
fi

# Line ending normalization - POSIX compatible
normalize_content() {
    awk '{ sub(/\r$/,""); gsub(/[[:space:]]+$/, ""); print }'
}

# Extract section from constitution
extract_section() {
    local section_spec="$1"
    local section_number="${section_spec%%:*}"

    # Use sed for precise section extraction
    if [[ "$section_number" == "VII" ]]; then
        sed -n '/^## Điều VII/,/^## /p' "$CONSTITUTION_SRC" | sed '$d' | normalize_content
    else
        # For other sections, return empty for now
        echo ""
    fi
}

# Extract injected content from runbook - safe grep
extract_injected_content() {
    local runbook_file="$1"
    local block_name="$2"

    # Extract content between markers, exclude metadata and HTML comment artifacts
    # Using || true to prevent grep from failing pipeline
    {
        sed -n "/BEGIN:CONSTITUTION:$block_name/,/END:CONSTITUTION:$block_name/p" "$runbook_file" | \
        sed '1d;$d' | \
        grep -v '^source=' | \
        grep -v '^section=' | \
        grep -v '^commit=' | \
        grep -v '^generated=' | \
        grep -v '^source_sha256=' | \
        grep -v '^-->$' | \
        sed '/^$/d'
    } | normalize_content || true
}

# Compute SHA-256 - deterministic
compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        echo "no-sha256-available"
    fi
}

# Verify equivalence for one agent/section
verify_equivalence() {
    local agent_name="$1"
    local runbook_file=".agents/$agent_name/runbook.md"
    local section_spec="$2"
    local block_name="${section_spec#*:}"

    # Check if markers exist - safe grep
    local has_marker=0
    if grep -q "BEGIN:CONSTITUTION:$block_name" "$runbook_file" 2>/dev/null; then
        has_marker=1
    fi

    if [[ $has_marker -eq 0 ]]; then
        echo "$agent_name|$section_spec|N/A|NO_MARKERS"
        return 1
    fi

    # Extract source content
    local source_content
    source_content=$(extract_section "$section_spec")

    # Extract injected content
    local injected_content
    injected_content=$(extract_injected_content "$runbook_file" "$block_name")

    # Compute hashes
    local source_hash
    source_hash=$(echo "$source_content" | compute_sha256)
    local injected_hash
    injected_hash=$(echo "$injected_content" | compute_sha256)

    # Output result
    if [[ "$source_hash" == "$injected_hash" ]]; then
        echo "$agent_name|$section_spec|$source_hash|PASS"
        return 0
    else
        echo "$agent_name|$section_spec|$source_hash|FAIL"
        return 1
    fi
}

# Show diff for failed verification
show_diff() {
    local agent_name="$1"
    local section_spec="$2"

    local runbook_file=".agents/$agent_name/runbook.md"
    local block_name="${section_spec#*:}"

    local source_content
    source_content=$(extract_section "$section_spec")
    local injected_content
    injected_content=$(extract_injected_content "$runbook_file" "$block_name")

    echo "=== DIFF: $agent_name - $section_spec ==="
    diff -u <(echo "$source_content") <(echo "$injected_content") | head -20 || true
    echo ""
}

# Main verification
main() {
    log_info "Starting Constitution Equivalence Verification"
    log_info "Source: $CONSTITUTION_SRC"
    log_info "Sections: $SECTIONS"

    local agents=("gemini" "claude" "codex")
    local results=()
    local failed_sections=()

    echo ""
    echo "VERIFICATION RESULTS:"
    echo "Agent     | Section       | SHA-256                              | Status"
    echo "----------|---------------|--------------------------------------|--------"

    # Process each agent and section
    IFS=',' read -ra SECTION_ARRAY <<< "$SECTIONS"
    for agent in "${agents[@]}"; do
        for section_spec in "${SECTION_ARRAY[@]}"; do
            # Temporarily disable errexit for this check
            set +e
            verify_equivalence "$agent" "$section_spec"
            local check_result=$?
            set -e

            if [[ $check_result -eq 0 ]]; then
                results+=("$agent|$section_spec|PASS")
            else
                results+=("$agent|$section_spec|FAIL")
                failed_sections+=("$agent:$section_spec")
            fi
        done
    done

    echo ""
    echo "SUMMARY:"
    local total_checks=${#results[@]}
    local passed_checks=0
    local failed_checks=0

    for result in "${results[@]}"; do
        if [[ "$result" == *"|PASS" ]]; then
            ((passed_checks++)) || true
        else
            ((failed_checks++)) || true
        fi
    done

    log_info "Total checks: $total_checks"
    log_ok "Passed: $passed_checks"

    if [[ $failed_checks -gt 0 ]]; then
        log_fail "Failed: $failed_checks"

        echo ""
        echo "FAILED SECTIONS DETAILS:"
        for failed_spec in "${failed_sections[@]}"; do
            IFS=':' read -r agent_name section_spec <<< "$failed_spec"
            show_diff "$agent_name" "$section_spec"
        done

        exit 1
    fi

    log_ok "All constitution content matches source exactly! ✅"
    exit 0
}

# Run main
main "$@"
