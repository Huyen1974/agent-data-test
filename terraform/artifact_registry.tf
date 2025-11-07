# Artifact Registry for Docker images
# Use data source to reference existing repository (avoiding Error 409)
data "google_artifact_registry_repository" "agent_data_docker_repo" {
  project       = var.project_id
  location      = var.region
  repository_id = "agent-data-${var.env}"
}

// Moved to module: modules/cloud_run_service
