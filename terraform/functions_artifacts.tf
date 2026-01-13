data "google_project" "cur" {
  project_id = var.project_id
}

locals {
  fn_region  = var.region
  src_bucket = google_storage_bucket.huyen1974_agent_data_artifacts_test.name
  appspot_sa = "${data.google_project.cur.project_id}@appspot.gserviceaccount.com"
}

data "archive_file" "mark_src" {
  type        = "zip"
  source_dir  = abspath("${path.root}/../functions/mark_stale_artifacts")
  output_path = "${path.module}/.build/mark_stale_artifacts.zip"
}

resource "google_storage_bucket_object" "mark_src" {
  name         = "functions/mark_stale_artifacts.zip"
  bucket       = local.src_bucket
  content_type = "application/zip"
  source       = data.archive_file.mark_src.output_path
}

resource "google_cloudfunctions2_function" "mark_stale" {
  name        = "mark-stale-artifacts"
  location    = local.fn_region
  description = "Mark stale Artifact Registry images by tagging them"

  build_config {
    runtime     = "python311"
    entry_point = "handle"
    source {
      storage_source {
        bucket = google_storage_bucket_object.mark_src.bucket
        object = google_storage_bucket_object.mark_src.name
      }
    }
  }

  service_config {
    available_memory = "256M"
    timeout_seconds  = 120
    ingress_settings = "ALLOW_INTERNAL_AND_GCLB"
    environment_variables = {
      PROJECT_ID     = var.project_id
      REGION         = var.region
      AR_REPO        = local.artifact_registry_repo
      AR_PACKAGE     = local.artifact_registry_package
      TTL_DAYS       = "14"
      IMPORTANT_TAGS = "latest,stable"
    }
  }
}

data "archive_file" "report_src" {
  type        = "zip"
  source_dir  = abspath("${path.root}/../functions/report_stale_artifacts")
  output_path = "${path.module}/.build/report_stale_artifacts.zip"
}

resource "google_storage_bucket_object" "report_src" {
  name         = "functions/report_stale_artifacts.zip"
  bucket       = local.src_bucket
  content_type = "application/zip"
  source       = data.archive_file.report_src.output_path
}

resource "google_cloudfunctions2_function" "report_stale" {
  name        = "report-stale-artifacts"
  location    = local.fn_region
  description = "Report stale images and notify Slack"

  build_config {
    runtime     = "python311"
    entry_point = "handle"
    source {
      storage_source {
        bucket = google_storage_bucket_object.report_src.bucket
        object = google_storage_bucket_object.report_src.name
      }
    }
  }

  service_config {
    available_memory = "256M"
    timeout_seconds  = 120
    ingress_settings = "ALLOW_INTERNAL_AND_GCLB"
    environment_variables = {
      PROJECT_ID        = var.project_id
      REGION            = var.region
      AR_REPO           = local.artifact_registry_repo
      AR_PACKAGE        = local.artifact_registry_package
      SLACK_SECRET_NAME = "SLACK_WEBHOOK_URL"
    }
  }
}

resource "google_cloud_run_service_iam_member" "mark_invoker" {
  location = google_cloudfunctions2_function.mark_stale.location
  project  = var.project_id
  service  = google_cloudfunctions2_function.mark_stale.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.appspot_sa}"
}

resource "google_cloud_run_service_iam_member" "report_invoker" {
  location = google_cloudfunctions2_function.report_stale.location
  project  = var.project_id
  service  = google_cloudfunctions2_function.report_stale.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.appspot_sa}"
}

resource "google_cloud_scheduler_job" "mark_daily" {
  name        = "mark-stale-artifacts-daily"
  region      = var.region
  description = "Daily mark stale artifacts"
  schedule    = "0 0 * * *"
  time_zone   = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.mark_stale.service_config[0].uri

    oidc_token {
      service_account_email = local.appspot_sa
    }
  }
}

resource "google_cloud_scheduler_job" "report_weekly" {
  name        = "report-stale-artifacts-weekly"
  region      = var.region
  description = "Weekly report stale artifacts to Slack"
  schedule    = "0 1 * * 1"
  time_zone   = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions2_function.report_stale.service_config[0].uri

    oidc_token {
      service_account_email = local.appspot_sa
    }
  }
}

# Ingest processor: Pub/Sub-triggered function to handle async ingest
data "archive_file" "ingest_processor_src" {
  type        = "zip"
  source_dir  = abspath("${path.root}/../functions/ingest_processor")
  output_path = "${path.module}/.build/ingest_processor.zip"
}

resource "google_storage_bucket_object" "ingest_processor_src" {
  name         = "functions/ingest_processor.zip"
  bucket       = local.src_bucket
  content_type = "application/zip"
  source       = data.archive_file.ingest_processor_src.output_path
}

resource "google_cloudfunctions2_function" "ingest_processor" {
  name        = "ingest-processor"
  location    = local.fn_region
  description = "Process async ingest messages from Pub/Sub and write metadata"

  build_config {
    runtime     = "python311"
    entry_point = "handle"
    source {
      storage_source {
        bucket = google_storage_bucket_object.ingest_processor_src.bucket
        object = google_storage_bucket_object.ingest_processor_src.name
      }
    }
  }

  service_config {
    available_memory      = "256M"
    timeout_seconds       = 120
    service_account_email = "${data.google_project.cur.number}-compute@developer.gserviceaccount.com"
    environment_variables = {
      PROJECT_ID          = var.project_id
      REGION              = var.region
      METADATA_COLLECTION = "metadata_test"
    }
  }

  event_trigger {
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.agent_data_tasks_test.id
    retry_policy   = "RETRY_POLICY_RETRY"
  }
}

# Allow Eventarc service account to invoke the function's underlying Cloud Run service
resource "google_cloud_run_service_iam_member" "ingest_eventarc_invoker" {
  location = google_cloudfunctions2_function.ingest_processor.location
  project  = var.project_id
  service  = google_cloudfunctions2_function.ingest_processor.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.cur.number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}

resource "google_cloud_run_service_iam_member" "ingest_pubsub_invoker" {
  location = google_cloudfunctions2_function.ingest_processor.location
  project  = var.project_id
  service  = google_cloudfunctions2_function.ingest_processor.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${data.google_project.cur.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_cloud_run_service_iam_member" "ingest_compute_invoker" {
  location = google_cloudfunctions2_function.ingest_processor.location
  project  = var.project_id
  service  = google_cloudfunctions2_function.ingest_processor.service_config[0].service
  role     = "roles/run.invoker"
  member   = "serviceAccount:${data.google_project.cur.number}-compute@developer.gserviceaccount.com"
}
