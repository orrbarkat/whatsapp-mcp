# Cloud Run Deployment

This comprehensive guide covers deploying the WhatsApp MCP Server to Google Cloud Platform using Cloud Run, including OAuth 2.1 authentication, database setup, and security best practices.

## Overview

Deploy the WhatsApp MCP server to Google Cloud Platform with:

- **Cloud Run**: Containerized MCP server with automatic scaling and OAuth protection
- **Supabase**: Managed PostgreSQL database via REST API for message storage (optional)
- **Cloud Storage**: GCS bucket for WhatsApp session persistence and backup
- **Secret Manager**: Secure storage for OAuth credentials and database configuration
- **Identity Platform**: OAuth 2.1 authentication for secure remote client access

**Note**: The current implementation uses SQLite by default or Supabase REST API for database access. Direct PostgreSQL/Cloud SQL connectivity is not currently supported.

## Prerequisites

### 1. Google Cloud SDK

```bash
# Install Google Cloud SDK
brew install google-cloud-sdk   # macOS

# Or download from https://cloud.google.com/sdk/docs/install

# Configure SDK
gcloud init
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Required APIs

Enable necessary Google Cloud APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  iamcredentials.googleapis.com \
  identitytoolkit.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

**API Purposes**:
- **Cloud Run**: Serverless container execution
- **Secret Manager**: Secure credential storage
- **Cloud Storage**: Session backup storage
- **IAM Credentials**: Service account authentication
- **Identity Toolkit**: OAuth 2.1 identity management
- **Cloud Build**: Container image building
- **Artifact Registry**: Container image storage

### 3. Development Tools

- Docker Desktop (for building container images)
- Terraform (optional, for infrastructure as code)
- PostgreSQL client tools (for database setup)

## OAuth 2.1 Configuration

### Authentication Overview

The WhatsApp MCP server uses OAuth 2.1 for secure client authentication when deployed remotely:

1. **Authentication Flow:**
   - Client obtains Bearer token from Google Identity Platform
   - Token included in Authorization header with each request
   - Server validates JWT token signature and claims
   - Only authorized clients can access the MCP server

2. **Security Benefits:**
   - Modern OAuth 2.1 protocol with enhanced security
   - JWT-based token validation with audience checking
   - Automatic token expiration and rotation
   - Secure client credentials storage in Secret Manager
   - Token-based access control for multi-user deployments

### Step 1: Configure OAuth Consent Screen

```bash
# Open OAuth consent screen configuration
open "https://console.cloud.google.com/apis/credentials/consent"

# Configure settings:
# - User Type: Internal (recommended) or External
# - App Name: "WhatsApp MCP Server"
# - Support Email: Your team's email
# - Developer Contact: Your team's email
```

**Configuration Options**:
- **Internal**: Limits access to organization members only (recommended)
- **External**: Allows access to any Google account (requires verification)

### Step 2: Create OAuth 2.0 Client ID

```bash
# Navigate to Credentials page
open "https://console.cloud.google.com/apis/credentials"

# Click "Create Credentials" → "OAuth 2.0 Client ID"
# Choose application type based on your client:
# - Web Application: For browser-based clients
# - Desktop Application: For CLI tools
```

**Configuration**:
- **Name**: WhatsApp MCP Client
- **Authorized redirect URIs**: (for web apps) Your application URLs
- **Authorized JavaScript origins**: (for web apps) Your domain

### Step 3: Store OAuth Credentials in Secret Manager

```bash
# Store OAuth Client ID
echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
  gcloud secrets create whatsapp-mcp-google-client-id \
  --replication-policy="automatic" \
  --data-file=-

# Store OAuth Audience (should match Client ID for Google ID tokens)
echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
  gcloud secrets create whatsapp-mcp-oauth-audience \
  --replication-policy="automatic" \
  --data-file=-
```

**Important**: For Google ID tokens, the audience claim equals the OAuth Client ID.

## Database Setup

### Option A: SQLite with GCS Backup (Default)

**Overview**: Uses SQLite for storage with automatic GCS backup for session persistence.

**Note**: GCS session backup only works with SQLite session storage. For production, consider Option B (Supabase) instead.

**1. Create GCS Bucket:**
```bash
# Create bucket for session storage
gcloud storage buckets create gs://YOUR_PROJECT-whatsapp-sessions \
  --location=us-central1 \
  --uniform-bucket-level-access
```

**2. Configure Encryption (Optional):**
```bash
# Create encryption key
gcloud kms keyrings create whatsapp-mcp \
  --location=us-central1

gcloud kms keys create sessions-key \
  --keyring=whatsapp-mcp \
  --location=us-central1 \
  --purpose=encryption

# Configure bucket encryption
gcloud storage buckets update gs://YOUR_PROJECT-whatsapp-sessions \
  --default-kms-key=projects/YOUR_PROJECT/locations/us-central1/keyRings/whatsapp-mcp/cryptoKeys/sessions-key
```

**3. Environment Configuration:**
```bash
# Set GCS bucket for session backup
GCS_SESSION_BUCKET=YOUR_PROJECT-whatsapp-sessions
GCS_SESSION_OBJECT_NAME=whatsapp.db
```

### Option B: Supabase PostgreSQL (Recommended for Production)

**Overview**: Store WhatsApp sessions and messages in Supabase Postgres for better persistence and multi-instance support.

#### Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and keys from Settings → API

#### Step 2: Run Message Tables Migration

```bash
# Set your Supabase DATABASE_URL
export DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres?sslmode=require"

# Run base schema migration (required)
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# Run additional migrations
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/001_create_chat_list_view.sql
```

**Or use Supabase Dashboard**:
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy contents of `000_create_bridge_tables.sql`
4. Paste and execute

#### Step 3: Run Session Tables Migration

```bash
# Using Supabase SQL Editor (Recommended)
# 1. Go to Supabase project dashboard
# 2. Navigate to SQL Editor
# 3. Copy contents of whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
# 4. Paste and execute

# Or using psql
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
```

This creates 13 session tables: `devices`, `identities`, `prekeys`, `sessions`, `sender_keys`, `signed_prekeys`, `app_state_sync_keys`, `app_state_version`, `app_state_mutation_macs`, `contacts`, `chat_settings`, `message_secrets`, `privacy_tokens`.

#### Step 4: Verify Tables

```sql
-- Check devices table exists
SELECT to_regclass('public.devices');
-- Should return: "devices"

-- Verify message tables
\d chats
\d messages

-- Verify all 13 session tables exist
SELECT count(*) FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('devices', 'identities', 'prekeys', 'sessions', 'sender_keys',
                  'signed_prekeys', 'app_state_sync_keys', 'app_state_version',
                  'app_state_mutation_macs', 'contacts', 'chat_settings',
                  'message_secrets', 'privacy_tokens');
-- Should return 13
```

#### Step 5: Create Supabase Secrets

```bash
# Store Supabase URL
echo -n "https://YOUR_PROJECT.supabase.co" | \
  gcloud secrets create whatsapp-mcp-supabase-url \
  --replication-policy="automatic" \
  --data-file=-

# Store Supabase service key (not anon key!)
echo -n "your-supabase-service-role-key" | \
  gcloud secrets create whatsapp-mcp-supabase-key \
  --replication-policy="automatic" \
  --data-file=-

# Store session DSN (required for Postgres session storage)
echo -n "postgresql://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres?sslmode=require" | \
  gcloud secrets create whatsapp-mcp-database-url \
  --replication-policy="automatic" \
  --data-file=-
```

**Important**:
- Use the Supabase **service key** (not anon key) as session tables have RLS enabled with deny-all policies.
- The `whatsapp-mcp-database-url` secret is used by the Go WhatsApp bridge for direct Postgres session storage.
- If you're using SQLite-only deployment (with GCS backup), you can omit this secret or create a placeholder.

#### Step 6: Verify Session Tables Security

```sql
-- Verify RLS is enabled (should show all tables with RLS on)
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('devices', 'identities', 'prekeys', 'sessions');
-- All should show rowsecurity = true

-- Verify service_role has access
SELECT grantee, privilege_type FROM information_schema.table_privileges
WHERE table_name = 'devices' AND grantee = 'service_role';
-- Should show SELECT, INSERT, UPDATE, DELETE

-- Verify anon/authenticated do NOT have direct access (security check)
SELECT grantee, privilege_type FROM information_schema.table_privileges
WHERE table_name = 'devices' AND grantee IN ('anon', 'authenticated');
-- Should return no rows (empty)
```

**Notes**:
- GCS session backup is automatically disabled when using Postgres sessions
- Use Supabase's built-in backups or `pg_dump` for session backup
- Session tables have RLS enabled with deny-all policies for security
- Only the Go bridge (using direct Postgres connection) can access session tables

## Service Account Setup

### Step 1: Create Service Account

```bash
# Create dedicated service account
gcloud iam service-accounts create whatsapp-mcp \
  --display-name="WhatsApp MCP Server"

# Get the full service account email
SA_EMAIL="whatsapp-mcp@YOUR_PROJECT.iam.gserviceaccount.com"
```

### Step 2: Grant Required Permissions

```bash
# Secret Manager access (for all secrets)
gcloud secrets add-iam-policy-binding whatsapp-mcp-google-client-id \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding whatsapp-mcp-oauth-audience \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# If using Supabase
gcloud secrets add-iam-policy-binding whatsapp-mcp-supabase-url \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding whatsapp-mcp-supabase-key \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Database URL for Postgres session storage (required when using Supabase/Postgres sessions)
gcloud secrets add-iam-policy-binding whatsapp-mcp-database-url \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# GCS bucket access (for SQLite session backup)
gcloud storage buckets add-iam-policy-binding \
  gs://YOUR_PROJECT-whatsapp-sessions \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.objectAdmin"
```

**Important**:
- Avoid granting project-level Editor or Owner roles. Use least-privilege principle.
- Only grant access to `whatsapp-mcp-database-url` if using PostgreSQL/Supabase for session storage.
- If using SQLite-only deployment, you can skip the `whatsapp-mcp-database-url` secret binding.

## Deployment Steps

### Quick Start with Automated Setup

```bash
# Set project ID and OAuth configuration
export GCP_PROJECT_ID=your-project-id
export OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
export OAUTH_AUDIENCE=your-client-id.apps.googleusercontent.com

# Run automated setup
./gcp/setup.sh
```

This script will:
1. Enable required APIs
2. Create service account with OAuth and storage permissions
3. Create GCS bucket for session storage
4. Configure OAuth credentials and secrets
5. Display deployment instructions

### Alternative: Terraform Deployment

For infrastructure as code:

```bash
# Navigate to Terraform directory
cd gcp/terraform

# Configure OAuth and project settings
cat > terraform.tfvars <<EOF
project_id = "your-project-id"
oauth_client_id = "your-client-id.apps.googleusercontent.com"
oauth_audience = "your-client-id.apps.googleusercontent.com"
EOF

# Deploy infrastructure
terraform init
terraform plan
terraform apply
```

### Build and Deploy Container

#### Step 1: Build Container Image

```bash
# Build and push to Artifact Registry
gcloud builds submit --tag us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest

# Or build locally and push
docker build -t us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest .
docker push us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest
```

#### Step 2: Deploy to Cloud Run

**With SQLite (Default)**:
```bash
gcloud run deploy whatsapp-mcp \
  --image=us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest \
  --region=us-central1 \
  --platform=managed \
  --service-account=whatsapp-mcp@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --port=3000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --update-secrets=\
GOOGLE_CLIENT_ID=whatsapp-mcp-google-client-id:latest,\
OAUTH_AUDIENCE=whatsapp-mcp-oauth-audience:latest \
  --set-env-vars=\
MCP_TRANSPORT=sse,\
MCP_PORT=3000,\
PORT=3000,\
WHATSAPP_BRIDGE_URL=http://localhost:8080,\
GCS_SESSION_BUCKET=${GCP_PROJECT_ID}-whatsapp-sessions,\
GCS_SESSION_OBJECT_NAME=whatsapp.db,\
OAUTH_ENABLED=true \
  --allow-unauthenticated
```

**With Supabase**:
```bash
gcloud run deploy whatsapp-mcp \
  --image=us-central1-docker.pkg.dev/${GCP_PROJECT_ID}/whatsapp-mcp/whatsapp-mcp:latest \
  --region=us-central1 \
  --platform=managed \
  --service-account=whatsapp-mcp@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
  --port=3000 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --update-secrets=\
GOOGLE_CLIENT_ID=whatsapp-mcp-google-client-id:latest,\
OAUTH_AUDIENCE=whatsapp-mcp-oauth-audience:latest,\
SUPABASE_URL=whatsapp-mcp-supabase-url:latest,\
SUPABASE_KEY=whatsapp-mcp-supabase-key:latest,\
WHATSAPP_SESSION_DATABASE_URL=whatsapp-mcp-session-dsn:latest \
  --set-env-vars=\
MCP_TRANSPORT=sse,\
MCP_PORT=3000,\
PORT=3000,\
WHATSAPP_BRIDGE_URL=http://localhost:8080,\
OAUTH_ENABLED=true \
  --allow-unauthenticated
```

#### Step 3: Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe whatsapp-mcp \
  --region=us-central1 \
  --format='value(status.url)')

# Test health endpoint (no auth required)
curl "${SERVICE_URL}/health"
# Should return: HTTP 200 OK

# Check service status
gcloud run services describe whatsapp-mcp \
  --region=us-central1 \
  --format="yaml(status,metadata.annotations)"
```

## MCP Client Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "whatsapp-remote": {
      "transport": "sse",
      "url": "https://YOUR-SERVICE-xxxxx-uc.a.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_GOOGLE_ID_TOKEN"
      }
    }
  }
}
```

Windows path: `%APPDATA%\Claude\claude_desktop_config.json`

### Cursor

Edit `~/.cursor/mcp.json` (macOS/Linux) or `%USERPROFILE%\.cursor\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "whatsapp-remote": {
      "transport": "sse",
      "url": "https://YOUR-SERVICE-xxxxx-uc.a.run.app/sse",
      "headers": {
        "Authorization": "Bearer YOUR_GOOGLE_ID_TOKEN"
      }
    }
  }
}
```

### Obtaining Google ID Tokens

```bash
# Generate a Google ID token with your OAuth Client ID as the audience
TOKEN=$(gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com)

# Use the token in your client configuration
echo $TOKEN
```

**Token Refresh**: Google ID tokens expire after 1 hour. You'll need to refresh the token periodically:
- Manually update the config file with a new token
- Or use a token refresh script/tool to automate token updates

## Monitoring and Management

### View Service Logs

```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp" --limit=50

# View logs with OAuth events
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp AND jsonPayload.oauth=*" --limit=50

# View error logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp AND severity>=ERROR" --limit=50

# Follow logs in real-time
gcloud run services logs tail whatsapp-mcp --region=us-central1
```

### Check Session Backend

```bash
# Check which session backend is being used
curl https://YOUR-SERVICE-URL/api/session-backend

# Response should include:
# - "backend": "postgres" or "sqlite"
# - "session_tables_ok": true/false
# - "session_host": database host (for Postgres)
```

### Management Consoles

- **Cloud Run**: [Service Dashboard](https://console.cloud.google.com/run)
- **OAuth**: [Credentials](https://console.cloud.google.com/apis/credentials)
- **Secret Manager**: [Secrets](https://console.cloud.google.com/security/secret-manager)
- **Storage**: [GCS Buckets](https://console.cloud.google.com/storage)
- **Logs**: [Cloud Logging](https://console.cloud.google.com/logs)

### Set Up Monitoring

```bash
# Create uptime check
gcloud monitoring uptime-checks create http whatsapp-mcp \
  --uri="https://YOUR-SERVICE-xxxxx-uc.a.run.app/health" \
  --period=300s \
  --timeout=10s

# Set up alerting policy
gcloud alpha monitoring policies create \
  --notification-channels="projects/YOUR_PROJECT/notificationChannels/YOUR_CHANNEL" \
  --display-name="WhatsApp MCP Server Health" \
  --conditions="metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.response_code_class!=\"2xx\""
```

## Security Hardening

### IAM Roles and Permissions

Configure minimal required IAM roles:

```bash
# Required: Secret Manager access
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:whatsapp-mcp@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Required: Storage access (grant at bucket level, not project)
gcloud storage buckets add-iam-policy-binding \
  gs://PROJECT_ID-whatsapp-sessions \
  --member="serviceAccount:whatsapp-mcp@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

**Avoid granting**:
- Project-level Editor or Owner roles
- Overly broad storage permissions
- Unnecessary Cloud SQL or compute permissions

### OAuth Security

**1. Token Management**:
- Use short-lived tokens (1 hour expiry)
- Implement automatic token refresh
- Never commit tokens to version control
- Monitor OAuth usage in audit logs

**2. Client Security**:
- Use separate client IDs for dev/staging/prod
- Configure appropriate scopes and permissions
- Implement token validation on client side
- Store credentials in Secret Manager only

**3. Server Security**:
- Enable OAuth for all endpoints except /health
- Configure audience validation (Client ID)
- Set up CORS for allowed origins if needed

### Secrets Management

**1. Rotation Cadence**:
- OAuth credentials: Every 90 days
- Supabase keys: Every 180 days
- Immediate rotation on security incidents

**2. Enable Audit Logging**:
```bash
# Enable Data Access logs for Secret Manager
# Console: IAM & Admin → Audit Logs → Secret Manager
# Enable: Admin Read, Data Read, Data Write

# Monitor secret access
gcloud logging read \
  "resource.type=secretmanager.googleapis.com/Secret \
   AND protoPayload.methodName=google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion" \
  --limit=50
```

**3. Access Control**:
- Grant secretAccessor role only to required service accounts
- Use separate secrets per environment
- Enable automatic secret versioning

### Network Security

**1. Ingress Controls**:
```bash
# Restrict Cloud Run ingress
gcloud run services update whatsapp-mcp \
  --ingress=internal-and-cloud-load-balancing \
  --execution-environment=gen2
```

**2. VPC Service Controls (Optional)**:
- Create service perimeter for Secret Manager
- Restrict data exfiltration
- Requires organization-level VPC-SC setup

**3. Cloud Armor (Optional)**:
- Deploy Cloud Load Balancer
- Configure rate limiting and DDoS protection
- Implement geo-blocking if needed

### Service Hardening

```bash
# Use Gen2 execution environment
gcloud run services update whatsapp-mcp \
  --execution-environment=gen2

# Enable Binary Authorization (optional, requires setup)
gcloud run services update whatsapp-mcp \
  --binary-authorization=default

# Set resource limits
gcloud run services update whatsapp-mcp \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=10
```

## Cost Optimization

### Monthly Cost Estimates

#### Development Environment (~$0-5/month)
- **Cloud Run**: Free tier (2M requests/month) - ~$0
- **Cloud Storage**: 5GB free tier - ~$0
- **Secret Manager**: 6 secrets, free tier - ~$0
- **Total**: ~$0-5 if within free tiers

#### Production Low Traffic (~$10-35/month)
- **Cloud Run**: ~100K requests, min-instances=0 - ~$5-10
- **Cloud Storage**: 10GB session data - ~$0.20
- **Secret Manager**: 6 secrets - ~$0.06
- **Supabase**: Free tier or ~$25/month for Pro
- **Total**: ~$10-35/month

#### Production High Availability (~$75-125/month)
- **Cloud Run**: ~1M requests, min-instances=1 - ~$50-100
- **Cloud Storage**: 50GB session data + backups - ~$1
- **Secret Manager**: 10 secrets with rotation - ~$0.10
- **Supabase Pro**: ~$25/month
- **Total**: ~$75-125/month

### Cost Optimization Tips

**1. Instance Configuration**:
```bash
# Start with minimal resources
gcloud run services update whatsapp-mcp \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10
```

**2. Scaling Configuration**:
```bash
# Update scaling settings
gcloud run services update whatsapp-mcp \
  --min-instances=0 \
  --max-instances=10 \
  --cpu-throttling \
  --concurrency=80
```

**3. Cost Monitoring**:
```bash
# Set up budget alert
gcloud billing budgets create \
  --billing-account=YOUR_BILLING_ACCOUNT \
  --display-name="WhatsApp MCP Budget" \
  --budget-amount=50USD \
  --threshold-rule=percent=0.8 \
  --threshold-rule=percent=1.0
```

**4. Additional Optimizations**:
- Use GCS lifecycle policies to archive old session data
- Implement request caching to reduce Cloud Run costs
- Monitor and optimize API usage patterns
- Leverage free tiers for development/testing

## Troubleshooting

### OAuth Issues

**Invalid Token**:
- Check audience and issuer claims match OAuth Client ID
- Verify token hasn't expired (1 hour lifetime)
- Generate new token: `gcloud auth print-identity-token --audiences=CLIENT_ID`

**Token Expired**:
- Verify token lifetime settings
- Implement automatic token refresh
- Check system clock is synchronized

**Missing Claims**:
- Review OAuth consent screen configuration
- Verify required scopes are granted
- Check token using jwt.io debugger

**CORS Errors**:
- Check allowed origins in Cloud Run
- Verify CORS headers are set correctly
- Test with curl first (bypasses CORS)

### Infrastructure Issues

**API Not Enabled**:
```bash
# Check enabled APIs
gcloud services list --enabled

# Enable missing API
gcloud services enable SERVICE_NAME.googleapis.com
```

**Storage Access**:
```bash
# Check bucket permissions
gcloud storage buckets get-iam-policy gs://BUCKET_NAME

# Grant access if needed
gcloud storage buckets add-iam-policy-binding gs://BUCKET_NAME \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/storage.objectAdmin"
```

**Secrets Access**:
```bash
# Verify secret exists
gcloud secrets describe SECRET_NAME

# Check IAM policy
gcloud secrets get-iam-policy SECRET_NAME

# Grant access
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

**Container Issues**:
```bash
# Check build status
gcloud builds list --limit=5

# View build logs
gcloud builds log BUILD_ID

# Test container locally
docker run -p 3000:3000 -e OAUTH_ENABLED=false IMAGE_NAME
```

**Supabase Connection**:
```bash
# Test connection string
psql "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?sslmode=require" -c "SELECT 1;"

# Verify migrations were applied
psql $DATABASE_URL -c "\dt"

# Check session tables
psql $DATABASE_URL -c "SELECT to_regclass('public.devices');"
```

### Common Fixes

```bash
# Test health endpoint (should bypass OAuth)
curl -v "https://YOUR-SERVICE-URL/health"  # Should return 200 OK

# Obtain a Google ID token for testing
TOKEN=$(gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com)

# Test authenticated endpoint
curl -H "Authorization: Bearer $TOKEN" "https://YOUR-SERVICE-URL/sse"

# Check service account permissions
gcloud projects get-iam-policy ${GCP_PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:whatsapp-mcp"

# View recent service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp" --limit=50

# Check session backend status
curl https://YOUR-SERVICE-URL/api/session-backend
```

## Maintenance

### Regular Updates

1. **Keep base images updated**:
```bash
# Rebuild with latest base image
docker build --no-cache -t IMAGE_NAME .
docker push IMAGE_NAME

# Redeploy to Cloud Run
gcloud run deploy whatsapp-mcp --image=IMAGE_NAME
```

2. **Apply security patches**:
```bash
# Update Go dependencies
cd whatsapp-bridge
go get -u ./...
go mod tidy

# Update Python dependencies
cd whatsapp-mcp-server
uv pip compile requirements.txt -o requirements.lock
```

3. **Monitor Cloud Run announcements**:
- Subscribe to [Cloud Run release notes](https://cloud.google.com/run/docs/release-notes)
- Review security advisories

### Backup Strategy

**1. Session Data Backups**:
```bash
# For SQLite: GCS handles automatic backup
# For Supabase: Use built-in backups or pg_dump
pg_dump "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres" > backup.sql
```

**2. Database Backups**:
```bash
# Schedule regular Supabase backups via dashboard
# Or automate with Cloud Scheduler + pg_dump
```

**3. Configuration Backups**:
- Export Cloud Run service configuration
- Back up Secret Manager secrets (metadata only)
- Document environment variables

### Monitoring Strategy

**1. Set Up Logging Exports**:
```bash
# Export logs to BigQuery for long-term analysis
gcloud logging sinks create whatsapp-mcp-logs \
  bigquery.googleapis.com/projects/PROJECT_ID/datasets/whatsapp_logs \
  --log-filter='resource.type="cloud_run_revision" \
                AND resource.labels.service_name="whatsapp-mcp"'
```

**2. Configure Error Reporting**:
- Enable Cloud Error Reporting
- Set up alerts for critical errors
- Monitor error rates and patterns

**3. Track Performance Metrics**:
- Monitor request latency
- Track memory and CPU usage
- Review cold start times
- Analyze scaling patterns

## Additional Resources

### Documentation
- [../database.md](../database.md): Database configuration guide
- [../migrations.md](../migrations.md): Schema migration instructions
- [../troubleshooting.md](../troubleshooting.md): General troubleshooting
- [../networking.md](../networking.md): Network and transport configuration

### GCP Resources
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [OAuth 2.1 Specification](https://oauth.net/2.1/)
- [Cloud Storage Documentation](https://cloud.google.com/storage/docs)

### Project Files
- [../../gcp/setup.sh](../../gcp/setup.sh): Automated provisioning script
- [../../gcp/terraform/](../../gcp/terraform/): Infrastructure as code
- [../../gcp/cloudrun.yaml](../../gcp/cloudrun.yaml): Cloud Run service definition
- [../../gcp/env-template.yaml](../../gcp/env-template.yaml): Environment variables reference

## Security Notes for Remote Access

- **Never commit tokens** to version control
- **Use environment variables** or secure credential storage for tokens
- **Rotate tokens** regularly and monitor access logs
- **Enable audit logging** in Secret Manager and Cloud Run
- **Consider VPC-SC** for additional network isolation
- **Use separate Client IDs** for different environments
- **Monitor OAuth usage** in Cloud Console
- **Implement least privilege** for service accounts
