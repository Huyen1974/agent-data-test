# GCS Buckets for agent-data-langroid
# Each bucket is individually defined for easier import and management

locals {
  bucket_types = {
    artifacts        = "artifacts"
    knowledge        = "knowledge"
    logs             = "logs"
    qdrant_snapshots = "qdrant-snapshots"
    source           = "source"
    tfstate          = "tfstate"
  }
}

resource "google_storage_bucket" "huyen1974_agent_data_artifacts_test" {
  project       = var.project_id
  name          = "huyen1974-agent-data-artifacts-${var.env}"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  force_destroy = false
  iam_configuration {
    uniform_bucket_level_access = true
  }
  public_access_prevention = "inherited"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    environment = var.env
    project     = "agent-data-langroid"
    managed_by  = "terraform"
    bucket_type = local.bucket_types.artifacts
  }
}

resource "google_storage_bucket" "huyen1974_agent_data_knowledge_test" {
  project       = var.project_id
  name          = "huyen1974-agent-data-knowledge-${var.env}"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  force_destroy = false
  iam_configuration {
    uniform_bucket_level_access = true
  }
  public_access_prevention = "inherited"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    environment = var.env
    project     = "agent-data-langroid"
    managed_by  = "terraform"
    bucket_type = local.bucket_types.knowledge
  }
}

resource "google_storage_bucket" "huyen1974_agent_data_logs_test" {
  project       = var.project_id
  name          = "huyen1974-agent-data-logs-${var.env}"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  force_destroy = false
  iam_configuration {
    uniform_bucket_level_access = true
  }
  public_access_prevention = "inherited"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    environment = var.env
    project     = "agent-data-langroid"
    managed_by  = "terraform"
    bucket_type = local.bucket_types.logs
  }
}

resource "google_storage_bucket" "huyen1974_agent_data_qdrant_snapshots_test" {
  project       = var.project_id
  name          = "huyen1974-agent-data-qdrant-snapshots-${var.env}"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  force_destroy = false
  iam_configuration {
    uniform_bucket_level_access = true
  }
  public_access_prevention = "inherited"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    environment = var.env
    project     = "agent-data-langroid"
    managed_by  = "terraform"
    bucket_type = local.bucket_types.qdrant_snapshots
  }
}

resource "google_storage_bucket" "huyen1974_agent_data_source_test" {
  project       = var.project_id
  name          = "huyen1974-agent-data-source-${var.env}"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  force_destroy = false
  iam_configuration {
    uniform_bucket_level_access = true
  }
  public_access_prevention = "inherited"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    environment = var.env
    project     = "agent-data-langroid"
    managed_by  = "terraform"
    bucket_type = local.bucket_types.source
  }
}

resource "google_storage_bucket" "huyen1974_agent_data_tfstate_test" {
  project       = var.project_id
  name          = "huyen1974-agent-data-tfstate-${var.env}"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  force_destroy = false
  iam_configuration {
    uniform_bucket_level_access = true
  }
  public_access_prevention = "inherited"

  versioning {
    enabled = true
  }

  lifecycle {
    prevent_destroy = true
  }

  labels = {
    environment = var.env
    project     = "agent-data-langroid"
    managed_by  = "terraform"
    bucket_type = local.bucket_types.tfstate
  }
}
