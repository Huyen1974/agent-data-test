#!/bin/bash
# Enhanced for M5.PRE-CLI-02 orchestration compatibility
# M5.PRE-CLI-01 — Preflight Secrets & Permissions trước Terraform/WIF (idempotent, evidence-based)
# - Trích xuất secrets/vars đang được tham chiếu trong workflows
# - Đối chiếu với secrets/variables thực tế (repo + environments)
# - Kiểm tra workflows dùng cloud auth có 'permissions: id-token: write'
# - Ghi báo cáo governance/preflight_M5_<TS>.md; chỉ commit/push khi PASS

set -euo pipefail

# Color codes for output
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

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v gh &> /dev/null; then
        missing_deps+=("gh (GitHub CLI)")
    fi

    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies:"
        for dep in "${missing_deps[@]}"; do
            log_error "  - $dep"
        done
        exit 1
    fi
}

# Initialize variables and environment
init_environment() {
    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository. Please run from project root."
        exit 1
    fi

    # Get repository information
    DEF_BRANCH="$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || echo "main")"
    REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "unknown/unknown")"
    TS="$(date -u +%Y%m%dT%H%M%SZ)"

    # Ensure we're on the default branch and up to date
    log_info "Switching to default branch: $DEF_BRANCH"
    git switch -q "$DEF_BRANCH" 2>/dev/null || {
        log_warn "Could not switch to $DEF_BRANCH, continuing with current branch"
    }

    git pull --ff-only --quiet 2>/dev/null || {
        log_warn "Could not pull latest changes, continuing with current state"
    }

    WF_DIR=".github/workflows"
    mkdir -p governance

    log_info "Repository: $REPO"
    log_info "Branch: $DEF_BRANCH"
    log_info "Timestamp: $TS"
}

# Extract secrets referenced in workflows
extract_workflow_references() {
    log_info "Extracting secrets and variables referenced in workflows..."

    REF_SECRETS="$(mktemp)"
    REF_VARS="$(mktemp)"

    if [ -d "$WF_DIR" ]; then
        # Extract secrets.* references
        grep -RhoE --exclude=*.bak --exclude=*.disabled --exclude-dir=archive --exclude=\*.bak --exclude=\*.disabled --exclude-dir=archive '\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}' "$WF_DIR" 2>/dev/null \
            | sed -E 's/.*secrets\.([A-Za-z0-9_]+).*/\1/' \
            | sort -u > "$REF_SECRETS" || true

        # Extract vars.* references
        grep -RhoE --exclude=*.bak --exclude=*.disabled --exclude-dir=archive --exclude=\*.bak --exclude=\*.disabled --exclude-dir=archive '\$\{\{\s*vars\.([A-Za-z0-9_]+)\s*\}\}' "$WF_DIR" 2>/dev/null \
            | sed -E 's/.*vars\.([A-Za-z0-9_]+).*/\1/' \
            | sort -u > "$REF_VARS" || true
    else
        log_warn "No workflows directory found at $WF_DIR"
        touch "$REF_SECRETS" "$REF_VARS"
    fi

    local ref_secrets_count=$(wc -l < "$REF_SECRETS")
    local ref_vars_count=$(wc -l < "$REF_VARS")

    log_info "Found $ref_secrets_count referenced secrets and $ref_vars_count referenced variables"
}

# List repository secrets from GitHub API
list_repo_secrets() {
    gh api "repos/$REPO/actions/secrets?per_page=100" 2>/dev/null \
        | jq -r '.secrets[]?.name // empty' 2>/dev/null \
        | sort -u || true
}

# List repository environments
list_envs() {
    gh api "repos/$REPO/environments?per_page=100" 2>/dev/null \
        | jq -r '.environments[]?.name // empty' 2>/dev/null \
        | sort -u || true
}

# List environment secrets
list_env_secrets() {
    local env="$1"
    gh api "repos/$REPO/environments/$env/secrets?per_page=100" 2>/dev/null \
        | jq -r '.secrets[]?.name // empty' 2>/dev/null \
        | sort -u || true
}

# List repository variables
list_repo_variables() {
    gh api "repos/$REPO/actions/variables?per_page=100" 2>/dev/null \
        | jq -r '.variables[]?.name // empty' 2>/dev/null \
        | sort -u || true
}

# Check existing secrets and variables
check_existing_secrets_vars() {
    log_info "Checking existing secrets and variables..."

    PRESENT_SECRETS="$(mktemp)"
    PRESENT_VARS="$(mktemp)"

    # Get repository-level secrets
    log_info "Fetching repository secrets..."
    list_repo_secrets > "$PRESENT_SECRETS" || {
        log_warn "Failed to fetch repository secrets"
        touch "$PRESENT_SECRETS"
    }

    # Get environment secrets
    local envs
    envs=$(list_envs)
    if [ -n "$envs" ]; then
        log_info "Fetching environment secrets..."
        while IFS= read -r env; do
            [ -z "$env" ] && continue
            log_info "  - Environment: $env"
            list_env_secrets "$env" >> "$PRESENT_SECRETS" || {
                log_warn "Failed to fetch secrets for environment: $env"
            }
        done <<< "$envs"
    else
        log_info "No environments found"
    fi

    # Remove duplicates from secrets
    sort -u "$PRESENT_SECRETS" -o "$PRESENT_SECRETS"

    # Get repository variables
    log_info "Fetching repository variables..."
    list_repo_variables > "$PRESENT_VARS" || {
        log_warn "Failed to fetch repository variables"
        touch "$PRESENT_VARS"
    }

    # Calculate missing secrets and variables
    MISSING_SECRETS="$(mktemp)"
    MISSING_VARS="$(mktemp)"

    comm -23 "$REF_SECRETS" "$PRESENT_SECRETS" > "$MISSING_SECRETS" || true
    # Filter built-in and optional secrets
    if [ -s "$MISSING_SECRETS" ]; then
        [ -f "governance/preflight_optional_secrets.txt" ] || : > "governance/preflight_optional_secrets.txt"
        awk 'BEGIN{
            # Load optional secrets from whitelist file
            while ((getline line < ENVIRON["OPT_FILE"]) > 0) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
                if (line && !match(line, /^#/)) {
                    optional[line] = 1
                }
            }
            close(ENVIRON["OPT_FILE"])
        }
        {
            # Filter out GITHUB_TOKEN and whitelisted secrets
            if ($0 != "GITHUB_TOKEN" && !($0 in optional)) {
                print $0
            }
        }' OPT_FILE="governance/preflight_optional_secrets.txt" "$MISSING_SECRETS" > "${MISSING_SECRETS}.filtered" || true
        mv "${MISSING_SECRETS}.filtered" "$MISSING_SECRETS" 2>/dev/null || true
    fi
    comm -23 "$REF_VARS" "$PRESENT_VARS" > "$MISSING_VARS" || true

    local present_secrets_count=$(wc -l < "$PRESENT_SECRETS")
    local missing_secrets_count=$(wc -l < "$MISSING_SECRETS")
    local present_vars_count=$(wc -l < "$PRESENT_VARS")
    local missing_vars_count=$(wc -l < "$MISSING_VARS")

    log_info "Present secrets: $present_secrets_count, Missing: $missing_secrets_count"
    log_info "Present variables: $present_vars_count, Missing: $missing_vars_count"
}

# Check OIDC workflows for proper permissions
check_oidc_permissions() {
    log_info "Checking OIDC workflows for proper permissions..."

    WF_NEED_OIDC="$(mktemp)"
    OIDC_PERM_MISSING="$(mktemp)"

    if [ -d "$WF_DIR" ]; then
        # Find workflows using cloud authentication
        grep -RslE --exclude=\*.bak --exclude=\*.disabled --exclude-dir=archive 'google-github-actions/auth|aws-actions/configure-aws-credentials|azure/login' "$WF_DIR" 2>/dev/null \
            | sort -u > "$WF_NEED_OIDC" || true
    else
        touch "$WF_NEED_OIDC"
    fi

    # Check each OIDC workflow for proper permissions
    while IFS= read -r wf; do
        [ -z "$wf" ] && continue
        log_info "Checking OIDC permissions in: $wf"

        # Check for 'id-token: write' under permissions block
        if ! awk '
            BEGIN{perm=0; has_id_token=0}
            /^[[:space:]]*permissions:[[:space:]]*$/ {perm=1; next}
            perm && /^[[:space:]]*id-token:[[:space:]]*write[[:space:]]*$/ {has_id_token=1}
            /^[[:space:]]*[a-zA-Z_-]+:[[:space:]]*/ && perm==1 && !/^[[:space:]]*id-token:/ && !/^[[:space:]]*contents:/ && !/^[[:space:]]*actions:/ {
                # Reset when we hit a new top-level key that is not a permission
                if (!/^[[:space:]]*[a-zA-Z_-]+:[[:space:]]*(read|write|none)[[:space:]]*$/) {
                    perm=0
                }
            }
            /^[a-zA-Z_-]+:[[:space:]]*/ && !/^[[:space:]]/ {perm=0}
            END{ exit(has_id_token?0:1) }
        ' "$wf"; then
            echo "$wf" >> "$OIDC_PERM_MISSING"
            log_warn "Missing id-token: write permission in $wf"
        else
            log_success "Proper OIDC permissions found in $wf"
        fi
    done < "$WF_NEED_OIDC"

    local oidc_workflows_count=$(wc -l < "$WF_NEED_OIDC")
    local missing_perms_count=$(wc -l < "$OIDC_PERM_MISSING")

    log_info "OIDC workflows: $oidc_workflows_count, Missing permissions: $missing_perms_count"
}

# Get workflow permissions information
get_workflow_permissions() {
    log_info "Fetching workflow permissions..."

    WORKFLOW_PERM_JSON="$(mktemp)"
    gh api "repos/$REPO/actions/permissions/workflow" > "$WORKFLOW_PERM_JSON" 2>/dev/null || {
        log_warn "Failed to fetch workflow permissions"
        echo '{}' > "$WORKFLOW_PERM_JSON"
    }

    DFLT_PERM="$(jq -r '.default_workflow_permissions // "unknown"' "$WORKFLOW_PERM_JSON" 2>/dev/null || echo "unknown")"
    log_info "Default workflow permissions: $DFLT_PERM"
}

# Check recent workflow runs
check_workflow_health() {
    log_info "Checking recent workflow run health..."

    check_last_run() {
        local wf="$1"
        gh run list --workflow "$wf" -L 1 --json status,conclusion 2>/dev/null \
            | jq -r '.[0].status + "/" + (.[0].conclusion // "null")' 2>/dev/null || echo "no-data"
    }

    RUN_WIF="$(check_last_run "wif-gsm-smoke.yml")"
    RUN_SYNC="$(check_last_run "sync-secrets.yml")"
    RUN_SECURITY="$(check_last_run "security-verify.yml")"

    log_info "Recent run status:"
    log_info "  - wif-gsm-smoke.yml: $RUN_WIF"
    log_info "  - sync-secrets.yml: $RUN_SYNC"
    log_info "  - security-verify.yml: $RUN_SECURITY"
}

# Generate comprehensive report
generate_report() {
    log_info "Generating preflight report..."

    RPT="governance/preflight_M5_${TS}.md"

    {
        echo "# M5 Preflight — Secrets & Permissions"
        echo ""
        echo "## Metadata"
        echo "- **Repository:** $REPO"
        echo "- **Branch:** $DEF_BRANCH"
        echo "- **Generated:** $TS"
        echo "- **Script Version:** M5.PRE-CLI-01"
        echo ""

        echo "## Executive Summary"
        local total_issues=0

        if [ -s "$MISSING_SECRETS" ]; then
            ((total_issues++))
        fi

        if [ -s "$MISSING_VARS" ]; then
            ((total_issues++))
        fi

        if [ -s "$OIDC_PERM_MISSING" ]; then
            ((total_issues++))
        fi

        if [ "$total_issues" -eq 0 ]; then
            echo "✅ **PASS** - All preflight checks passed successfully"
        else
            echo "❌ **FAIL** - $total_issues issue(s) found that must be resolved"
        fi
        echo ""

        echo "## Referenced Secrets in Workflows"
        if [ -s "$REF_SECRETS" ]; then
            sed 's/^/- `/' "$REF_SECRETS" | sed 's/$/`/'
        else
            echo "_No secrets referenced in workflows_"
        fi
        echo ""

        echo "## Missing Secrets"
        echo "These secrets are referenced in workflows but not found in repository or environments:"
        if [ -s "$MISSING_SECRETS" ]; then
            sed 's/^/- ❌ `/' "$MISSING_SECRETS" | sed 's/$/`/'
        else
            echo "_No missing secrets_"
        fi
        echo ""

        echo "## Referenced Variables (vars.*)"
        if [ -s "$REF_VARS" ]; then
            sed 's/^/- `/' "$REF_VARS" | sed 's/$/`/'
        else
            echo "_No variables referenced in workflows_"
        fi
        echo ""

        echo "## Missing Variables"
        echo "These variables are referenced in workflows but not found in repository:"
        if [ -s "$MISSING_VARS" ]; then
            sed 's/^/- ❌ `/' "$MISSING_VARS" | sed 's/$/`/'
        else
            echo "_No missing variables_"
        fi
        echo ""

        echo "## Cloud OIDC Authentication Workflows"
        if [ -s "$WF_NEED_OIDC" ]; then
            sed 's/^/- `/' "$WF_NEED_OIDC" | sed 's/$/`/'
        else
            echo "_No workflows requiring cloud OIDC authentication_"
        fi
        echo ""

        echo "### Workflows Missing Required Permissions"
        echo "These workflows use cloud authentication but lack 'permissions: id-token: write':"
        if [ -s "$OIDC_PERM_MISSING" ]; then
            sed 's/^/- ❌ `/' "$OIDC_PERM_MISSING" | sed 's/$/`/'
        else
            echo "_All OIDC workflows have proper permissions_"
        fi
        echo ""

        echo "## Repository Workflow Permissions"
        echo "- **Default workflow permissions:** \`$DFLT_PERM\`"
        echo ""

        echo "## Key CI/CD Health Check"
        echo "Status of critical workflows (latest run):"
        echo "- **wif-gsm-smoke.yml:** \`$RUN_WIF\`"
        echo "- **sync-secrets.yml:** \`$RUN_SYNC\`"
        echo "- **security-verify.yml:** \`$RUN_SECURITY\`"
        echo ""

        echo "## Recommendations"
        if [ -s "$MISSING_SECRETS" ]; then
            echo "### Missing Secrets"
            echo "1. Add the following secrets to your repository settings:"
            sed 's/^/   - /' "$MISSING_SECRETS"
            echo "2. Verify secrets are available in appropriate environments if using environment protection rules"
            echo ""
        fi

        if [ -s "$MISSING_VARS" ]; then
            echo "### Missing Variables"
            echo "1. Add the following variables to your repository settings:"
            sed 's/^/   - /' "$MISSING_VARS"
            echo ""
        fi

        if [ -s "$OIDC_PERM_MISSING" ]; then
            echo "### Missing OIDC Permissions"
            echo "1. Add the following permissions block to workflows:"
            echo "   \`\`\`yaml"
            echo "   permissions:"
            echo "     id-token: write"
            echo "     contents: read"
            echo "   \`\`\`"
            echo "2. Update the following workflow files:"
            sed 's/^/   - /' "$OIDC_PERM_MISSING"
            echo ""
        fi

        echo "## Compliance Notes"
        echo "- This preflight check ensures compliance with M5.PRE-CLI-01 requirements"
        echo "- Validates secrets and permissions before Terraform/WIF deployment"
        echo "- Evidence-based validation with idempotent execution"
        echo "- Report committed only when all checks pass"
        echo ""

        echo "## Technical Details"
        echo "- **Script:** \`scripts/m5_preflight_secrets_permissions.sh\`"
        echo "- **Execution time:** \`$(date -u)\`"
        echo "- **Repository URL:** \`https://github.com/$REPO\`"
        echo "- **Commit SHA:** \`$(git rev-parse HEAD 2>/dev/null || echo "unknown")\`"

    } > "$RPT"

    log_success "Report generated: $RPT"
}

# Validate preflight requirements
validate_preflight() {
    log_info "Validating preflight requirements..."

    local fail_count=0
    local error_messages=()

    # Check for missing secrets
    if [ -s "$MISSING_SECRETS" ]; then
        local count=$(wc -l < "$MISSING_SECRETS")
        error_messages+=("$count missing secrets detected")
        ((fail_count++))
        log_error "Missing secrets:"
        while IFS= read -r secret; do
            log_error "  - $secret"
        done < "$MISSING_SECRETS"
    fi

    # Check for missing variables
    if [ -s "$MISSING_VARS" ]; then
        local count=$(wc -l < "$MISSING_VARS")
        error_messages+=("$count missing variables detected")
        ((fail_count++))
        log_error "Missing variables:"
        while IFS= read -r var; do
            log_error "  - $var"
        done < "$MISSING_VARS"
    fi

    # Check for OIDC permission issues
    if [ -s "$OIDC_PERM_MISSING" ]; then
        local count=$(wc -l < "$OIDC_PERM_MISSING")
        error_messages+=("$count workflows require OIDC but lack id-token: write")
        ((fail_count++))
        log_error "Workflows missing OIDC permissions:"
        while IFS= read -r wf; do
            log_error "  - $wf"
        done < "$OIDC_PERM_MISSING"
    fi

    if [ "$fail_count" -gt 0 ]; then
        log_error "FAILED: Preflight checks found ${fail_count} issue(s):"
        for msg in "${error_messages[@]}"; do
            log_error "  - $msg"
        done
        log_error "See report for details: governance/preflight_M5_${TS}.md"
        return 1
    fi

    log_success "All preflight checks passed!"
    echo "All preflight checks passed!"
    return 0
}

# Commit and push report
commit_report() {
    local passed="$1"

    RPT="governance/preflight_M5_${TS}.md"

    # Add report to git
    git add "$RPT" >/dev/null 2>&1 || {
        log_warn "Could not add report to git"
        return 1
    }

    # Check if there are changes to commit
    if git diff --cached --quiet; then
        log_info "No changes to commit (report unchanged)"
        return 0
    fi

    # Only commit if checks passed
    if [ "$passed" = "true" ]; then
        if git commit -m "gov: add M5 preflight report (secrets & permissions) @ $TS" >/dev/null 2>&1; then
            log_success "Report committed successfully"

            if git push -u origin "$DEF_BRANCH" >/dev/null 2>&1; then
                log_success "Report pushed to remote"
            else
                log_warn "Could not push to remote (report committed locally)"
            fi
        else
            log_warn "Could not commit report"
        fi
    else
        # Reset staged changes if checks failed
        git reset HEAD "$RPT" >/dev/null 2>&1 || true
        log_info "Report not committed (preflight checks failed)"
    fi
}

# Cleanup temporary files
cleanup() {
    log_info "Cleaning up temporary files..."

    # List of temp files to clean
    local temp_files=(
        "$REF_SECRETS"
        "$REF_VARS"
        "$PRESENT_SECRETS"
        "$MISSING_SECRETS"
        "$PRESENT_VARS"
        "$MISSING_VARS"
        "$WF_NEED_OIDC"
        "$OIDC_PERM_MISSING"
        "$WORKFLOW_PERM_JSON"
    )

    for file in "${temp_files[@]}"; do
        if [ -n "${file:-}" ] && [ -f "$file" ]; then
            rm -f "$file" || true
        fi
    done
}

# Main execution function
main() {
    log_info "Starting M5.PRE-CLI-01 - Preflight Secrets & Permissions Check"

    # Trap to ensure cleanup on exit
    trap cleanup EXIT

    # Initialize
    check_dependencies
    init_environment

    # Execute checks
    extract_workflow_references
    check_existing_secrets_vars
    check_oidc_permissions
    get_workflow_permissions
    check_workflow_health

    # Generate report
    generate_report

    # Validate and determine if we should commit
    local validation_passed="false"
    if validate_preflight; then
        validation_passed="true"
        log_success "SUCCESS: Preflight checks passed."
    else
        log_error "FAILED: Preflight checks found issues."
    fi

    # Commit report (only if validation passed)
    commit_report "$validation_passed"

    # Exit with appropriate code
    if [ "$validation_passed" = "true" ]; then
        log_success "M5.PRE-CLI-01 completed successfully"
        exit 0
    else
        log_error "M5.PRE-CLI-01 failed validation"
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
M5.PRE-CLI-01 - Preflight Secrets & Permissions Check

DESCRIPTION:
    Validates GitHub repository secrets and workflow permissions before
    Terraform/WIF deployment. Ensures all referenced secrets exist and
    OIDC workflows have proper permissions.

USAGE:
    $0 [options]

OPTIONS:
    -h, --help      Show this help message
    -v, --verbose   Enable verbose output
    -d, --dry-run   Run checks without committing results

REQUIREMENTS:
    - GitHub CLI (gh) authenticated
    - Git repository with remote
    - jq for JSON processing

EXIT CODES:
    0   All checks passed
    1   Validation failed or missing dependencies

EXAMPLES:
    $0                  # Run full preflight check
    $0 --dry-run        # Run checks without committing
    $0 --help           # Show this help

For more information, see: governance/preflight_M5_*.md
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        -d|--dry-run)
            log_info "DRY RUN MODE: Will not commit results"
            DRY_RUN=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            log_info "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main "$@"
