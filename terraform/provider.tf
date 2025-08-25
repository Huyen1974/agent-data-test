terraform {
  required_version = ">= 1.5.7" # Note: CI uses >= 1.8.5
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.49"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = "us-east4"
}
