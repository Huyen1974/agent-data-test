#!/usr/bin/env bash
set -euo pipefail

# Script to retrieve GitHub PAT from GCP Secret Manager and configure Git
# Secret: gh_pat_sync_secrets
# Project: github-chatgpt-ggcloud

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/artifacts/logs/get_pat_from_gcp.log"

# Ensure log directory exists
mkdir -p "${PROJECT_ROOT}/artifacts/logs"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting PAT retrieval from GCP Secret Manager..."

# Check if gcloud is available
if ! command -v gcloud &> /dev/null; then
    log "ERROR: gcloud CLI is not installed or not in PATH"
    exit 1
fi

# Check if we're authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    log "ERROR: Not authenticated with GCP. Please run 'gcloud auth login' first"
    exit 1
fi

# Set the project
PROJECT_ID="github-chatgpt-ggcloud"
SECRET_NAME="gh_pat_sync_secrets"

log "Retrieving PAT from GCP Secret Manager..."
log "Project: $PROJECT_ID"
log "Secret: $SECRET_NAME"

# Get the PAT from Secret Manager
PAT=$(gcloud secrets versions access latest \
    --secret="$SECRET_NAME" \
    --project="$PROJECT_ID" \
    2>>"$LOG_FILE")

if [ -z "$PAT" ]; then
    log "ERROR: Failed to retrieve PAT from Secret Manager"
    exit 1
fi

log "Successfully retrieved PAT from Secret Manager"

# Configure Git to use the PAT via HTTPS credentials
# The PAT should be in format: username:token
# We'll store it in ~/.git-credentials for HTTPS authentication

GIT_CREDENTIALS_FILE="$HOME/.git-credentials"
BACKUP_FILE="$HOME/.git-credentials.backup.$(date +%Y%m%d_%H%M%S)"

# Backup existing credentials if they exist
if [ -f "$GIT_CREDENTIALS_FILE" ]; then
    cp "$GIT_CREDENTIALS_FILE" "$BACKUP_FILE"
    log "Backed up existing git credentials to $BACKUP_FILE"
fi

# Check if this PAT is already configured
if grep -q "$PAT" "$GIT_CREDENTIALS_FILE" 2>/dev/null; then
    log "PAT already configured in git credentials"
else
    # Add the PAT to git credentials
    echo "https://$PAT@github.com" >> "$GIT_CREDENTIALS_FILE"
    log "Added PAT to git credentials"
fi

# Configure git to use credential helper
git config --global credential.helper store
git config --global credential.useHttpPath true

log "Git PAT configuration completed successfully"

# Verify the configuration
if git config --global credential.helper | grep -q store; then
    log "Git credential helper configured correctly"
else
    log "WARNING: Git credential helper not configured properly"
fi

log "PAT setup script completed successfully"
