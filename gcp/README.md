# Google Cloud Run Deployment Guide

This guide provides comprehensive instructions for deploying the WhatsApp MCP Server to Google Cloud Run. It covers OAuth 2.1 authentication setup, environment configuration, and security best practices.

## Prerequisites

1. Google Cloud Project setup:
   ```bash
   # Install Google Cloud SDK
   brew install google-cloud-sdk   # macOS
   
   # Initialize and set project
   gcloud init
   gcloud config set project YOUR_PROJECT_ID
   
   # Enable required APIs
   gcloud services enable \
     run.googleapis.com \
     secretmanager.googleapis.com \
     storage.googleapis.com \
     iamcredentials.googleapis.com
   ```

2. OAuth 2.1 credentials setup:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to "APIs & Services" → "OAuth consent screen"
   - Configure consent screen (Internal or External)
   - Create OAuth 2.0 Client ID (see details below)

## OAuth 2.1 Setup

1. Configure OAuth consent screen:
   - User Type: Internal (recommended) or External
   - App name: "WhatsApp MCP Server"
   - User support email: Your team's email
   - Application homepage: Your Cloud Run service URL
   - Authorized domains: Your Cloud Run domain
   - Developer contact: Your team's email

2. Create OAuth 2.0 Client ID:
   ```bash
   # Navigate to Credentials
   open https://console.cloud.google.com/apis/credentials
   
   # Click "Create Credentials" → "OAuth 2.0 Client ID"
   # Choose application type based on your client:
   #   - Web application: For browser-based clients
   #   - Desktop application: For CLI tools
   ```

3. Store credentials in Secret Manager:
   ```bash
   # Create secrets
   echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
     gcloud secrets create whatsapp-mcp-google-client-id \
     --replication-policy="automatic" \
     --data-file=-

   # OAuth audience should match the Google OAuth Client ID for Google ID tokens
   echo -n "YOUR_CLIENT_ID.apps.googleusercontent.com" | \
     gcloud secrets create whatsapp-mcp-oauth-audience \
     --replication-policy="automatic" \
     --data-file=-
   ```

## Storage Configuration

### Option A: GCS Session Storage (SQLite-based)

**Note:** GCS session backup only works with SQLite session storage. For production, consider Supabase Postgres sessions (Option B) instead.

1. Create GCS bucket for session storage:
   ```bash
   # Create bucket (replace with your desired name)
   gcloud storage buckets create gs://YOUR_PROJECT-whatsapp-sessions \
     --location=us-central1 \
     --uniform-bucket-level-access
   ```

2. Configure encryption (optional but recommended):
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

### Option B: Supabase Session Storage (Recommended for Production)

Store WhatsApp sessions in Supabase Postgres for better persistence and multi-instance support.

**Step 1: Run Session Tables Migration**

```bash
# Using Supabase SQL Editor (Recommended)
# 1. Go to your Supabase project dashboard
# 2. Navigate to SQL Editor
# 3. Copy contents of ../whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
# 4. Paste and execute

# Or using psql
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" \
  -f ../whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
```

**Step 2: Verify Tables**

```sql
-- Check devices table exists
SELECT to_regclass('public.devices');

-- Verify all 13 session tables exist
SELECT count(*) FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('devices', 'identities', 'prekeys', 'sessions', 'sender_keys',
                  'signed_prekeys', 'app_state_sync_keys', 'app_state_version',
                  'app_state_mutation_macs', 'contacts', 'chat_settings',
                  'message_secrets', 'privacy_tokens');
-- Should return 13
```

**Step 3: Create Secret for Session DSN**

```bash
# Create session DSN secret
echo -n "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require" | \
  gcloud secrets create whatsapp-mcp-session-dsn \
  --replication-policy="automatic" \
  --data-file=-

# If already exists, add new version
echo -n "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require" | \
  gcloud secrets versions add whatsapp-mcp-session-dsn \
  --data-file=-
```

**Step 4: Update Cloud Run Configuration**

In your `cloudrun.yaml`, uncomment the session DSN environment variable:

```yaml
# Session database configuration
- name: WHATSAPP_SESSION_DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: whatsapp-mcp-session-dsn
      key: latest
```

**Step 5: Grant Service Account Access**

```bash
# Grant access to session DSN secret
gcloud secrets add-iam-policy-binding whatsapp-mcp-session-dsn \
  --member="serviceAccount:whatsapp-mcp@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Step 6: Verify Deployment**

```bash
# Check bridge logs
gcloud run services logs read whatsapp-mcp --region=us-central1 --limit=50

# Look for:
# "Using Postgres session store"
# "Postgres session DSN host: db.[PROJECT-REF].supabase.co"
# "✓ Session tables validated successfully"

# Check session backend status via API
curl https://[YOUR-SERVICE-URL]/api/session-backend
```

**Notes:**

- GCS session backup is automatically disabled when using Postgres sessions
- Use Supabase's built-in backups or `pg_dump` for session backup
- Session tables have RLS enabled with deny-all policies for security
- Only the Go bridge (using direct Postgres connection) can access session tables
- For complete documentation, see `../whatsapp-mcp-server/migrations/README.md`

## Service Account Setup

1. Create dedicated service account:
   ```bash
   # Create service account
   gcloud iam service-accounts create whatsapp-mcp \
     --display-name="WhatsApp MCP Server"
   
   # Get the full service account email
   SA_EMAIL="whatsapp-mcp@YOUR_PROJECT.iam.gserviceaccount.com"
   ```

2. Grant required permissions:
   ```bash
   # Secret Manager access
   gcloud secrets add-iam-policy-binding whatsapp-mcp-google-client-id \
     --member="serviceAccount:$SA_EMAIL" \
     --role="roles/secretmanager.secretAccessor"
   
   gcloud secrets add-iam-policy-binding whatsapp-mcp-oauth-audience \
     --member="serviceAccount:$SA_EMAIL" \
     --role="roles/secretmanager.secretAccessor"
   
   # GCS bucket access
   gcloud storage buckets add-iam-policy-binding \
     gs://YOUR_PROJECT-whatsapp-sessions \
     --member="serviceAccount:$SA_EMAIL" \
     --role="roles/storage.objectViewer"
   
   gcloud storage buckets add-iam-policy-binding \
     gs://YOUR_PROJECT-whatsapp-sessions \
     --member="serviceAccount:$SA_EMAIL" \
     --role="roles/storage.objectCreator"
   ```

## Cloud Run Deployment

1. Build and push container:
   ```bash
   # Build with Cloud Build
   gcloud builds submit \
     --tag gcr.io/YOUR_PROJECT/whatsapp-mcp
   ```

2. Deploy to Cloud Run:
   ```bash
   # Deploy service
   gcloud run deploy whatsapp-mcp \
     --image gcr.io/YOUR_PROJECT/whatsapp-mcp \
     --region us-central1 \
     --service-account $SA_EMAIL \
     --port 3000 \
     --memory 512Mi \
     --cpu 1 \
     --min-instances 0 \
     --max-instances 10 \
     --set-env-vars "MCP_TRANSPORT=sse" \
     --set-secrets "GOOGLE_CLIENT_ID=whatsapp-mcp-google-client-id:latest" \
     --set-secrets "OAUTH_AUDIENCE=whatsapp-mcp-oauth-audience:latest" \
     --allow-unauthenticated
   ```

## Health Checks and Monitoring

1. Health check endpoint:
   - Cloud Run automatically probes `/health`
   - Endpoint bypasses OAuth authentication
   - Returns HTTP 200 OK when service is healthy

2. Set up monitoring:
   ```bash
   # Create uptime check
   gcloud monitoring uptime-checks create http whatsapp-mcp \
     --uri="https://YOUR-SERVICE-xxxxx-uc.a.run.app/health" \
     --period=300s \
     --timeout=10s
   
   # Create alerting policy (recommended)
   gcloud alpha monitoring policies create \
     --notification-channels="projects/YOUR_PROJECT/notificationChannels/YOUR_CHANNEL" \
     --display-name="WhatsApp MCP Server Health" \
     --conditions="metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.response_code_class!=\"2xx\""
   ```

## MCP Client Configuration

After deploying to Cloud Run, configure your MCP clients to connect to the remote server:

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

### Cursor

Edit `~/.cursor/mcp.json`:

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

### Obtaining Tokens

```bash
# Get Google ID token for your OAuth Client ID
gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com
```

**Note**: Tokens expire after 1 hour and must be refreshed manually or via automation.

## Cost Optimization

Monthly cost estimates for WhatsApp MCP on Cloud Run:

### Development (~$0-5/month)
- **Cloud Run**: Free tier (2M requests/month)
- **Cloud Storage**: 5GB free tier
- **Secret Manager**: 6 secrets, free tier
- **Total**: $0-5 if within free tiers

### Production Low Traffic (~$10-35/month)
- **Cloud Run**: ~100K requests, min-instances=0 - $5-10
- **Cloud Storage**: 10GB - $0.20
- **Secret Manager**: 6 secrets - $0.06
- **Supabase**: Free tier or $25/month Pro
- **Total**: $10-35/month

### Production High Availability (~$75-125/month)
- **Cloud Run**: ~1M requests, min-instances=1 - $50-100
- **Cloud Storage**: 50GB + backups - $1
- **Secret Manager**: 10 secrets with rotation - $0.10
- **Supabase Pro**: $25/month
- **Total**: $75-125/month

### Cost Optimization Tips

1. Instance configuration:
   - Start with minimal resources (512Mi memory, 1 CPU)
   - Set min-instances=0 for cost savings
   - Adjust max-instances based on load
   - Monitor actual usage and adjust

2. Scaling configuration:
   ```bash
   # Update scaling configuration
   gcloud run services update whatsapp-mcp \
     --min-instances=0 \
     --max-instances=10 \
     --cpu-throttling \
     --concurrency=80
   ```

3. Cost monitoring:
   ```bash
   # Set up budget alert
   gcloud billing budgets create \
     --billing-account=YOUR_BILLING_ACCOUNT \
     --display-name="WhatsApp MCP Budget" \
     --budget-amount=50USD \
     --threshold-rule=percent=0.8 \
     --threshold-rule=percent=1.0
   ```

4. Additional optimizations:
   - Use GCS lifecycle policies to archive old session data
   - Implement request caching to reduce Cloud Run costs
   - Monitor and optimize API usage patterns
   - Leverage free tiers for development/testing

## Security Best Practices

### IAM Roles and Permissions

Configure the Cloud Run service account with minimal required roles:

```bash
# Required roles for the service account
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:whatsapp-mcp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant storage permissions at bucket level (not project level)
gcloud storage buckets add-iam-policy-binding \
  gs://PROJECT_ID-whatsapp-sessions \
  --member="serviceAccount:whatsapp-mcp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

**Avoid granting**:
- Project-level Editor or Owner roles
- Overly broad storage permissions
- Unnecessary Cloud SQL or compute permissions

### OAuth Configuration

1. **Use internal user type when possible**:
   - Limits access to organization members only
   - Reduces attack surface for token theft

2. **Token security**:
   - Never commit tokens to version control
   - Use short-lived tokens (1 hour expiry)
   - Implement automatic token refresh
   - Monitor OAuth usage in audit logs

3. **Client ID protection**:
   - Store Client ID in Secret Manager
   - Rotate credentials if compromised
   - Use separate Client IDs per environment

### Secrets Management

1. **Secret rotation cadence**:
   - OAuth credentials: Rotate every 90 days
   - Supabase keys: Rotate every 180 days
   - Review and rotate on security incidents

2. **Enable audit logging**:
   ```bash
   # Enable Data Access audit logs for Secret Manager
   # Via Cloud Console: IAM & Admin → Audit Logs → Secret Manager
   # Enable: Admin Read, Data Read, Data Write
   ```

3. **Secret access monitoring**:
   ```bash
   # Monitor secret access logs
   gcloud logging read \
     "resource.type=secretmanager.googleapis.com/Secret \
      AND protoPayload.methodName=google.cloud.secretmanager.v1.SecretManagerService.AccessSecretVersion" \
     --limit=50
   ```

### Network Security

1. **Ingress controls**:
   ```bash
   # Restrict to internal + load balancer only
   gcloud run services update whatsapp-mcp \
     --ingress=internal-and-cloud-load-balancing \
     --execution-environment=gen2
   ```

2. **VPC Service Controls** (optional, advanced):
   - Create a service perimeter around Secret Manager and Storage
   - Restricts data exfiltration
   - Requires VPC-SC setup

3. **Cloud Armor** (optional, for DDoS protection):
   - Deploy Cloud Load Balancer in front of Cloud Run
   - Configure Cloud Armor security policies
   - Rate limiting and geo-blocking

### Service Hardening

```bash
# Enable Binary Authorization (optional, requires setup)
gcloud run services update whatsapp-mcp \
  --binary-authorization=default

# Use Gen2 execution environment
gcloud run services update whatsapp-mcp \
  --execution-environment=gen2

# Limit service account scope
gcloud run services update whatsapp-mcp \
  --no-allow-unauthenticated  # If using IAM auth
```

### Monitoring and Alerting

1. **Enable Cloud Logging exports**:
   ```bash
   # Export logs to BigQuery for long-term analysis
   gcloud logging sinks create whatsapp-mcp-logs \
     bigquery.googleapis.com/projects/PROJECT_ID/datasets/whatsapp_logs \
     --log-filter='resource.type="cloud_run_revision" \
                   AND resource.labels.service_name="whatsapp-mcp"'
   ```

2. **Set up security alerts**:
   - Alert on failed OAuth attempts
   - Monitor unusual secret access patterns
   - Track unauthorized API calls

3. **Regular security reviews**:
   - Review IAM permissions monthly
   - Audit secret access logs weekly
   - Check for unused service accounts

## Troubleshooting

1. Check service health:
   ```bash
   # View service status
   gcloud run services describe whatsapp-mcp
   
   # Check recent logs
   gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp" --limit=50
   ```

2. Common issues:
   - OAuth configuration
   - Secret access
   - Storage permissions
   - Memory/CPU limits
   - Network connectivity

3. Debug tools:
   ```bash
   # Test service locally
   PORT=3000 OAUTH_ENABLED=true docker run --rm -p 3000:3000 gcr.io/YOUR_PROJECT/whatsapp-mcp
   
   # Validate service account permissions
   gcloud beta asset analyze-iam-policy \
     --identity="serviceAccount:$SA_EMAIL" \
     --permissions="secretmanager.versions.access,storage.objects.get"
   ```

## Maintenance

1. Regular updates:
   - Keep base images updated
   - Apply security patches
   - Update dependencies
   - Monitor Cloud Run announcements

2. Backup strategy:
   - Regular session exports
   - Database backups
   - Configuration backups

3. Monitoring strategy:
   - Set up logging exports
   - Configure error reporting
   - Track performance metrics
   - Set up alerts