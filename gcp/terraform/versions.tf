terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # Optional: Configure remote state in GCS
  # Uncomment and configure after creating the bucket
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "whatsapp-mcp/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
