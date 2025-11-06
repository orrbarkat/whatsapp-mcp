variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "db_instance_name" {
  description = "Cloud SQL instance name"
  type        = string
  default     = "whatsapp-mcp-db"
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "whatsapp_mcp"
}

variable "db_user" {
  description = "Database user name"
  type        = string
  default     = "whatsapp_user"
}

variable "db_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "db_disk_size_gb" {
  description = "Database disk size in GB"
  type        = number
  default     = 10
}

variable "bucket_name" {
  description = "GCS bucket name for session storage (must be globally unique)"
  type        = string
  default     = ""
}

variable "bucket_location" {
  description = "GCS bucket location"
  type        = string
  default     = "US"
}

variable "service_account_name" {
  description = "Service account name for Cloud Run"
  type        = string
  default     = "whatsapp-mcp-sa"
}

variable "secret_prefix" {
  description = "Prefix for Secret Manager secrets"
  type        = string
  default     = "whatsapp-mcp"
}

variable "enable_backup" {
  description = "Enable automated backups for Cloud SQL"
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "Backup start time in HH:MM format (UTC)"
  type        = string
  default     = "03:00"
}

variable "enable_private_ip" {
  description = "Enable private IP for Cloud SQL (requires VPC setup)"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default = {
    application = "whatsapp-mcp"
    managed-by  = "terraform"
  }
}
