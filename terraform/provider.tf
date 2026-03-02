terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.21"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "asia-southeast1"
}
