# Vector integrity monitoring infrastructure
# Leverages endpoints from PR #242: /kb/audit-sync, /health
# GC-LAW compliant: no new SA, uses existing appspot SA pattern

# Look up the Cloud Run service to get its URL dynamically
data "google_cloud_run_service" "agent_data" {
  name     = var.run_service_name
  location = var.region
  project  = var.project_id
}

# Grant App Engine default SA permission to invoke Cloud Run service
# Required for Cloud Scheduler to call /kb/audit-sync with OIDC auth
# Follows same pattern as mark_invoker/report_invoker in functions_artifacts.tf
resource "google_cloud_run_service_iam_member" "scheduler_audit_invoker" {
  location = var.region
  project  = var.project_id
  service  = var.run_service_name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.appspot_sa}"
}

# Cloud Scheduler: auto-heal vector sync every 12 hours
# Calls POST /kb/audit-sync with auto_heal=true to detect and fix issues automatically
resource "google_cloud_scheduler_job" "audit_sync_6h" {
  name        = "vector-audit-sync-6h"
  region      = var.region
  description = "Auto-heal vector sync integrity every 12 hours"
  schedule    = "0 */12 * * *"
  time_zone   = "Etc/UTC"

  http_target {
    http_method = "POST"
    uri         = "${data.google_cloud_run_service.agent_data.status[0].url}/kb/audit-sync"
    body        = base64encode(jsonencode({ auto_heal = true }))

    headers = {
      "Content-Type" = "application/json"
      "x-api-key"    = data.google_secret_manager_secret_version.agent_data_api_key.secret_data
    }

    oidc_token {
      service_account_email = local.appspot_sa
    }
  }
}

# Log-based metric: count failed audit-sync and health calls (5xx)
resource "google_logging_metric" "vector_endpoint_errors" {
  name        = "vector-endpoint-errors"
  description = "Count of 5xx errors on vector monitoring endpoints"
  filter      = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.run_service_name}"
    httpRequest.requestUrl=~"/kb/audit-sync|/kb/reindex-missing|/kb/cleanup-orphans|/health"
    httpRequest.status>=500
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
  }
}

# Notification channel for vector monitoring alerts
resource "google_monitoring_notification_channel" "vector_ops_email" {
  display_name = "Vector Ops Email"
  type         = "email"

  labels = {
    email_address = var.alert_email
  }
}

# Alert: vector monitoring endpoint failures
# Fires when any vector integrity endpoint returns 5xx for > 5 minutes
resource "google_monitoring_alert_policy" "vector_endpoint_failures" {
  display_name = "Vector Monitoring Endpoint Failures"
  combiner     = "OR"
  enabled      = true

  conditions {
    display_name = "Vector endpoints returning 5xx errors"

    condition_threshold {
      filter          = "metric.type=\"logging.googleapis.com/user/vector-endpoint-errors\" AND resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_COUNT"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.vector_ops_email.name]
}
