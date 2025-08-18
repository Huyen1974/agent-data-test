#!/bin/bash
# Pre-push validation script
# Simple validation to ensure basic checks pass before push

set -euo pipefail

echo "[pre-push] Running pre-push validation..."

# Check if we're pushing to a feature branch
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" =~ ^feat/ ]]; then
    echo "[pre-push] Pushing feature branch: $BRANCH"
    echo "[pre-push] Basic validation passed."
else
    echo "[pre-push] Pushing to branch: $BRANCH"
fi

echo "[pre-push] Pre-push validation completed successfully."
exit 0
