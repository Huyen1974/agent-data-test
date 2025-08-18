#!/bin/bash
# M5 Fix Missing Secrets - Helper script to address missing secrets from preflight report
# Automatically detects missing secrets and provides guided fixes

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

    if ! command -v gh &> /dev/null; then
        missing_deps+=("gh (GitHub CLI)")
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

# Extract missing secrets from report
extract_missing_secrets() {
    local report="$1"

    # Extract secrets between "Missing Secrets" and next section
    awk '/^## Missing Secrets/,/^##/ {
        if ($0 ~ /^- ❌ `.*`$/) {
            gsub(/^- ❌ `/, "")
            gsub(/`$/, "")
            print
        }
    }' "$report" | head -n -1 || true
}

# Check if secret exists in repository
check_secret_exists() {
    local secret_name="$1"
    local repo
    repo="$(gh repo view --json nameWithOwner -q .nameWithOwner)"

    gh api "repos/$repo/actions/secrets/$secret_name" &>/dev/null
}

# Get secret type suggestion
get_secret_type() {
    local secret_name="$1"

    case "$secret_name" in
        *API_KEY*|*TOKEN*|*SECRET*)
            echo "API Key/Token"
            ;;
        *PROJECT*|*ID*)
            echo "Project/Resource ID"
            ;;
        *URL*|*ENDPOINT*)
            echo "Service URL/Endpoint"
            ;;
        *WEBHOOK*)
            echo "Webhook URL"
            ;;
        *)
            echo "Secret Value"
            ;;
    esac
}

# Get secret description
get_secret_description() {
    local secret_name="$1"

    case "$secret_name" in
        "OPENAI_API_KEY")
            echo "OpenAI API key for AI model access"
            ;;
        "SLACK_WEBHOOK_URL")
            echo "Slack webhook URL for notifications"
            ;;
        "GCP_PROJECT_ID")
            echo "Google Cloud Project ID"
            ;;
        "GCP_SERVICE_ACCOUNT")
            echo "Google Cloud Service Account email"
            ;;
        "GCP_WIF_PROVIDER")
            echo "Google Cloud Workload Identity Federation Provider"
            ;;
        "GITHUB_TOKEN")
            echo "GitHub Personal Access Token (usually auto-provided)"
            ;;
        "QDRANT_CLUSTER1_KEY")
            echo "Qdrant cluster API key"
            ;;
        "QDRANT_CLUSTER1_ID")
            echo "Qdrant cluster ID"
            ;;
        *)
            echo "Required secret for workflow functionality"
            ;;
    esac
}

# Interactive secret addition
add_secret_interactive() {
    local secret_name="$1"
    local secret_type
    local secret_desc

    secret_type=$(get_secret_type "$secret_name")
    secret_desc=$(get_secret_description "$secret_name")

    echo
    log_info "Setting up secret: $secret_name"
    log_info "Type: $secret_type"
    log_info "Description: $secret_desc"
    echo

    # Special handling for GITHUB_TOKEN
    if [ "$secret_name" = "GITHUB_TOKEN" ]; then
        log_warn "GITHUB_TOKEN is usually provided automatically by GitHub Actions"
        log_warn "You may not need to add this manually. Check your workflow configuration."
        echo
        read -p "Do you want to add this secret anyway? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping GITHUB_TOKEN"
            return 0
        fi
    fi

    echo "Please enter the value for $secret_name:"
    echo "(The input will be hidden for security)"
    read -s -p "Secret value: " secret_value
    echo

    if [ -z "$secret_value" ]; then
        log_warn "Empty value provided, skipping $secret_name"
        return 0
    fi

    # Confirm before adding
    echo
    log_info "Ready to add secret: $secret_name"
    read -p "Confirm adding this secret? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Skipping $secret_name"
        return 0
    fi

    # Add the secret
    if echo "$secret_value" | gh secret set "$secret_name"; then
        log_success "Successfully added secret: $secret_name"
    else
        log_error "Failed to add secret: $secret_name"
        return 1
    fi
}

# Batch mode for common secrets
setup_common_secrets() {
    log_info "Setting up common secrets in batch mode..."

    local common_secrets=(
        "GCP_PROJECT_ID:Google Cloud Project ID"
        "GCP_SERVICE_ACCOUNT:Service Account Email"
        "GCP_WIF_PROVIDER:Workload Identity Provider"
        "OPENAI_API_KEY:OpenAI API Key"
        "QDRANT_CLUSTER1_KEY:Qdrant API Key"
        "QDRANT_CLUSTER1_ID:Qdrant Cluster ID"
    )

    for secret_def in "${common_secrets[@]}"; do
        local secret_name="${secret_def%%:*}"
        local secret_desc="${secret_def##*:}"

        if check_secret_exists "$secret_name"; then
            log_success "$secret_name already exists"
            continue
        fi

        echo
        log_info "Setting up: $secret_name"
        log_info "Description: $secret_desc"

        read -s -p "Enter value for $secret_name (or press Enter to skip): " secret_value
        echo

        if [ -n "$secret_value" ]; then
            if echo "$secret_value" | gh secret set "$secret_name"; then
                log_success "Added: $secret_name"
            else
                log_error "Failed to add: $secret_name"
            fi
        else
            log_info "Skipped: $secret_name"
        fi
    done
}

# Main function
main() {
    log_info "M5 Fix Missing Secrets Helper"
    echo

    check_dependencies

    # Get latest preflight report
    local report
    report=$(get_latest_report)
    log_info "Using report: $report"

    # Extract missing secrets
    local missing_secrets
    missing_secrets=$(extract_missing_secrets "$report")

    if [ -z "$missing_secrets" ]; then
        log_success "No missing secrets found in latest report!"
        exit 0
    fi

    echo
    log_info "Missing secrets found:"
    while IFS= read -r secret; do
        [ -n "$secret" ] && log_warn "  - $secret"
    done <<< "$missing_secrets"
    echo

    # Choose mode
    echo "How would you like to fix missing secrets?"
    echo "1) Interactive mode (guided setup for each secret)"
    echo "2) Batch mode (common secrets only)"
    echo "3) Manual instructions only"
    echo "4) Exit"

    read -p "Choose option (1-4): " -r choice

    case "$choice" in
        1)
            log_info "Starting interactive mode..."
            while IFS= read -r secret; do
                [ -n "$secret" ] && add_secret_interactive "$secret"
            done <<< "$missing_secrets"
            ;;
        2)
            setup_common_secrets
            ;;
        3)
            echo
            log_info "Manual setup instructions:"
            echo "1. Go to your GitHub repository"
            echo "2. Navigate to Settings → Secrets and variables → Actions"
            echo "3. Click 'New repository secret'"
            echo "4. Add each missing secret:"
            echo
            while IFS= read -r secret; do
                if [ -n "$secret" ]; then
                    local desc
                    desc=$(get_secret_description "$secret")
                    echo "   • $secret: $desc"
                fi
            done <<< "$missing_secrets"
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

    echo
    log_info "Secret setup completed!"
    log_info "Run the preflight check again to verify:"
    log_info "  scripts/m5_preflight_secrets_permissions.sh"
}

# Show help
show_help() {
    cat << EOF
M5 Fix Missing Secrets Helper

DESCRIPTION:
    Helper script to fix missing secrets identified by M5 preflight check.
    Provides interactive and batch modes for adding secrets.

USAGE:
    $0 [options]

OPTIONS:
    -h, --help      Show this help message
    -b, --batch     Run in batch mode for common secrets
    -m, --manual    Show manual instructions only

REQUIREMENTS:
    - GitHub CLI (gh) authenticated
    - Latest M5 preflight report in governance/

EXAMPLES:
    $0                  # Interactive mode
    $0 --batch          # Batch mode for common secrets
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
if [ "${BATCH_MODE:-false}" = "true" ]; then
    setup_common_secrets
elif [ "${MANUAL_MODE:-false}" = "true" ]; then
    report=$(get_latest_report)
    missing_secrets=$(extract_missing_secrets "$report")

    if [ -z "$missing_secrets" ]; then
        log_success "No missing secrets found!"
        exit 0
    fi

    log_info "Manual setup instructions for missing secrets:"
    echo
    while IFS= read -r secret; do
        if [ -n "$secret" ]; then
            desc=$(get_secret_description "$secret")
            echo "• $secret: $desc"
        fi
    done <<< "$missing_secrets"
else
    main "$@"
fi
