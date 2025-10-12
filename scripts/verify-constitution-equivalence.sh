#!/usr/bin/env bash
# Constitution Equivalence Verifier
# Verifies that injected constitution content matches source exactly

set -euo pipefail
IFS=$'\n\t'

# UTF-8 for Unicode handling
export LC_ALL=C.UTF-8 LANG=C.UTF-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
BLUE='\033[0;34m'
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

# Line ending normalization
normalize_content() {
    awk '{ sub(/\r$/,""); print }' | sed 's/[[:space:]]*$//'
}

# Extract section from constitution
extract_section() {
    local section_spec="$1"
    local section_number="${section_spec%%:*}"
    local block_name="${section_spec#*:}"

    # Use sed for precise section extraction (matches sync script)
    if [[ "$section_number" == "VII" ]]; then
        sed -n '/^## Điều VII/,/^## /p' "$CONSTITUTION_SRC" | sed '$d' | normalize_content
    else
        # For other sections, return empty for now
        echo ""
    fi
}

# Extract injected content from runbook
extract_injected_content() {
    local runbook_file="$1"
    local block_name="$2"

    # Extract content between markers, exclude metadata and HTML comment artifacts
    sed -n "/BEGIN:CONSTITUTION:$block_name/,/END:CONSTITUTION:$block_name/p" "$runbook_file" | \
    sed '1d;$d' | \
    grep -v '^source=' | \
    grep -v '^section=' | \
    grep -v '^commit=' | \
    grep -v '^generated=' | \
    grep -v '^source_sha256=' | \
    grep -v '^-->$' | \
    sed '/^$/d' | \
    normalize_content
}

# Compute SHA-256
compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | cut -d' ' -f1
    else
        echo "no-sha256-available"
    fi
}

# Verify equivalence for one agent/section
verify_equivalence() {
    local agent_name="$1"
    local runbook_file=".agents/$agent_name/runbook.md"
    local section_spec="$2"
    local section_id="${section_spec%%:*}"
    local block_name="${section_spec#*:}"

    # Check if markers exist
    if ! grep -q "BEGIN:CONSTITUTION:$block_name" "$runbook_file"; then
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
    local section_id="${section_spec%%:*}"
    local block_name="${section_spec#*:}"

    local source_content
    source_content=$(extract_section "$section_spec")
    local injected_content
    injected_content=$(extract_injected_content "$runbook_file" "$block_name")

    echo "=== DIFF: $agent_name - $section_spec ==="
    diff -u <(echo "$source_content") <(echo "$injected_content") | head -20
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
    local total_checks=0
    local passed_checks=0

    echo ""
    echo "VERIFICATION RESULTS:"
    echo "Agent     | Section       | SHA-256                              | Status"
    echo "----------|---------------|--------------------------------------|--------"

    # Process each agent and section
    IFS=',' read -ra SECTION_ARRAY <<< "$SECTIONS"
    for agent in "${agents[@]}"; do
        for section_spec in "${SECTION_ARRAY[@]}"; do
            if verify_equivalence "$agent" "$section_spec"; then
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
            ((passed_checks++))
        else
            ((failed_checks++))
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

        return 1
    fi

    log_ok "All constitution content matches source exactly! ✅"
    return 0
}

# Run main
main "$@"
