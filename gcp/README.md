# Google Cloud Run Deployment

This guide has been consolidated and enhanced. Please see:

## [Complete Cloud Run Deployment Guide](../docs/deployment/cloud-run.md)

The comprehensive Cloud Run deployment guide includes:

- **Prerequisites and API Setup** - Required GCP APIs and tools
- **OAuth 2.1 Authentication** - Complete OAuth setup with Google Identity Platform
- **Database Configuration** - Cloud SQL, Supabase, and session storage options
- **Service Account and IAM** - Minimal required permissions
- **Deployment Steps** - Build, push, and deploy to Cloud Run
- **Monitoring and Alerts** - Logging, uptime checks, and error reporting
- **Cost Optimization** - Pricing estimates and optimization tips
- **Security Hardening** - IAM roles, network security, and secrets management
- **Troubleshooting** - Common issues and solutions

---

## Cloud Build Setup

This section covers automating your deployment to Cloud Run using Google Cloud Build. Cloud Build provides continuous integration and deployment from your code repository (GitHub or Cloud Source Repositories) to Cloud Run.

### Environment Variables Setup

Before running any commands, set these environment variables:

```bash
# Required: Your GCP project ID
export PROJECT_ID="your-project-id"

# Optional: Customize these or use defaults
export REGION="${REGION:-europe-west6}"
export REPOSITORY="${REPOSITORY:-whatsapp-mcp}"
export SERVICE_NAME="${SERVICE_NAME:-whatsapp-mcp-server}"

# Set as active project
gcloud config set project ${PROJECT_ID}
```

### Prerequisites

#### Required APIs

Enable these APIs before setting up Cloud Build:

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com
```

**API Purposes**:
- `cloudbuild.googleapis.com` - Build automation and CI/CD
- `run.googleapis.com` - Cloud Run service deployment
- `artifactregistry.googleapis.com` - Container image storage
- `secretmanager.googleapis.com` - Secure credential management
- `sqladmin.googleapis.com` - Cloud SQL administration (if used)

#### Required Secrets

Create the following secrets in Secret Manager before deployment:

**Required for all deployments:**
```bash
# OAuth Client ID (from Google Cloud Console)
echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
  gcloud secrets create whatsapp-mcp-google-client-id \
  --project=${PROJECT_ID} \
  --replication-policy="automatic" \
  --data-file=-
```

**When using PostgreSQL/Supabase for session storage:**
```bash
# Database connection string for session storage
echo -n "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?sslmode=require" | \
  gcloud secrets create whatsapp-mcp-database-url \
  --project=${PROJECT_ID} \
  --replication-policy="automatic" \
  --data-file=-
```

**Note**: If using SQLite-only deployment (with GCS backup), you can either:
- Omit the `DATABASE_URL` secret entirely and remove it from `cloudbuild.yaml`
- Create a placeholder secret with value `sqlite::memory:` (not used but prevents deployment errors)

See [SECRETS_REFERENCE.md](../SECRETS_REFERENCE.md) for complete secret configuration.

#### Artifact Registry Setup

Cloud Build pushes container images to Artifact Registry:

```bash
# Create repository (if not exists)
gcloud artifacts repositories create ${REPOSITORY} \
  --repository-format=docker \
  --location=${REGION} \
  --project=${PROJECT_ID} \
  --description="WhatsApp MCP Server container images"

# Verify repository
gcloud artifacts repositories describe ${REPOSITORY} \
  --location=${REGION} \
  --project=${PROJECT_ID}
```

Repository URL format: `${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/IMAGE`

#### IAM Roles for Cloud Build Service Account

Grant the Cloud Build service account necessary permissions:

```bash
# Get Cloud Build service account email
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} \
  --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Grant required roles
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/artifactregistry.writer"
```

**Roles Explained**:
- `roles/run.admin` - Deploy and manage Cloud Run services
- `roles/iam.serviceAccountUser` - Act as the runtime service account
- `roles/artifactregistry.writer` - Push container images

### Repository Connection Options

Cloud Build supports two repository types:

**Option A: GitHub (Recommended)**
- Connect via GitHub App for secure access
- Automatic webhook configuration
- No code mirroring required
- Best for external GitHub repositories

**Option B: Cloud Source Repositories (CSR)**
- Managed Git hosting on GCP
- Native integration with Cloud Build
- Requires repository mirroring or direct push
- Best for internal projects or private repos

### Automated Setup

Use the provided setup script to automate Cloud Build configuration:

```bash
# Run automated setup
./gcp/cloudbuild-setup.sh
```

**Available Flags**:
- `--skip-trigger` or `--no-trigger` - Set up infrastructure without creating build trigger
- `--help` or `-h` - Display usage information

**Environment Variables**:
- `REGION` - GCP region (default: `us-central1`)
- `REPOSITORY` - Artifact Registry repository name (default: `whatsapp-mcp`)
- `SERVICE_NAME` - Cloud Run service name (default: `whatsapp-mcp`)

**Examples**:
```bash
# Full setup with default settings
./gcp/cloudbuild-setup.sh

# Setup with custom region and service name
REGION=us-central1 SERVICE_NAME=whatsapp-mcp ./gcp/cloudbuild-setup.sh

# Infrastructure only, manual trigger later
./gcp/cloudbuild-setup.sh --skip-trigger
```

The script performs:
1. Validates prerequisites and authentication
2. Enables required APIs
3. Creates Artifact Registry repository
4. Configures Cloud Build service account IAM
5. Creates build trigger (unless `--skip-trigger` is set)
6. Optionally tests manual build

### Manual Trigger Creation

If you skipped trigger creation or need to create additional triggers:

#### Option A: GitHub Repository Trigger

**Via gcloud CLI**:
```bash
# Prerequisites: Create GitHub App connection first
# Visit: https://console.cloud.google.com/cloud-build/connections

# Get connection and repository resource names
CONNECTION_NAME="git"
REPO_NAME="orrbarkat-whatsapp-mcp"

# Full repository resource path
REPOSITORY_RESOURCE="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION_NAME}/repositories/${REPO_NAME}"

# Create trigger
gcloud builds triggers create github \
  --name="whatsapp-mcp-main-trigger" \
  --repository="${REPOSITORY_RESOURCE}" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --region="${REGION}" \
  --project=${PROJECT_ID} \
  --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}"
```

**Via Google Cloud Console**:
1. Visit [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **Create Trigger**
3. Configure:
   - **Name**: `whatsapp-mcp-main-trigger`
   - **Region**: Select your region (e.g., `us-central1`)
   - **Event**: Push to branch
   - **Source**: Select your GitHub connection and repository
   - **Branch**: `^main$` (regex pattern)
   - **Build Configuration**: Cloud Build configuration file
   - **Location**: `cloudbuild.yaml`
4. Add substitution variables:
   - `_REGION`: `us-central1`
   - `_REPOSITORY`: `whatsapp-mcp`
   - `_SERVICE_NAME`: `whatsapp-mcp`
5. Click **Create**

**Setting up GitHub Connection** (required first):
1. Visit [Cloud Build Connections](https://console.cloud.google.com/cloud-build/connections)
2. Click **Create Connection**
3. Select **GitHub** and follow OAuth flow
4. Connect your repository through [Cloud Build Repositories](https://console.cloud.google.com/cloud-build/repositories)

#### Option B: Cloud Source Repositories Trigger

**Via gcloud CLI**:
```bash
# Prerequisites: Create CSR repository first
gcloud source repos create ${REPOSITORY} --project=${PROJECT_ID}
# Then push your code to CSR

# Create trigger
gcloud builds triggers create cloud-source-repositories \
  --name="whatsapp-mcp-main-trigger" \
  --repo="${REPOSITORY}" \
  --branch-pattern="^main$" \
  --build-config="cloudbuild.yaml" \
  --region="${REGION}" \
  --project=${PROJECT_ID} \
  --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}"
```

**Via Google Cloud Console**:
1. Create CSR repository:
   ```bash
   gcloud source repos create ${REPOSITORY} --project=${PROJECT_ID}
   ```
2. Visit [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
3. Click **Create Trigger**
4. Configure:
   - **Name**: `whatsapp-mcp-main-trigger`
   - **Region**: Your region (e.g., `us-central1`)
   - **Event**: Push to branch
   - **Source**: Cloud Source Repository
   - **Repository**: Your repository name
   - **Branch**: `^main$`
   - **Build Configuration**: `cloudbuild.yaml`
5. Add substitution variables (same as GitHub option)

**Verification Commands**:
```bash
# List all triggers
gcloud builds triggers list --region=${REGION} --project=${PROJECT_ID}

# Describe specific trigger
gcloud builds triggers describe whatsapp-mcp-main-trigger \
  --region=${REGION} --project=${PROJECT_ID}

# Test trigger manually
gcloud builds triggers run whatsapp-mcp-main-trigger \
  --region=${REGION} --project=${PROJECT_ID}
```

### Understanding cloudbuild.yaml

The `cloudbuild.yaml` file defines the build and deployment pipeline.

#### Substitution Variables

Customize behavior without editing the file:

```yaml
substitutions:
  _REGION: europe-west6              # Cloud Run deployment region
  _REPOSITORY: whatsapp-mcp         # Artifact Registry repository
  _SERVICE_NAME: whatsapp-mcp-server       # Cloud Run service name
  _IMAGE_TAG: ${SHORT_SHA}          # Git commit SHA (auto-populated)
  _SERVICE_ACCOUNT: whatsapp-mcp@${PROJECT_ID}.iam.gserviceaccount.com # Cloud Run service account
  _GCS_SESSION_BUCKET: ${PROJECT_ID}-whatsapp-sessions
```

Override when submitting builds:
```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --substitutions=_REGION=${REGION},_SERVICE_NAME=${SERVICE_NAME}
```

#### Build Steps Explained

**Step 1: Build Docker Image**
```yaml
- name: 'gcr.io/cloud-builders/docker'
  id: 'build-image'
  args: ['build', '-t', 'IMAGE_URL', '.']
```
Builds container from `Dockerfile`, tags with commit SHA and `latest`.

**Step 2: Push to Artifact Registry**
```yaml
- name: 'gcr.io/cloud-builders/docker'
  id: 'push-image-sha'
  args: ['push', 'IMAGE_URL']
```
Uploads container images to Artifact Registry.

**Step 3: Deploy to Cloud Run**
```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'deploy-cloud-run'
  entrypoint: 'gcloud'
  args: ['run', 'deploy', ...]
```
Deploys the new image to Cloud Run with environment variables and secrets.

#### Environment Variables

Configured in the deploy step:
```yaml
--set-env-vars=\
  MCP_TRANSPORT=sse,\
  PORT=3000,\
  WHATSAPP_BRIDGE_URL=http://localhost:8080,\
  GCS_SESSION_BUCKET=${_GCS_SESSION_BUCKET},\
  OAUTH_ENABLED=true,\
  LOG_LEVEL=INFO
```

**Key Variables Explained**:
- `WHATSAPP_BRIDGE_URL`: URL to the Go WhatsApp bridge. Default is `http://localhost:8080` because the bridge runs in the same container. If you deploy the bridge as a separate service, update this to the external service URL (e.g., `https://bridge-service.run.app`).
- `PORT` / `MCP_PORT`: Container port for the MCP server (default: 3000)
- `MCP_TRANSPORT`: Transport protocol (default: `sse` for Server-Sent Events)
- `GCS_SESSION_BUCKET`: GCS bucket for SQLite session backup (only used with SQLite storage)
- `OAUTH_ENABLED`: Enable OAuth 2.1 authentication for remote access

Modify these in `cloudbuild.yaml` or override via substitutions.

#### Secrets Configuration

Mounted from Secret Manager:
```yaml
--update-secrets=\
  GOOGLE_CLIENT_ID=whatsapp-mcp-google-client-id:latest,\
  DATABASE_URL=whatsapp-mcp-database-url:latest
```

Ensure secrets exist before deployment. See [Required Secrets](#required-secrets) above.

#### Resource Settings

```yaml
--cpu=2                   # vCPUs allocated
--memory=2Gi              # Memory allocation
--min-instances=0         # Scale to zero when idle
--max-instances=10        # Maximum concurrent instances
--concurrency=80          # Requests per instance
--timeout=300             # Request timeout (seconds)
```

Adjust based on workload requirements.

#### Health Checks

```yaml
--startup-probe-path=/health    # Initial readiness check
--liveness-probe-path=/health   # Ongoing health monitoring
```

The server must respond 200 OK at `/health` endpoint.

#### Build Options

```yaml
options:
  machineType: 'N1_HIGHCPU_8'     # Fast build machine
  logging: CLOUD_LOGGING_ONLY      # Log destination
  substitutionOption: 'ALLOW_LOOSE' # Allow missing substitutions
timeout: 1800s                      # 30 minute build timeout
```

### Testing Cloud Build

#### Local Docker Build (Pre-flight Check)

```bash
# Build locally to verify Dockerfile
docker build -t whatsapp-mcp-test .

# Test container locally
docker run -p 3000:3000 \
  -e OAUTH_ENABLED=false \
  -e MCP_TRANSPORT=sse \
  -e PORT=3000 \
  whatsapp-mcp-test

# Health check
curl http://localhost:3000/health
```

#### Manual Build Submission

```bash
# Submit build manually (doesn't require trigger)
gcloud builds submit \
  --config=cloudbuild.yaml \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --substitutions=_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}

# Monitor build progress
gcloud builds list --ongoing --region=${REGION} --project=${PROJECT_ID}

# View build logs
BUILD_ID=$(gcloud builds list --region=${REGION} --project=${PROJECT_ID} \
  --limit=1 --format="value(id)")
gcloud builds log ${BUILD_ID} --region=${REGION} --project=${PROJECT_ID}
```

#### Validate Deployment

```bash
# Check Cloud Run service
gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} --project=${PROJECT_ID}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --format="value(status.url)")

# Test health endpoint
curl "${SERVICE_URL}/health"

# Check Artifact Registry images
gcloud artifacts docker images list \
  ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME} \
  --project=${PROJECT_ID}
```

### Troubleshooting Cloud Build

#### Build Fails: Permission Denied

**Symptom**: Build fails with IAM permission errors.

**Solution**:
```bash
# Verify Cloud Build SA has required roles
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} \
  --format="value(projectNumber)")
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud projects get-iam-policy ${PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:${CLOUDBUILD_SA}"

# Re-grant roles if missing
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/run.admin"
```

#### Build Fails: Secret Not Found

**Symptom**: `ERROR: Secret 'whatsapp-mcp-database-url' not found`

**Solution**:
```bash
# Verify secret exists
gcloud secrets describe whatsapp-mcp-database-url --project=${PROJECT_ID}

# If missing, create it
echo -n "YOUR_DATABASE_URL" | \
  gcloud secrets create whatsapp-mcp-database-url \
  --project=${PROJECT_ID} \
  --replication-policy="automatic" \
  --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding whatsapp-mcp-database-url \
  --project=${PROJECT_ID} \
  --member="serviceAccount:whatsapp-mcp@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Build Fails: Artifact Registry Not Found

**Symptom**: `ERROR: Repository '${REPOSITORY}' not found`

**Solution**:
```bash
# Create repository
gcloud artifacts repositories create ${REPOSITORY} \
  --repository-format=docker \
  --location=${REGION} \
  --project=${PROJECT_ID}

# Verify creation
gcloud artifacts repositories list \
  --location=${REGION} --project=${PROJECT_ID}
```

#### Trigger Not Firing

**Symptom**: Pushing to GitHub/CSR doesn't trigger build.

**Solution**:
```bash
# Verify trigger exists and is active
gcloud builds triggers list --region=${REGION} --project=${PROJECT_ID}

# Check trigger configuration
gcloud builds triggers describe whatsapp-mcp-main-trigger \
  --region=${REGION} --project=${PROJECT_ID}

# For GitHub: Verify webhook is configured
# Visit: https://console.cloud.google.com/cloud-build/repositories

# Test trigger manually
gcloud builds triggers run whatsapp-mcp-main-trigger \
  --region=${REGION} --project=${PROJECT_ID}
```

#### Deployment Succeeds but Service Unhealthy

**Symptom**: Build completes but Cloud Run service fails health checks.

**Solution**:
```bash
# Check Cloud Run logs
gcloud run services logs read ${SERVICE_NAME} \
  --region=${REGION} --project=${PROJECT_ID} --limit=50

# Common issues:
# 1. Missing environment variables
# 2. Secret access denied
# 3. Bridge not starting (WHATSAPP_BRIDGE_URL misconfigured)
# 4. Database connection failure

# Verify secrets are accessible
gcloud secrets get-iam-policy whatsapp-mcp-google-client-id \
  --project=${PROJECT_ID}

# Test service manually
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} --project=${PROJECT_ID} --format="value(status.url)")
curl -v "${SERVICE_URL}/health"
```

#### Build Times Out

**Symptom**: `ERROR: Build timed out after 1800s`

**Solution**:
```bash
# Increase timeout in cloudbuild.yaml
# Edit: timeout: 3600s  # 60 minutes

# Or use faster machine type
# Edit options.machineType: 'E2_HIGHCPU_32'

# Check for slow steps
gcloud builds log BUILD_ID --region=${REGION} --project=${PROJECT_ID}
```

#### Substitution Variable Errors

**Symptom**: `ERROR: Substitution variable '_REGION' not found`

**Solution**:
```bash
# Ensure all required substitutions are provided
gcloud builds submit \
  --config=cloudbuild.yaml \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --substitutions=_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}

# Or set defaults in cloudbuild.yaml substitutions section
```

**Useful Debugging Commands**:
```bash
# List recent builds
gcloud builds list --region=${REGION} --project=${PROJECT_ID} --limit=10

# View detailed build log
gcloud builds log BUILD_ID --region=${REGION} --project=${PROJECT_ID}

# Check service health
gcloud run services describe ${SERVICE_NAME} \
  --region=${REGION} --project=${PROJECT_ID}

# View Cloud Run logs
gcloud run services logs read ${SERVICE_NAME} \
  --region=${REGION} --project=${PROJECT_ID}

# Test local build
docker build -t test-image .
docker run -p 3000:3000 -e OAUTH_ENABLED=false test-image
```

**Console Links**:
- [Cloud Build History](https://console.cloud.google.com/cloud-build/builds)
- [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
- [Connections & Repositories](https://console.cloud.google.com/cloud-build/repositories)
- [Artifact Registry](https://console.cloud.google.com/artifacts)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager)
- [Cloud Run Services](https://console.cloud.google.com/run)

---

## Cloud Run Deployment

**For automated deployments using Cloud Build, see the [Cloud Build Setup](#cloud-build-setup) section above.**

This section covers manual deployment using gcloud commands. Cloud Build can automate these steps with continuous deployment from your repository.

For detailed deployment instructions including OAuth setup, database configuration, and production best practices, see the [Complete Cloud Run Deployment Guide](../docs/deployment/cloud-run.md).

## Quick Links

- **[Main README](../README.md)** - Getting started and local setup
- **[Database Configuration](../docs/database.md)** - SQLite, PostgreSQL, Supabase options
- **[Migrations Guide](../docs/migrations.md)** - Database schema setup
- **[Environment Variables](../SECRETS_REFERENCE.md)** - Complete secrets reference
- **[Troubleshooting](../docs/troubleshooting.md)** - Common issues

## Legacy Files (Archived)

The following files have been consolidated into the main deployment guide:

- `DATABASE_SETUP.md` → See [docs/deployment/cloud-run.md#database-setup](../docs/deployment/cloud-run.md#database-setup)
- `API_REQUIREMENTS.md` → See [docs/deployment/cloud-run.md#prerequisites](../docs/deployment/cloud-run.md#prerequisites)
- `env-template.yaml` - Still available for reference

## Helper Scripts

This directory contains useful automation scripts:

- **`setup.sh`** - Automated GCP resource provisioning
- **`terraform/`** - Infrastructure as code for Cloud Run deployment

See the [deployment guide](../docs/deployment/cloud-run.md) for usage instructions.
