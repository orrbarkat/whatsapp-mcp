# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Service Account for Cloud Run
resource "google_service_account" "whatsapp_mcp" {
  account_id   = var.service_account_name
  display_name = "WhatsApp MCP Service Account"
  description  = "Service account for WhatsApp MCP Cloud Run service"
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

# IAM binding: Cloud SQL Client role
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.whatsapp_mcp.email}"
}

# IAM binding: Secret Manager Secret Accessor role
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.whatsapp_mcp.email}"
}

# Generate random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Cloud SQL Instance
resource "google_sql_database_instance" "whatsapp_mcp" {
  name             = var.db_instance_name
  database_version = var.db_version
  region           = var.region
  project          = var.project_id

  settings {
    tier              = var.db_tier
    disk_type         = "PD_SSD"
    disk_size         = var.db_disk_size_gb
    disk_autoresize   = true
    availability_type = "ZONAL"

    backup_configuration {
      enabled            = var.enable_backup
      start_time         = var.backup_start_time
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7  # Sunday
      hour         = 4  # 4 AM
      update_track = "stable"
    }

    ip_configuration {
      ipv4_enabled    = !var.enable_private_ip
      private_network = var.enable_private_ip ? "projects/${var.project_id}/global/networks/default" : null
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = false

  depends_on = [google_project_service.required_apis]
}

# Database
resource "google_sql_database" "whatsapp_mcp" {
  name     = var.db_name
  instance = google_sql_database_instance.whatsapp_mcp.name
  project  = var.project_id
}

# Database User
resource "google_sql_user" "whatsapp_user" {
  name     = var.db_user
  instance = google_sql_database_instance.whatsapp_mcp.name
  password = random_password.db_password.result
  project  = var.project_id
}

# GCS Bucket for session storage
resource "google_storage_bucket" "sessions" {
  name          = var.bucket_name != "" ? var.bucket_name : "${var.project_id}-whatsapp-mcp-sessions"
  location      = var.bucket_location
  project       = var.project_id
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

# IAM binding: Storage Object Admin for service account on bucket
resource "google_storage_bucket_iam_member" "sessions_object_admin" {
  bucket = google_storage_bucket.sessions.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.whatsapp_mcp.email}"
}

# Secret Manager: DATABASE_URL
resource "google_secret_manager_secret" "database_url" {
  secret_id = "${var.secret_prefix}-database-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id

  secret_data = "postgresql://${var.db_user}:${random_password.db_password.result}@localhost/${var.db_name}?host=/cloudsql/${google_sql_database_instance.whatsapp_mcp.connection_name}"
}

# Secret Manager: SUPABASE_URL (placeholder - must be updated manually)
resource "google_secret_manager_secret" "supabase_url" {
  secret_id = "${var.secret_prefix}-supabase-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "supabase_url" {
  secret = google_secret_manager_secret.supabase_url.id

  # Placeholder value - update with actual Supabase URL or use Cloud SQL Postgres URL
  secret_data = "https://your-project.supabase.co"
}

# Secret Manager: SUPABASE_KEY (placeholder - must be updated manually)
resource "google_secret_manager_secret" "supabase_key" {
  secret_id = "${var.secret_prefix}-supabase-key"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "supabase_key" {
  secret = google_secret_manager_secret.supabase_key.id

  # Placeholder value - update with actual Supabase anon/service key
  secret_data = "your-supabase-anon-key"
}

# Secret Manager: OAuth Client ID (placeholder - optional)
resource "google_secret_manager_secret" "oauth_client_id" {
  secret_id = "${var.secret_prefix}-oauth-client-id"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "oauth_client_id" {
  secret = google_secret_manager_secret.oauth_client_id.id

  secret_data = "your-oauth-client-id"
}

# Secret Manager: OAuth Client Secret (placeholder - optional)
resource "google_secret_manager_secret" "oauth_client_secret" {
  secret_id = "${var.secret_prefix}-oauth-client-secret"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "oauth_client_secret" {
  secret = google_secret_manager_secret.oauth_client_secret.id

  secret_data = "your-oauth-client-secret"
}

# Secret Manager: Session Database DSN (optional - for Supabase session storage)
resource "google_secret_manager_secret" "session_dsn" {
  secret_id = "${var.secret_prefix}-session-dsn"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = var.labels

  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "session_dsn" {
  secret = google_secret_manager_secret.session_dsn.id

  # Placeholder value - update with actual Supabase Postgres DSN for session storage
  # Example: postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
  # Note: If not set, defaults to DATABASE_URL or local SQLite
  secret_data = "postgresql://postgres:your-password@db.your-project.supabase.co:5432/postgres?sslmode=require"
}
