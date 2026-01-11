# === GROUP 2: AGENT DATA - TEST ENVIRONMENT ===

resource "google_storage_bucket" "agent_tf_state_test" {
  name                        = "huyen1974-agent-data-tfstate-test" # A1-T
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  versioning { enabled = true }
  lifecycle { prevent_destroy = true }
}

resource "google_storage_bucket" "agent_knowledge_test" {
  name                        = "huyen1974-agent-data-knowledge-test" # A2-T
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle { prevent_destroy = true } # Permanent Knowledge
}

resource "google_storage_bucket" "agent_artifacts_test" {
  name                        = "huyen1974-agent-data-artifacts-test" # A3-T
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle { prevent_destroy = true }
}

resource "google_storage_bucket" "agent_logs_test" {
  name                        = "huyen1974-agent-data-logs-test" # A4-T
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

resource "google_storage_bucket" "agent_snapshots_test" {
  name                        = "huyen1974-agent-data-qdrant-snapshots-test" # A5-T
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

resource "google_storage_bucket" "agent_backup_test" {
  name                        = "huyen1974-agent-data-backup-test" # A6-T
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  versioning { enabled = true }
  lifecycle_rule {
    condition { age = 90 }
    action { type = "Delete" }
  }
}

# === GROUP 3: AGENT DATA - PRODUCTION (RESERVED/EXISTING) ===
# Note: Defining these now to manage them if they exist

resource "google_storage_bucket" "agent_tf_state_prod" {
  name                        = "huyen1974-agent-data-tfstate-production" # A1-P
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  versioning { enabled = true }
  lifecycle { prevent_destroy = true }
}

resource "google_storage_bucket" "agent_knowledge_prod" {
  name                        = "huyen1974-agent-data-knowledge-production" # A2-P
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle { prevent_destroy = true }
}

resource "google_storage_bucket" "agent_artifacts_prod" {
  name                        = "huyen1974-agent-data-artifacts-production" # A3-P
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle { prevent_destroy = true }
}

resource "google_storage_bucket" "agent_logs_prod" {
  name                        = "huyen1974-agent-data-logs-production" # A4-P
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

resource "google_storage_bucket" "agent_snapshots_prod" {
  name                        = "huyen1974-agent-data-qdrant-snapshots-production" # A5-P
  location                    = "ASIA-SOUTHEAST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

# === LEGACY / EXTERNAL ===
resource "google_storage_bucket" "faiss_index" {
  name          = "huyen1974-faiss-index-storage"
  location      = "ASIA-SOUTHEAST1"
  storage_class = "STANDARD"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
