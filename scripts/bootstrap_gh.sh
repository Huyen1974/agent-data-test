#!/bin/bash
# GitHub CLI Auth Bootstrap Script
# Based on logic from M5.1_cli01_verify.sh and .cursor/law_files/ALL_LAWs.md
# Usage:
#   PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh verify
#   PROJECT="github-chatgpt-ggcloud" SECRET_NAME="gh_pat_sync_secrets" scripts/bootstrap_gh.sh apply

set -euo pipefail

ACTION="${1:-verify}"
PROJECT="${PROJECT:-}"
SECRET_NAME="${SECRET_NAME:-}"

log() { printf "[bootstrap_gh] %s\n" "$*"; }

if [ -z "$PROJECT" ] || [ -z "$SECRET_NAME" ]; then
    log "ERROR: Required environment variables not set"
    log "Usage: PROJECT=<project> SECRET_NAME=<secret> $0 <verify|apply>"
    exit 1
fi

verify_auth() {
    log "Running GH Bootstrap VERIFY (no config changes)..."

    # Check if gh CLI is installed
    if ! command -v gh >/dev/null 2>&1; then
        log "FAIL: GitHub CLI (gh) not found. Please install it first."
        return 1
    fi

    # Check authentication status
    if gh auth status -h github.com >/dev/null 2>&1; then
        log "PASS: GitHub CLI is authenticated"
        return 0
    else
        log "WARN: gh not authenticated"
        return 1
    fi
}

apply_auth() {
    log "Attempting GH Bootstrap APPLY..."

    # Try to get token from Google Secret Manager
    if command -v gcloud >/dev/null 2>&1; then
        # Check if gcloud is authenticated
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" >/dev/null 2>&1; then
            # Try to access the secret
            if TOKEN=$(gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT" 2>/dev/null); then
                log "Successfully retrieved token from GSM"

                # Login with the token
                echo "$TOKEN" | gh auth login --with-token

                if gh auth status -h github.com >/dev/null 2>&1; then
                    log "PASS: Successfully authenticated with GitHub CLI"
                    return 0
                else
                    log "FAIL: Authentication failed even after token login"
                    return 1
                fi
            else
                log "WARN: Could not access secret $SECRET_NAME in project $PROJECT"
                return 1
            fi
        else
            log "WARN: gcloud not authenticated, cannot access secrets"
            return 1
        fi
    else
        log "WARN: gcloud CLI not available"
        return 1
    fi
}

case "$ACTION" in
    verify)
        verify_auth
        ;;
    apply)
        if ! verify_auth; then
            apply_auth
        fi
        ;;
    *)
        log "ERROR: Unknown action '$ACTION'. Use 'verify' or 'apply'"
        exit 1
        ;;
esac
