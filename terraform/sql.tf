locals {
  managed_sql_instance_name = var.sql_instance_name != "" ? var.sql_instance_name : "agent-data-managed-sql"
}

resource "google_project_service" "sqladmin" {
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudscheduler" {
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "sql_scheduler" {
  account_id   = "sql-scheduler"
  display_name = "SQL Scheduler Service Account"
}

resource "google_service_account_iam_member" "scheduler_token_creator" {
  service_account_id = google_service_account.sql_scheduler.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}

resource "google_project_iam_member" "sql_scheduler_admin" {
  project = var.project_id
  role    = "roles/cloudsql.admin"
  member  = "serviceAccount:${google_service_account.sql_scheduler.email}"
}

resource "google_sql_database_instance" "managed" {
  name                = local.managed_sql_instance_name
  database_version    = var.sql_database_version
  region              = var.sql_region
  project             = var.project_id
  deletion_protection = var.sql_deletion_protection

  settings {
    tier              = var.sql_tier
    availability_type = "ZONAL"
    activation_policy = "NEVER"

    backup_configuration {
      enabled                        = true
      start_time                     = var.sql_backup_start_time
      point_in_time_recovery_enabled = false
    }

    ip_configuration {
      ipv4_enabled = true
    }
  }
}

resource "google_cloud_scheduler_job" "sql_start" {
  name      = "${local.managed_sql_instance_name}-start"
  schedule  = var.sql_start_schedule
  time_zone = var.sql_schedule_timezone
  region    = var.sql_scheduler_region

  http_target {
    http_method = "PATCH"
    uri         = "https://sqladmin.googleapis.com/v1/projects/${var.project_id}/instances/${local.managed_sql_instance_name}?updateMask=settings.activationPolicy"
    body        = base64encode(jsonencode({ settings = { activationPolicy = "ALWAYS" } }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.sql_scheduler.email
    }
  }

  depends_on = [
    google_project_service.sqladmin,
    google_project_service.cloudscheduler,
    google_service_account_iam_member.scheduler_token_creator,
    google_project_iam_member.sql_scheduler_admin,
    google_sql_database_instance.managed
  ]
}

resource "google_cloud_scheduler_job" "sql_stop" {
  name      = "${local.managed_sql_instance_name}-stop"
  schedule  = var.sql_stop_schedule
  time_zone = var.sql_schedule_timezone
  region    = var.sql_scheduler_region

  http_target {
    http_method = "PATCH"
    uri         = "https://sqladmin.googleapis.com/v1/projects/${var.project_id}/instances/${local.managed_sql_instance_name}?updateMask=settings.activationPolicy"
    body        = base64encode(jsonencode({ settings = { activationPolicy = "NEVER" } }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = google_service_account.sql_scheduler.email
    }
  }

  depends_on = [
    google_cloud_scheduler_job.sql_start,
    google_project_service.sqladmin,
    google_project_service.cloudscheduler,
    google_service_account_iam_member.scheduler_token_creator,
    google_project_iam_member.sql_scheduler_admin
  ]
}
