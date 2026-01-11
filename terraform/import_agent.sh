#!/bin/bash
set -e

echo "🔹 1. INITIALIZING..."
# Partial backend config - using the A1-T bucket itself for state if possible,
# OR use local state temporarily if the bucket is empty/new.
# Adhering to Plan: We will use local state for import, then migrate later if needed,
# BUT standard practice is to init with the target state bucket if it exists.
terraform init -migrate-state -backend-config="bucket=huyen1974-agent-data-tfstate-test"

echo "🔹 2. IMPORTING RESOURCES..."
# Helper function
safe_import() {
  addr=$1
  id=$2
  if terraform state show "$addr" >/dev/null 2>&1; then
    echo "✅ $addr already imported."
  else
    echo "🚀 Importing $id..."
    terraform import -var="project_id=github-chatgpt-ggcloud" -var="env=test" "$addr" "$id"
  fi
}

# Group 2 (Test)
safe_import "google_storage_bucket.agent_tf_state_test" "huyen1974-agent-data-tfstate-test"
safe_import "google_storage_bucket.agent_knowledge_test" "huyen1974-agent-data-knowledge-test"
safe_import "google_storage_bucket.agent_artifacts_test" "huyen1974-agent-data-artifacts-test"
safe_import "google_storage_bucket.agent_logs_test" "huyen1974-agent-data-logs-test"
safe_import "google_storage_bucket.agent_snapshots_test" "huyen1974-agent-data-qdrant-snapshots-test"
safe_import "google_storage_bucket.agent_backup_test" "huyen1974-agent-data-backup-test"

# Group 3 (Prod)
safe_import "google_storage_bucket.agent_tf_state_prod" "huyen1974-agent-data-tfstate-production"
safe_import "google_storage_bucket.agent_knowledge_prod" "huyen1974-agent-data-knowledge-production"
safe_import "google_storage_bucket.agent_artifacts_prod" "huyen1974-agent-data-artifacts-production"
safe_import "google_storage_bucket.agent_logs_prod" "huyen1974-agent-data-logs-production"
safe_import "google_storage_bucket.agent_snapshots_prod" "huyen1974-agent-data-qdrant-snapshots-production"

# Legacy
safe_import "google_storage_bucket.faiss_index" "huyen1974-faiss-index-storage"

echo "🔹 3. VERIFYING (PLAN)..."
terraform plan -var="project_id=github-chatgpt-ggcloud" -var="env=test" -out=phase4_import.tfplan
