data "google_project" "current" {
  project_id = var.project_id
}

resource "google_project_iam_member" "run_sa_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Disabled: Cloud Run is disabled (count=0 in main.tf)
# This IAM binding causes Error 403: CI service account lacks permission to grant this role
# Re-enable when Cloud Run service is provisioned
# resource "google_project_iam_member" "run_sa_firestore_user" {
#   project = var.project_id
#   role    = "roles/datastore.user"
#   member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
# }

# Allow Cloud Run / Functions runtime SA to publish to Pub/Sub topic
resource "google_pubsub_topic_iam_member" "publisher_on_tasks_topic" {
  project = var.project_id
  topic   = google_pubsub_topic.agent_data_tasks_test.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}

# Allow runtime SA to read from knowledge bucket (for function download)
resource "google_storage_bucket_iam_member" "runtime_sa_object_viewer_knowledge" {
  bucket = google_storage_bucket.huyen1974_agent_data_knowledge_test.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}
