# GCP API Requirements

This document lists all Google Cloud APIs required for the WhatsApp MCP server deployment.

## Required APIs

The following APIs must be enabled in your GCP project before deploying:

### Core Services

1. **Cloud Run API** (`run.googleapis.com`)
   - Required for deploying and running the containerized MCP server
   - Manages serverless container execution

2. **Cloud SQL Admin API** (`sqladmin.googleapis.com`)
   - Required for Cloud SQL PostgreSQL database management
   - Enables database instance creation, configuration, and connections

3. **Cloud Storage API** (`storage-api.googleapis.com`)
   - Required for GCS bucket operations
   - Manages session data and file storage

4. **Cloud Storage Component API** (`storage-component.googleapis.com`)
   - Required for GCS client library functionality
   - Supports advanced storage features

5. **Secret Manager API** (`secretmanager.googleapis.com`)
   - Required for storing sensitive configuration
   - Manages DATABASE_URL, SUPABASE credentials, and OAuth secrets

6. **Artifact Registry API** (`artifactregistry.googleapis.com`)
   - Required for Docker image storage
   - Cloud Run pulls container images from Artifact Registry

7. **Cloud Build API** (`cloudbuild.googleapis.com`)
   - Required for building Docker images
   - Automates containerization of the application

### Optional but Recommended

8. **Service Networking API** (`servicenetworking.googleapis.com`)
   - Optional: For VPC peering with Cloud SQL (private IP)
   - Enhances security by enabling private connectivity

9. **Compute Engine API** (`compute.googleapis.com`)
   - Optional: Required if using VPC networks or private Cloud SQL
   - Manages networking resources

10. **Cloud Resource Manager API** (`cloudresourcemanager.googleapis.com`)
    - Optional: For project-level IAM and resource management
    - Useful for Terraform automation

## Enabling APIs

### Using gcloud CLI

Enable all required APIs at once:

```bash
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  storage-api.googleapis.com \
  storage-component.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project=YOUR_PROJECT_ID
```

Enable optional APIs:

```bash
gcloud services enable \
  servicenetworking.googleapis.com \
  compute.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project=YOUR_PROJECT_ID
```

### Using the GCP Console

1. Navigate to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
2. Search for each API by name
3. Click "Enable" for each required API

### Using Terraform

APIs are automatically enabled when using the Terraform configuration in `gcp/terraform/main.tf`:

```bash
cd gcp/terraform
terraform init
terraform plan
terraform apply
```

## Verification

Check which APIs are currently enabled:

```bash
gcloud services list --enabled --project=YOUR_PROJECT_ID
```

Check if a specific API is enabled:

```bash
gcloud services list --enabled \
  --filter="name:run.googleapis.com" \
  --project=YOUR_PROJECT_ID
```

## Troubleshooting

### API Not Enabled Error

If you encounter errors like:
```
Error 403: Cloud Run API has not been used in project XXX before or it is disabled.
```

Enable the specific API:
```bash
gcloud services enable run.googleapis.com --project=YOUR_PROJECT_ID
```

### Permission Denied

Ensure your user account has the following IAM roles:
- `roles/serviceusage.serviceUsageAdmin` (to enable APIs)
- `roles/owner` or `roles/editor` (for full project access)

Check your permissions:
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

### Quota Exceeded

Some APIs have quota limits. Check quotas:
```bash
gcloud services list --enabled --project=YOUR_PROJECT_ID
```

View quota details in the [GCP Console](https://console.cloud.google.com/iam-admin/quotas).

## API Costs

Most APIs are free to enable. Costs are incurred based on usage:

- **Cloud Run**: Pay per request and compute time
- **Cloud SQL**: Pay per instance uptime and storage
- **Cloud Storage**: Pay per GB stored and data transfer
- **Secret Manager**: Free tier available, then pay per secret/access
- **Cloud Build**: Free tier includes 120 build-minutes per day

Refer to [GCP Pricing](https://cloud.google.com/pricing) for detailed cost information.

## Automated Setup

The `gcp/setup.sh` script automatically enables all required APIs:

```bash
export GCP_PROJECT_ID=your-project-id
./gcp/setup.sh
```

This ensures all APIs are enabled before provisioning resources.
