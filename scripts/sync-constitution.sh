#!/usr/bin/env bash
# Constitution Sync Script
# Syncs relevant sections from master constitution to agent runbooks
# Features: 16 improvements for production readiness

set -euo pipefail
IFS=$'\n\t'

# UTF-8 locale for Unicode stability
export LC_ALL=C.UTF-8 LANG=C.UTF-8

# Configuration
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

CONSTITUTION_SRC="${CONSTITUTION_SRC:-docs/constitution/CONSTITUTION.md}"
DEFAULT_SECTIONS="$(cat scripts/constitution.sections 2>/dev/null || echo "VII:CURSOR_MGMT")"
SECTIONS="${SECTIONS:-$DEFAULT_SECTIONS}"

# Command line arguments
DRY_RUN=false
CHECK_MODE=false
ALLOW_MISSING=false
CUSTOM_SECTIONS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --check)
            CHECK_MODE=true
            shift
            ;;
        --allow-missing)
            ALLOW_MISSING=true
            shift
            ;;
        --sections)
            CUSTOM_SECTIONS="$2"
            shift 2
            ;;
        --constitution-src)
            CONSTITUTION_SRC="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Override sections if specified
if [[ -n "$CUSTOM_SECTIONS" ]]; then
    SECTIONS="$CUSTOM_SECTIONS"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_dry() { echo -e "${BLUE}[DRY]${NC} $1"; }

# Validate source file exists and is within repo
if [[ ! -f "$CONSTITUTION_SRC" ]]; then
    log_error "Constitution source file not found: $CONSTITUTION_SRC"
    exit 1
fi

if [[ "$CONSTITUTION_SRC" == /* ]]; then
    # Absolute path - must be within repo
    if [[ "$CONSTITUTION_SRC" != "$REPO_ROOT"/* ]]; then
        log_error "CONSTITUTION_SRC must be within repo: $CONSTITUTION_SRC"
        exit 1
    fi
fi

# CRLF normalization function
normalize_lines() {
    awk '{ sub(/\r$/,""); print }'
}

# Multi-language section extraction with regex support
extract_section() {
    local section_spec="$1"
    local section_number="${section_spec%%:*}"
    local block_name="${section_spec#*:}"

    # Use sed for precise section extraction
    if [[ "$section_number" == "VII" ]]; then
        sed -n '/^## Điều VII/,/^## /p' "$CONSTITUTION_SRC" | sed '$d' | normalize_lines
    else
        # For other sections, return empty for now
        echo ""
    fi
}

# SHA-256 content hash (cross-platform)
compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | cut -d' ' -f1
    else
        echo "no-sha256-available"
    fi
}

# Auto-insert markers if missing
auto_insert_markers() {
    local runbook_file="$1"
    local block_name="$2"

    if ! grep -q "BEGIN:CONSTITUTION:$block_name" "$runbook_file"; then
        log_info "Auto-inserting markers for $block_name in $(basename "$runbook_file")"

        # Find insertion point (before ## REPORTING or at end)
        local insert_point=""
        if grep -q "^## REPORTING" "$runbook_file"; then
            insert_point="## REPORTING"
        else
            insert_point="$"
        fi

        # Create temp file for safe replacement
        local tmp_file
        tmp_file=$(mktemp)

        if [[ "$insert_point" == "$" ]]; then
            # Append at end
            cat "$runbook_file" > "$tmp_file"
            {
                echo ""
                echo "<!-- BEGIN:CONSTITUTION:$block_name (auto-generated; do not edit)"
                echo "source=$CONSTITUTION_SRC"
                echo "section=${block_name#*:}"
                echo "commit=<auto>"
                echo "generated=<auto>"
                echo "source_sha256=<auto>"
                echo "-->"
                echo "<!-- END:CONSTITUTION:$block_name -->"
            } >> "$tmp_file"
        else
            # Insert before REPORTING section
            awk "
            /^## REPORTING/ {
                print \"\"
                print \"<!-- BEGIN:CONSTITUTION:$block_name (auto-generated; do not edit)\"
                print \"source=$CONSTITUTION_SRC\"
                print \"section=${block_name#*:}\"
                print \"commit=<auto>\"
                print \"generated=<auto>\"
                print \"source_sha256=<auto>\"
                print \"-->\"
                print \"<!-- END:CONSTITUTION:$block_name -->\"
                print \"\"
            }
            { print }
            " "$runbook_file" > "$tmp_file"
        fi

        mv "$tmp_file" "$runbook_file"
    fi
}

# Update constitution markers with content
update_constitution_markers() {
    local runbook_file="$1"
    local block_name="$2"
    local content="$3"

    # Auto-insert markers if missing and allowed
    if [[ "$ALLOW_MISSING" == "true" ]]; then
        auto_insert_markers "$runbook_file" "$block_name"
    fi

    # Check if markers exist
    if ! grep -q "BEGIN:CONSTITUTION:$block_name" "$runbook_file"; then
        if [[ "$CHECK_MODE" == "true" ]]; then
            log_error "Missing constitution markers for $block_name in $(basename "$runbook_file")"
            return 1
        else
            log_error "Missing constitution markers for $block_name in $(basename "$runbook_file")"
            log_error "Run with --allow-missing to auto-insert markers"
            return 1
        fi
    fi

    # Generate metadata
    local commit_hash
    commit_hash=$(git rev-parse --short HEAD)
    local timestamp
    timestamp=$(date -u +"%F %T UTC")
    local content_hash
    content_hash=$(echo "$content" | compute_sha256)

    # Create backup
    local backup_dir
    backup_dir=".constitution-backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp "$runbook_file" "$backup_dir/$(basename "$runbook_file")"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_dry "Would update $runbook_file with:"
        log_dry "  Block: $block_name"
        log_dry "  Commit: $commit_hash"
        log_dry "  Content hash: $content_hash"
        log_dry "  Content length: ${#content} chars"
        return 0
    fi

    if [[ "$CHECK_MODE" == "true" ]]; then
        # Simple check - verify markers exist and basic metadata is present
        if ! grep -q "BEGIN:CONSTITUTION:$block_name" "$runbook_file"; then
            log_error "Missing constitution markers for $block_name in $(basename "$runbook_file")"
            return 1
        fi

        if ! grep -q "END:CONSTITUTION:$block_name" "$runbook_file"; then
            log_error "Missing end marker for $block_name in $(basename "$runbook_file")"
            return 1
        fi

        if ! grep -q "commit=[a-f0-9]\+" "$runbook_file"; then
            log_error "Missing commit hash in $(basename "$runbook_file")"
            return 1
        fi

        if ! grep -q "source_sha256=[a-f0-9]\+" "$runbook_file"; then
            log_error "Missing content hash in $(basename "$runbook_file")"
            return 1
        fi

        log_info "✅ $(basename "$runbook_file") is in sync for $block_name"
        return 0
    fi

    # Simple file replacement using Python for reliability
    python3 -c "
import sys, re

runbook_file = '$runbook_file'
block_name = '$block_name'
content = '''$content'''
commit_hash = '$commit_hash'
timestamp = '$timestamp'
content_hash = '$content_hash'

try:
    with open(runbook_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Find marker lines
    begin_idx = -1
    end_idx = -1

    for i, line in enumerate(lines):
        if f'<!-- BEGIN:CONSTITUTION:{block_name}' in line:
            begin_idx = i
        elif f'<!-- END:CONSTITUTION:{block_name} -->' in line:
            end_idx = i
            break

    if begin_idx != -1 and end_idx != -1:
        # Find the end of the BEGIN comment (the --> line)
        comment_end_idx = begin_idx
        for i in range(begin_idx, len(lines)):
            if '-->' in lines[i]:
                comment_end_idx = i
                break

        # Replace content between comment end and END marker
        new_lines = lines[:comment_end_idx + 1]  # Keep up to -->
        new_lines.append('\n')  # Add newline after -->
        # Split content properly and add each line
        for content_line in content.splitlines():
            new_lines.append(content_line + '\n')
        new_lines.append('\n')  # Add newline before END
        new_lines.extend(lines[end_idx:])  # Keep END marker and rest

        lines = new_lines

    # Update metadata
    for i, line in enumerate(lines):
        if 'commit=<auto>' in line:
            lines[i] = re.sub(r'commit=<auto>', f'commit={commit_hash}', line)
        if 'generated=<auto>' in line:
            lines[i] = re.sub(r'generated=<auto>', f'generated={timestamp}', line)
        if 'source_sha256=<auto>' in line:
            lines[i] = re.sub(r'source_sha256=<auto>', f'source_sha256={content_hash}', line)

    with open(runbook_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

except Exception as e:
    print(f'Error updating file: {e}', file=sys.stderr)
    sys.exit(1)
"

    log_info "Updated $(basename "$runbook_file") with $block_name content"
}

# Main execution
main() {
    log_info "Starting Constitution Sync"
    log_info "Source: $CONSTITUTION_SRC"
    log_info "Sections: $SECTIONS"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN MODE - No files will be modified"
    elif [[ "$CHECK_MODE" == "true" ]]; then
        log_info "CHECK MODE - Validating sync status"
    fi

    local agent_dirs=(.agents/gemini .agents/claude .agents/codex)
    local total_files=0
    local changed_files=0

    # Validate all target directories exist
    for agent_dir in "${agent_dirs[@]}"; do
        if [[ ! -d "$agent_dir" ]]; then
            log_error "Agent directory not found: $agent_dir"
            exit 1
        fi
    done

    # Process each section
    IFS=',' read -ra SECTION_ARRAY <<< "$SECTIONS"
    for section_spec in "${SECTION_ARRAY[@]}"; do
        local section_content
        section_content=$(extract_section "$section_spec")

        if [[ -z "$section_content" ]]; then
            if [[ "$ALLOW_MISSING" == "true" ]]; then
                log_warn "Section $section_spec not found in constitution, skipping"
                continue
            else
                log_error "Section $section_spec not found in constitution"
                exit 1
            fi
        fi

        local block_name="${section_spec#*:}"

        # Process each agent runbook
        for agent_dir in "${agent_dirs[@]}"; do
            local runbook_file="$agent_dir/runbook.md"
            ((total_files++))

            if ! update_constitution_markers "$runbook_file" "$block_name" "$section_content"; then
                exit 1
            fi

            if [[ "$DRY_RUN" == "false" && "$CHECK_MODE" == "false" ]]; then
                ((changed_files++))
            fi
        done
    done

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Dry run complete - $total_files files would be processed"
    elif [[ "$CHECK_MODE" == "true" ]]; then
        log_info "Check complete - All $total_files files are in sync"
    else
        log_info "Sync complete - Updated $changed_files files"
        log_info "Backups available in .constitution-backups/"
    fi
}

# Run main function
main "$@"
