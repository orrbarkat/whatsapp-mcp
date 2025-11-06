output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "service_account_email" {
  description = "Service account email for Cloud Run"
  value       = google_service_account.whatsapp_mcp.email
}

output "cloudsql_connection_name" {
  description = "Cloud SQL connection name for Cloud Run --add-cloudsql-instances flag"
  value       = google_sql_database_instance.whatsapp_mcp.connection_name
}

output "cloudsql_instance_name" {
  description = "Cloud SQL instance name"
  value       = google_sql_database_instance.whatsapp_mcp.name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.whatsapp_mcp.name
}

output "database_user" {
  description = "Database user name"
  value       = google_sql_user.whatsapp_user.name
}

output "database_password" {
  description = "Database user password (sensitive)"
  value       = random_password.db_password.result
  sensitive   = true
}

output "gcs_bucket_name" {
  description = "GCS bucket name for session storage"
  value       = google_storage_bucket.sessions.name
}

output "gcs_bucket_url" {
  description = "GCS bucket URL"
  value       = google_storage_bucket.sessions.url
}

output "secret_database_url_name" {
  description = "Secret Manager secret name for DATABASE_URL"
  value       = google_secret_manager_secret.database_url.secret_id
}

output "secret_supabase_url_name" {
  description = "Secret Manager secret name for SUPABASE_URL"
  value       = google_secret_manager_secret.supabase_url.secret_id
}

output "secret_supabase_key_name" {
  description = "Secret Manager secret name for SUPABASE_KEY"
  value       = google_secret_manager_secret.supabase_key.secret_id
}

output "secret_oauth_client_id_name" {
  description = "Secret Manager secret name for OAuth Client ID"
  value       = google_secret_manager_secret.oauth_client_id.secret_id
}

output "secret_oauth_client_secret_name" {
  description = "Secret Manager secret name for OAuth Client Secret"
  value       = google_secret_manager_secret.oauth_client_secret.secret_id
}

output "cloud_run_deploy_command" {
  description = "Example Cloud Run deployment command"
  value       = <<-EOT
    gcloud run deploy whatsapp-mcp-server \
      --image=gcr.io/${var.project_id}/whatsapp-mcp-server:latest \
      --region=${var.region} \
      --platform=managed \
      --allow-unauthenticated \
      --service-account=${google_service_account.whatsapp_mcp.email} \
      --add-cloudsql-instances=${google_sql_database_instance.whatsapp_mcp.connection_name} \
      --update-secrets=DATABASE_URL=${google_secret_manager_secret.database_url.secret_id}:latest,\
SUPABASE_URL=${google_secret_manager_secret.supabase_url.secret_id}:latest,\
SUPABASE_KEY=${google_secret_manager_secret.supabase_key.secret_id}:latest \
      --set-env-vars=GCS_SESSION_BUCKET=${google_storage_bucket.sessions.name},\
GCS_SESSION_OBJECT_NAME=whatsapp.db,\
MCP_TRANSPORT=sse,\
MCP_PORT=8000
  EOT
}

output "database_connection_command" {
  description = "Command to connect to database via Cloud SQL Proxy"
  value       = <<-EOT
    # Start Cloud SQL Proxy:
    cloud-sql-proxy ${google_sql_database_instance.whatsapp_mcp.connection_name} &

    # Connect with psql:
    psql "host=localhost user=${var.db_user} dbname=${var.db_name}"
    # Password: Use 'terraform output -raw database_password' to retrieve
  EOT
}

output "next_steps" {
  description = "Next steps after Terraform apply"
  value       = <<-EOT
    ✅ Infrastructure provisioned successfully!

    Next steps:

    1. Update Supabase secrets (if using Supabase):
       echo -n 'YOUR_SUPABASE_URL' | gcloud secrets versions add ${google_secret_manager_secret.supabase_url.secret_id} --data-file=-
       echo -n 'YOUR_SUPABASE_KEY' | gcloud secrets versions add ${google_secret_manager_secret.supabase_key.secret_id} --data-file=-

    2. Update OAuth secrets (if OAuth enabled):
       echo -n 'YOUR_CLIENT_ID' | gcloud secrets versions add ${google_secret_manager_secret.oauth_client_id.secret_id} --data-file=-
       echo -n 'YOUR_CLIENT_SECRET' | gcloud secrets versions add ${google_secret_manager_secret.oauth_client_secret.secret_id} --data-file=-

    3. Run database migrations:
       See gcp/DATABASE_SETUP.md for detailed instructions

    4. Build and push Docker image:
       gcloud builds submit --tag gcr.io/${var.project_id}/whatsapp-mcp-server

    5. Deploy to Cloud Run:
       Use the command in 'cloud_run_deploy_command' output

    6. Retrieve database password:
       terraform output -raw database_password
  EOT
}
