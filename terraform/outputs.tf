output "project_id" {
  description = "The GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region"
  value       = var.region
}

output "environment" {
  description = "The environment"
  value       = var.env
}

output "gcs_buckets" {
  description = "Map of GCS bucket purposes to their names"
  value = {
    artifacts        = google_storage_bucket.huyen1974_agent_data_artifacts_test.name
    knowledge        = google_storage_bucket.huyen1974_agent_data_knowledge_test.name
    logs             = google_storage_bucket.huyen1974_agent_data_logs_test.name
    qdrant_snapshots = google_storage_bucket.huyen1974_agent_data_qdrant_snapshots_test.name
    source           = google_storage_bucket.huyen1974_agent_data_source_test.name
    tfstate          = google_storage_bucket.huyen1974_agent_data_tfstate_test.name
  }
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository details"
  value = {
    name     = data.google_artifact_registry_repository.agent_data_docker_repo.name
    location = data.google_artifact_registry_repository.agent_data_docker_repo.location
    id       = data.google_artifact_registry_repository.agent_data_docker_repo.repository_id
  }
}

output "qdrant_endpoint" {
  description = "Qdrant cluster endpoint"
  value       = "https://${var.qdrant_cluster_id}.qdrant.tech"
}

output "qdrant_secret_name" {
  description = "Qdrant API key secret name"
  value       = data.google_secret_manager_secret.qdrant_api.secret_id
}
