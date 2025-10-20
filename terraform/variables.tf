variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-east4"
}

variable "env" {
  description = "Environment (test/production)"
  type        = string
  default     = "test"
  validation {
    condition     = contains(["test", "production"], var.env)
    error_message = "Environment must be either 'test' or 'production'."
  }
}

variable "qdrant_cluster_id" {
  description = "Qdrant cluster ID"
  type        = string
}


variable "qdrant_api_key" {
  description = "Qdrant API key"
  type        = string
  sensitive   = true
}

variable "billing_account_id" {
  description = "GCP Billing Account ID (e.g., 000000-000000-000000)"
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email address to receive alert notifications"
  type        = string
  default     = "ad-alerts@example.com"
}

variable "run_service_name" {
  description = "Cloud Run service name to monitor"
  type        = string
  default     = "agent-data-test"
}

variable "sql_instance_name" {
  description = "Name for the managed Cloud SQL instance"
  type        = string
  default     = ""
}

variable "sql_region" {
  description = "Region for the Cloud SQL instance"
  type        = string
  default     = "asia-southeast1"
}

variable "sql_tier" {
  description = "Machine type tier for Cloud SQL"
  type        = string
  default     = "db-f1-micro"
}

variable "sql_database_version" {
  description = "Cloud SQL PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "sql_backup_start_time" {
  description = "Backup start time in HH:MM (24h)"
  type        = string
  default     = "01:00"
}

variable "sql_schedule_timezone" {
  description = "Timezone for the start/stop scheduler"
  type        = string
  default     = "Asia/Ho_Chi_Minh"
}

variable "sql_start_schedule" {
  description = "Cron schedule for starting the Cloud SQL instance"
  type        = string
  default     = "0 8 * * *"
}

variable "sql_stop_schedule" {
  description = "Cron schedule for stopping the Cloud SQL instance"
  type        = string
  default     = "0 18 * * *"
}

variable "sql_scheduler_region" {
  description = "Cloud Scheduler region for the SQL automation jobs"
  type        = string
  default     = "asia-southeast1"
}

variable "sql_deletion_protection" {
  description = "Whether to enable deletion protection on the SQL instance"
  type        = bool
  default     = false
}
