plugin "google" {
  enabled = true
  version = "0.31.0"
  source  = "github.com/terraform-linters/tflint-ruleset-google"
}

rule "google_storage_bucket_versioning" {
  enabled = true
}
