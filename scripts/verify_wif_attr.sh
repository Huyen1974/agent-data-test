#!/bin/bash
#
# verify_wif_attr.sh - WIF Attribute Verification Script (M2 Security Verify)
# Part of Prompt 169m - Security Verification System
#
# Verifies Workload Identity Federation (WIF) configuration for:
# - Attribute conditions for 3 repositories
# - Required attribute mappings (repository, ref, actor)
# - Service Account IAM bindings
#
# Environment Variables Required:
# - PROJ: GCP Project ID (default: github-chatgpt-ggcloud)
# - PN: Project Number (default: 812872501910)
# - WIF_POOL: WIF Pool name (default: agent-data-pool)
# - WIF_PROVIDER_NAME: WIF Provider name (default: github-provider)
#
# Output: JSON to stdout with verification results
# Exit: 0 on success, 1 on failure

set -euo pipefail

# Default values
PROJ="${PROJ:-github-chatgpt-ggcloud}"
PN="${PN:-812872501910}"
WIF_POOL="${WIF_POOL:-agent-data-pool}"
WIF_PROVIDER_NAME="${WIF_PROVIDER_NAME:-github-provider}"

# Required repositories
REQUIRED_REPOS=(
    "Huyen1974/chatgpt-githubnew"
    "Huyen1974/agent-data-test"
    "Huyen1974/agent-data-production"
)

# Required attribute mappings
REQUIRED_MAPPINGS=(
    "attribute.repository"
    "attribute.ref"
    "attribute.actor"
)

# Construct provider path
PROV="projects/${PN}/locations/global/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER_NAME}"

# Initialize result object
timestamp_utc=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")

# Function to check if string contains all required repos
check_repo_includes() {
    local condition="$1"
    local central_ok="false"
    local test_ok="false"
    local production_ok="false"

    if echo "$condition" | grep -q "Huyen1974/chatgpt-githubnew"; then
        central_ok="true"
    fi

    if echo "$condition" | grep -q "Huyen1974/agent-data-test"; then
        test_ok="true"
    fi

    if echo "$condition" | grep -q "Huyen1974/agent-data-production"; then
        production_ok="true"
    fi

    echo "\"central\": $central_ok, \"test\": $test_ok, \"production\": $production_ok"
}

# Function to check attribute mappings
check_mappings() {
    local mapping_json="$1"
    local has_repository="false"
    local has_ref="false"
    local has_actor="false"

    if echo "$mapping_json" | grep -q '"attribute.repository"'; then
        has_repository="true"
    fi

    if echo "$mapping_json" | grep -q '"attribute.ref"'; then
        has_ref="true"
    fi

    if echo "$mapping_json" | grep -q '"attribute.actor"'; then
        has_actor="true"
    fi

    echo "\"has_repository\": $has_repository, \"has_ref\": $has_ref, \"has_actor\": $has_actor"
}

# Function to check SA bindings
check_sa_bindings() {
    local sa_email="chatgpt-deployer@${PROJ}.iam.gserviceaccount.com"
    local central_ok="false"
    local test_ok="false"
    local production_ok="false"

    # Get IAM policy for the service account
    local policy_json
    if policy_json=$(gcloud iam service-accounts get-iam-policy "$sa_email" --format=json 2>/dev/null); then

        # Check for workloadIdentityUser role bindings
        local bindings
        bindings=$(echo "$policy_json" | jq -r '.bindings[]? | select(.role == "roles/iam.workloadIdentityUser") | .members[]?' 2>/dev/null || echo "")

        # Check each repository binding
        if echo "$bindings" | grep -q "principalSet://iam.googleapis.com/projects/${PN}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/Huyen1974/chatgpt-githubnew"; then
            central_ok="true"
        fi

        if echo "$bindings" | grep -q "principalSet://iam.googleapis.com/projects/${PN}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/Huyen1974/agent-data-test"; then
            test_ok="true"
        fi

        if echo "$bindings" | grep -q "principalSet://iam.googleapis.com/projects/${PN}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/Huyen1974/agent-data-production"; then
            production_ok="true"
        fi
    fi

    echo "\"central\": $central_ok, \"test\": $test_ok, \"production\": $production_ok"
}

# Main verification logic
main() {
    # Get WIF provider configuration
    local provider_json
    if ! provider_json=$(gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_NAME" \
        --location=global \
        --workload-identity-pool="$WIF_POOL" \
        --project="$PROJ" \
        --format=json 2>/dev/null); then
        echo "ERROR: Failed to describe WIF provider: $PROV" >&2
        exit 1
    fi

    # Extract attribute condition and mapping
    local attr_condition
    local attr_mapping
    attr_condition=$(echo "$provider_json" | jq -r '.attributeCondition // ""')
    attr_mapping=$(echo "$provider_json" | jq -r '.attributeMapping // {}')

    # Check repository includes
    local includes_result
    includes_result=$(check_repo_includes "$attr_condition")

    # Check attribute mappings
    local mapping_result
    mapping_result=$(check_mappings "$attr_mapping")

    # Check SA bindings
    local sa_binding_result
    sa_binding_result=$(check_sa_bindings)

    # Output JSON result
    cat <<EOF
{
  "prov": "$PROV",
  "includes": {$includes_result},
  "mapping": {$mapping_result},
  "sa_binding": {$sa_binding_result},
  "timestamp_utc": "$timestamp_utc"
}
EOF
}

# Execute main function
main "$@"
