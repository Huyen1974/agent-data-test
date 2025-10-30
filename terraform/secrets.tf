# Secret Manager references for agent-data-langroid

data "google_secret_manager_secret" "qdrant_api" {
  project   = var.project_id
  secret_id = "Qdrant_agent_data_N1D8R2vC0_5"
}

data "google_secret_manager_secret_version" "qdrant_api" {
  project = var.project_id
  secret  = data.google_secret_manager_secret.qdrant_api.id
  version = "latest"
}

data "google_secret_manager_secret" "agent_data_api_key" {
  project   = var.project_id
  secret_id = "AGENT_DATA_API_KEY"
}

data "google_secret_manager_secret_version" "agent_data_api_key" {
  project = var.project_id
  secret  = data.google_secret_manager_secret.agent_data_api_key.id
  version = "latest"
}
