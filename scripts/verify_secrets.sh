#!/bin/bash
set -euo pipefail

# verify_secrets.sh - Check required environment variables for CI/CD
# Exit 1 with ::error:: message if any required secrets are missing or placeholder

echo "::notice::🔐 Verifying required secrets..."

# Required environment variables
REQUIRED_VARS=(
    "GCP_PROJECT_ID"
    "GCP_SERVICE_ACCOUNT"
    "GCP_WIF_PROVIDER"
    "GCP_WIF_POOL"
    "GCP_SA_KEY_JSON"
    "OPENAI_API_KEY"
    "QDRANT_CLOUD_MGMT_KEY"
    "QDRANT_CLUSTER1_ID"
    "QDRANT_CLUSTER1_KEY"
)

# Common placeholder values that indicate unset secrets
PLACEHOLDER_VALUES=(
    "xxx"
    "changeme"
    "your-api-key"
    "your-project-id"
    "your-cluster-id"
    "placeholder"
    "TODO"
    "FIXME"
    ""
)

# Function to check if value is a placeholder
is_placeholder() {
    local value="$1"

    # Check for star-only patterns (placeholder stars)
    if [[ "$value" =~ ^\*+$ ]]; then
        return 0
    fi

    # Check if value is too short (minimum 20 chars for secrets)
    if [[ ${#value} -lt 20 ]]; then
        return 0
    fi

    for placeholder in "${PLACEHOLDER_VALUES[@]}"; do
        if [[ "$value" == "$placeholder" ]]; then
            return 0
        fi
    done
    return 1
}

# Check each required variable
missing_vars=()
placeholder_vars=()

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    elif is_placeholder "${!var}"; then
        placeholder_vars+=("$var")
    else
        value="${!var}"
        echo "✅ $var (${#value} chars)"
    fi
done

# Special validation for QDRANT_API_URL if it exists
if [[ -n "${QDRANT_API_URL:-}" ]]; then
    if [[ ! "$QDRANT_API_URL" =~ ^https://.*\.cloud\.qdrant\.io:6333$ ]]; then
        echo "::error::❌ QDRANT_API_URL format validation failed!"
        echo "::error::Expected format: https://<cluster-id>.<region>.gcp.cloud.qdrant.io:6333"
        echo "::error::Got: $QDRANT_API_URL"
        exit 1
    else
        echo "✅ QDRANT_API_URL format validated"
    fi
fi

# Report any issues
if [[ ${#missing_vars[@]} -gt 0 ]] || [[ ${#placeholder_vars[@]} -gt 0 ]]; then
    echo "::error::❌ Secret verification failed!"

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        echo "::error::Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "::error::  - $var"
        done
    fi

    if [[ ${#placeholder_vars[@]} -gt 0 ]]; then
        echo "::error::Found placeholder values in required variables:"
        for var in "${placeholder_vars[@]}"; do
            echo "::error::  - $var = '${!var}'"
        done
    fi

    echo "::error::Please ensure all required secrets are properly configured in GitHub repository settings."
    exit 1
fi

echo "::notice::✅ All required secrets verified successfully!"
echo "::notice::Ready for E2E testing with real OpenAI + Qdrant integration"
