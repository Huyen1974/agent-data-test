terraform {
  required_version = ">= 1.5.7" # Note: CI uses >= 1.8.5
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.46.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "asia-southeast1"
}
