module "agent_data_service_test" {
  count                  = 0 # disable Cloud Run provisioning in automated apply
  source                 = "./modules/cloud_run_service"
  project_id             = "github-chatgpt-ggcloud"
  location               = "asia-southeast1"
  service_name           = "agent-data-test"
  image_path             = "asia-southeast1-docker.pkg.dev/github-chatgpt-ggcloud/agent-data-test/agent-data-test:latest"
  api_key_secret         = data.google_secret_manager_secret.agent_data_api_key.secret_id
  api_key_secret_version = data.google_secret_manager_secret_version.agent_data_api_key.version
}
