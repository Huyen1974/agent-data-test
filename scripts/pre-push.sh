#!/usr/bin/env bash
# Pre-push script for agent-data-langroid
# Enforces local checks and workflow verification before pushing

set -euo pipefail

# Configuration
TF_BACKEND_BUCKET="huyen1974-agent-data-tfstate-test"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "🔍 Pre-push validation for agent-data-langroid"
echo "=============================================="

# Function to check if GitHub CLI is available and authenticated
check_gh_auth() {
    if ! command -v gh &> /dev/null; then
        echo "❌ GitHub CLI (gh) not found. Please install it to proceed."
        echo "   brew install gh"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        echo "❌ GitHub CLI not authenticated. Please run 'gh auth login'"
        exit 1
    fi

    echo "✅ GitHub CLI authenticated"
}

# Function to check for running workflows
check_running_workflows() {
    echo "🔄 Checking for running workflows..."

    # Check if pass-gate workflow exists first
    if ! gh run list --workflow=pass-gate --limit 1 &> /dev/null; then
        echo "⚠️  No pass-gate workflow found (this is expected for new implementation)"
        return 0
    fi

    # Check if any pass-gate workflows are still running
    local running_count
    running_count=$(gh run list --workflow=pass-gate --json status \
        | jq -r '.[] | select(.status != "completed") | .status' \
        | wc -l | tr -d ' ')

    if [[ "$running_count" -gt 0 ]]; then
        echo "❌ Some workflows are still running. Please wait for completion."
        gh run list --workflow=pass-gate --limit 5
        exit 1
    fi

    echo "✅ No running workflows detected"
}

# Function to check recent CI status
check_recent_ci_status() {
    echo "🔍 Checking recent CI status..."

    # Get the last 5 workflow runs and check their status
    local failed_runs
    failed_runs=$(gh run list --limit 5 --json name,status,conclusion 2>/dev/null \
        | jq -r '.[] | select(.status == "completed" and .conclusion != "success") | "\(.name): \(.conclusion)"' 2>/dev/null || echo "")

    if [[ -n "$failed_runs" ]]; then
        echo "❌ Recent CI failures detected:"
        echo "$failed_runs"
        echo ""
        echo "Please ensure all CI checks pass before pushing."
        exit 1
    fi

    echo "✅ Recent CI status looks good"
}

# Function to validate terraform locally
validate_terraform() {
    echo "🏗️  Validating Terraform configuration..."

    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        echo "❌ Terraform not found. Please install terraform 1.8.x"
        exit 1
    fi

    # Navigate to terraform directory
    cd terraform/

    # Initialize terraform with the backend bucket
    echo "  Initializing terraform..."
    if ! terraform init -backend-config="bucket=${TF_BACKEND_BUCKET}" -input=false -no-color &> /dev/null; then
        echo "❌ Terraform init failed. Please check backend configuration."
        exit 1
    fi

    # Validate terraform configuration
    echo "  Validating terraform configuration..."
    if ! terraform validate -no-color; then
        echo "❌ Terraform validation failed"
        exit 1
    fi

    # Check terraform formatting
    echo "  Checking terraform formatting..."
    if ! terraform fmt -check -recursive; then
        echo "❌ Terraform files are not properly formatted"
        echo "   Run: terraform fmt -recursive"
        exit 1
    fi

    # Return to repo root
    cd "$REPO_ROOT"

    echo "✅ Terraform validation passed"
}

# Function to check pre-commit hooks
check_pre_commit() {
    echo "🪝 Running pre-commit checks..."

    if ! command -v pre-commit &> /dev/null; then
        echo "❌ pre-commit not found. Please install pre-commit"
        echo "   pip install pre-commit"
        exit 1
    fi

    if ! pre-commit run --all-files; then
        echo "❌ Pre-commit checks failed"
        exit 1
    fi

    echo "✅ Pre-commit checks passed"
}

# Function to check test manifest consistency
check_test_manifest() {
    echo "📋 Checking test manifest consistency..."

    if ! python scripts/collect_manifest.py --check test_manifest_baseline.txt; then
        echo "❌ Test manifest drift detected"
        echo "   Run: python scripts/collect_manifest.py > test_manifest_baseline.txt"
        echo "   Then commit the updated baseline file"
        exit 1
    fi

    echo "✅ Test manifest is consistent"
}

# Main execution flow
main() {
    # Abort if there are uncommitted changes
    if ! git diff --quiet; then
        echo "❌ You have uncommitted changes. Please commit or stash them first."
        exit 1
    fi

    # Abort if there are staged changes
    if ! git diff --cached --quiet; then
        echo "❌ You have staged changes. Please commit them first."
        exit 1
    fi

    # Run all checks
    check_gh_auth
    check_running_workflows
    check_recent_ci_status
    validate_terraform
    check_pre_commit
    check_test_manifest

    echo ""
    echo "🎉 All pre-push checks passed!"
    echo "   Ready to push to remote repository."
    echo ""
}

# Handle script interruption
trap 'echo "❌ Pre-push validation interrupted"; exit 1' INT TERM

# Run main function
main "$@"
