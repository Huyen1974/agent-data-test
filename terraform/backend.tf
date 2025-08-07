terraform {
  backend "gcs" {
    bucket = "huyen1974-agent-data-tfstate-test"
    prefix = "state"
  }
}
