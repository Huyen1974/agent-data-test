#!/bin/bash
# M5 Fix OIDC Permissions - Helper script to fix missing OIDC permissions in workflows
# Automatically detects workflows missing 'permissions: id-token: write' and fixes them

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi

    if ! command -v awk &> /dev/null; then
        missing_deps+=("awk")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            log_error "  - $dep"
        done
        exit 1
    fi
}

# Get latest preflight report
get_latest_report() {
    local latest_report
    latest_report=$(find governance -name "preflight_M5_*.md" -type f | sort | tail -1)

    if [ -z "$latest_report" ]; then
        log_error "No preflight reports found in governance/ directory"
        log_info "Run 'scripts/m5_preflight_secrets_permissions.sh' first"
        exit 1
    fi

    echo "$latest_report"
}

# Extract workflows missing OIDC permissions from report
extract_missing_oidc_workflows() {
    local report="$1"

    # Extract workflows between "Workflows Missing Required Permissions" and next section
    awk '/^### Workflows Missing Required Permissions/,/^##/ {
        if ($0 ~ /^- ❌ `.*`$/) {
            gsub(/^- ❌ `/, "")
            gsub(/`$/, "")
            print
        }
    }' "$report" | head -n -1 || true
}

# Check if workflow file exists and is writable
check_workflow_file() {
    local workflow_file="$1"

    if [ ! -f "$workflow_file" ]; then
        log_error "Workflow file does not exist: $workflow_file"
        return 1
    fi

    if [ ! -w "$workflow_file" ]; then
        log_error "Workflow file is not writable: $workflow_file"
        return 1
    fi

    return 0
}

# Backup workflow file
backup_workflow() {
    local workflow_file="$1"
    local backup_file="${workflow_file}.backup.$(date +%Y%m%d_%H%M%S)"

    if cp "$workflow_file" "$backup_file"; then
        log_info "Created backup: $backup_file"
        echo "$backup_file"
    else
        log_error "Failed to create backup for: $workflow_file"
        return 1
    fi
}

# Check if workflow already has proper permissions
has_id_token_permission() {
    local workflow_file="$1"

    awk '
        BEGIN{perm=0; has_id_token=0}
        /^[[:space:]]*permissions:[[:space:]]*$/ {perm=1; next}
        perm && /^[[:space:]]*id-token:[[:space:]]*write[[:space:]]*$/ {has_id_token=1}
        /^[[:space:]]*[a-zA-Z_-]+:[[:space:]]*/ && perm==1 && !/^[[:space:]]*id-token:/ && !/^[[:space:]]*contents:/ && !/^[[:space:]]*actions:/ {
            if (!/^[[:space:]]*[a-zA-Z_-]+:[[:space:]]*(read|write|none)[[:space:]]*$/) {
                perm=0
            }
        }
        /^[a-zA-Z_-]+:[[:space:]]*/ && !/^[[:space:]]/ {perm=0}
        END{ exit(has_id_token?0:1) }
    ' "$workflow_file"
}

# Add OIDC permissions to workflow
add_oidc_permissions() {
    local workflow_file="$1"
    local temp_file
    temp_file=$(mktemp)

    log_info "Processing: $workflow_file"

    # Create modified workflow with OIDC permissions
    awk '
        BEGIN {
            found_permissions = 0
            found_jobs = 0
            added_permissions = 0
        }

        # Check if permissions block already exists
        /^permissions:[[:space:]]*$/ {
            found_permissions = 1
            print $0
            next
        }

        # If in permissions block, check for id-token
        found_permissions && /^[[:space:]]*[a-zA-Z_-]+:[[:space:]]*(read|write|none)[[:space:]]*$/ {
            print $0
            if ($0 ~ /id-token:/) {
                # Replace existing id-token permission
                gsub(/id-token:[[:space:]]*(read|none)/, "id-token: write")
            }
            next
        }

        # End of permissions block, add id-token if not found
        found_permissions && /^[a-zA-Z_-]+:[[:space:]]*/ && !/^[[:space:]]/ {
            if (!added_permissions) {
                print "  id-token: write"
                added_permissions = 1
            }
            found_permissions = 0
            print $0
            next
        }

        # If jobs section found and no permissions block exists, add it
        /^jobs:[[:space:]]*$/ && !found_permissions && !added_permissions {
            print "permissions:"
            print "  id-token: write"
            print "  contents: read"
            print ""
            print $0
            added_permissions = 1
            next
        }

        # Default: print line as-is
        {
            print $0
        }

        END {
            # If permissions block was found but id-token not added, add it
            if (found_permissions && !added_permissions) {
                print "  id-token: write"
            }
        }
    ' "$workflow_file" > "$temp_file"

    # Verify the modification was successful
    if [ -s "$temp_file" ]; then
        if mv "$temp_file" "$workflow_file"; then
            log_success "Added OIDC permissions to: $workflow_file"
            return 0
        else
            log_error "Failed to update workflow file: $workflow_file"
            rm -f "$temp_file"
            return 1
        fi
    else
        log_error "Generated empty file for: $workflow_file"
        rm -f "$temp_file"
        return 1
    fi
}

# Show diff for manual review
show_workflow_diff() {
    local workflow_file="$1"
    local backup_file="$2"

    log_info "Changes made to $workflow_file:"
    echo "----------------------------------------"

    if command -v diff &> /dev/null; then
        diff -u "$backup_file" "$workflow_file" || true
    else
        echo "diff command not available, showing before/after:"
        echo "BEFORE:"
        grep -A 5 -B 5 "permissions:" "$backup_file" 2>/dev/null || echo "No permissions block found"
        echo "AFTER:"
        grep -A 5 -B 5 "permissions:" "$workflow_file" 2>/dev/null || echo "No permissions block found"
    fi

    echo "----------------------------------------"
}

# Validate workflow syntax
validate_workflow_syntax() {
    local workflow_file="$1"

    # Basic YAML syntax check using awk
    if awk '
        BEGIN { errors = 0 }
        /^[[:space:]]*- / {
            # Check for proper list item indentation
            if (match($0, /^[[:space:]]*/)) {
                indent = RLENGTH
                if (indent % 2 != 0) {
                    print "Warning: Odd indentation at line " NR ": " $0
                }
            }
        }
        /^[a-zA-Z_-]+:[[:space:]]*$/ {
            # Top-level keys should not be indented
            if (match($0, /^[[:space:]]+/)) {
                print "Error: Top-level key should not be indented at line " NR ": " $0
                errors++
            }
        }
        END { exit(errors > 0 ? 1 : 0) }
    ' "$workflow_file"; then
        log_success "Workflow syntax validation passed: $workflow_file"
        return 0
    else
        log_warn "Workflow syntax validation failed: $workflow_file"
        return 1
    fi
}

# Interactive mode for fixing workflows
fix_workflow_interactive() {
    local workflow_file="$1"

    echo
    log_info "Workflow: $workflow_file"

    # Check if already has proper permissions
    if has_id_token_permission "$workflow_file"; then
        log_success "Already has proper OIDC permissions"
        return 0
    fi

    # Show current permissions block
    log_info "Current permissions block:"
    grep -A 10 -B 2 "permissions:" "$workflow_file" 2>/dev/null || echo "No permissions block found"

    echo
    read -p "Fix this workflow? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Skipping $workflow_file"
        return 0
    fi

    # Create backup
    local backup_file
    if ! backup_file=$(backup_workflow "$workflow_file"); then
        return 1
    fi

    # Apply fix
    if add_oidc_permissions "$workflow_file"; then
        # Validate syntax
        if validate_workflow_syntax "$workflow_file"; then
            show_workflow_diff "$workflow_file" "$backup_file"
            echo
            read -p "Keep these changes? (Y/n): " -r
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                mv "$backup_file" "$workflow_file"
                log_info "Reverted changes to $workflow_file"
            else
                rm -f "$backup_file"
                log_success "Applied changes to $workflow_file"
            fi
        else
            log_error "Syntax validation failed, reverting changes"
            mv "$backup_file" "$workflow_file"
            return 1
        fi
    else
        log_error "Failed to add permissions"
        return 1
    fi
}

# Batch mode for fixing all workflows
fix_workflows_batch() {
    local workflows=("$@")
    local fixed_count=0
    local failed_count=0

    for workflow_file in "${workflows[@]}"; do
        log_info "Processing: $workflow_file"

        if ! check_workflow_file "$workflow_file"; then
            ((failed_count++))
            continue
        fi

        if has_id_token_permission "$workflow_file"; then
            log_success "Already has proper OIDC permissions: $workflow_file"
            continue
        fi

        # Create backup
        local backup_file
        if ! backup_file=$(backup_workflow "$workflow_file"); then
            ((failed_count++))
            continue
        fi

        # Apply fix
        if add_oidc_permissions "$workflow_file" && validate_workflow_syntax "$workflow_file"; then
            log_success "Fixed OIDC permissions: $workflow_file"
            rm -f "$backup_file"
            ((fixed_count++))
        else
            log_error "Failed to fix: $workflow_file"
            mv "$backup_file" "$workflow_file"
            ((failed_count++))
        fi
    done

    echo
    log_info "Batch processing completed:"
    log_info "  Fixed: $fixed_count workflows"
    log_info "  Failed: $failed_count workflows"
}

# Main function
main() {
    log_info "M5 Fix OIDC Permissions Helper"
    echo

    check_dependencies

    # Get latest preflight report
    local report
    report=$(get_latest_report)
    log_info "Using report: $report"

    # Extract workflows missing OIDC permissions
    local missing_workflows
    missing_workflows=$(extract_missing_oidc_workflows "$report")

    if [ -z "$missing_workflows" ]; then
        log_success "No workflows missing OIDC permissions found in latest report!"
        exit 0
    fi

    echo
    log_info "Workflows missing OIDC permissions:"
    while IFS= read -r workflow; do
        [ -n "$workflow" ] && log_warn "  - $workflow"
    done <<< "$missing_workflows"
    echo

    # Convert to array
    local workflows_array=()
    while IFS= read -r workflow; do
        [ -n "$workflow" ] && workflows_array+=("$workflow")
    done <<< "$missing_workflows"

    # Choose mode
    if [ "${BATCH_MODE:-false}" = "true" ]; then
        fix_workflows_batch "${workflows_array[@]}"
    else
        echo "How would you like to fix missing OIDC permissions?"
        echo "1) Interactive mode (review each workflow)"
        echo "2) Batch mode (fix all automatically)"
        echo "3) Manual instructions only"
        echo "4) Exit"

        read -p "Choose option (1-4): " -r choice

        case "$choice" in
            1)
                log_info "Starting interactive mode..."
                for workflow in "${workflows_array[@]}"; do
                    fix_workflow_interactive "$workflow"
                done
                ;;
            2)
                log_info "Starting batch mode..."
                fix_workflows_batch "${workflows_array[@]}"
                ;;
            3)
                echo
                log_info "Manual fix instructions:"
                echo "Add the following permissions block to each workflow:"
                echo
                echo "permissions:"
                echo "  id-token: write"
                echo "  contents: read"
                echo
                echo "Workflows to fix:"
                for workflow in "${workflows_array[@]}"; do
                    echo "  - $workflow"
                done
                echo
                ;;
            4)
                log_info "Exiting..."
                exit 0
                ;;
            *)
                log_error "Invalid choice"
                exit 1
                ;;
        esac
    fi

    echo
    log_info "OIDC permissions fix completed!"
    log_info "Run the preflight check again to verify:"
    log_info "  scripts/m5_preflight_secrets_permissions.sh"
}

# Show help
show_help() {
    cat << EOF
M5 Fix OIDC Permissions Helper

DESCRIPTION:
    Helper script to fix missing OIDC permissions in workflows identified
    by M5 preflight check. Automatically adds 'permissions: id-token: write'
    to workflows that use cloud authentication.

USAGE:
    $0 [options]

OPTIONS:
    -h, --help      Show this help message
    -b, --batch     Run in batch mode (fix all automatically)
    -m, --manual    Show manual instructions only

REQUIREMENTS:
    - Latest M5 preflight report in governance/
    - Write access to workflow files
    - git for file operations

EXAMPLES:
    $0                  # Interactive mode
    $0 --batch          # Batch mode (fix all)
    $0 --manual         # Manual instructions only

For more information, see: docs/M5_PREFLIGHT_SECRETS_PERMISSIONS.md
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--batch)
            BATCH_MODE=true
            shift
            ;;
        -m|--manual)
            MANUAL_MODE=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run appropriate mode
if [ "${MANUAL_MODE:-false}" = "true" ]; then
    report=$(get_latest_report)
    missing_workflows=$(extract_missing_oidc_workflows "$report")

    if [ -z "$missing_workflows" ]; then
        log_success "No workflows missing OIDC permissions found!"
        exit 0
    fi

    log_info "Manual fix instructions for workflows missing OIDC permissions:"
    echo
    echo "Add this permissions block to each workflow (before jobs section):"
    echo
    echo "permissions:"
    echo "  id-token: write"
    echo "  contents: read"
    echo
    echo "Workflows to fix:"
    while IFS= read -r workflow; do
        [ -n "$workflow" ] && echo "  - $workflow"
    done <<< "$missing_workflows"
else
    main "$@"
fi
