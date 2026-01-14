module "agent_data_service_test" {
  count                  = 0 # disable Cloud Run provisioning in automated apply
  source                 = "./modules/cloud_run_service"
  project_id             = var.project_id
  location               = var.region
  service_name           = var.run_service_name
  image_path             = "${var.region}-docker.pkg.dev/${var.project_id}/${local.artifact_registry_repo}/${local.artifact_registry_package}:latest"
  api_key_secret         = data.google_secret_manager_secret.agent_data_api_key.secret_id
  api_key_secret_version = data.google_secret_manager_secret_version.agent_data_api_key.version
}
