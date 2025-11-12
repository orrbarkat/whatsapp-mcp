# Secrets and Environment Variables Reference

**This is the authoritative source for all environment variables and secrets used in the WhatsApp MCP Server.**

For templates and examples, see:
- [.env.example](../.env.example) - Local development template
- [gcp/env-template.yaml](gcp/env-template.yaml) - Cloud Run deployment template

This document provides a comprehensive reference of all secrets and environment variables used in the WhatsApp MCP Server.

## Quick Reference Table

| Variable Name | Type | Purpose | Required | Default | Terraform Secret Name |
|--------------|------|---------|----------|---------|----------------------|
| `DATABASE_URL` | Secret/Env | Message history storage | No | SQLite: `file:store/messages.db` | `whatsapp-mcp-database-url` |
| `WHATSAPP_SESSION_DATABASE_URL` | Secret/Env | Session data storage | No | Falls back to `DATABASE_URL`, then SQLite | `whatsapp-mcp-session-dsn` |
| `SUPABASE_URL` | Secret/Env | Supabase project URL | Conditional* | - | `whatsapp-mcp-supabase-url` |
| `SUPABASE_KEY` | Secret/Env | Supabase service key | Conditional* | - | `whatsapp-mcp-supabase-key` |
| `GOOGLE_CLIENT_ID` | Secret | OAuth client ID | Yes (Cloud Run) | - | `whatsapp-mcp-oauth-client-id` |
| `OAUTH_AUDIENCE` | Secret | OAuth audience | Yes (Cloud Run) | - | `whatsapp-mcp-oauth-audience` |
| `GCS_SESSION_BUCKET` | Env | GCS bucket name | No | - | - |
| `GCS_SESSION_OBJECT_NAME` | Env | GCS object name | No | `whatsapp.db` | - |
| `MCP_TRANSPORT` | Env | Transport mode | No | `stdio` (local), `sse` (Cloud Run) | - |
| `PORT` | Env | HTTP server port | No | `3000` | - |
| `MCP_PORT` | Env | MCP server port | No | `3000` | - |
| `WHATSAPP_BRIDGE_URL` | Env | Bridge API URL | No | `http://localhost:8080` | - |
| `OAUTH_ENABLED` | Env | Enable OAuth | No | `false` (local), `true` (Cloud Run) | - |

*Required when using Supabase Python SDK features or Supabase for database storage.

## Database Configuration

### Messages Database (DATABASE_URL)

**Purpose:** Stores chat history, message content, and media metadata.

**Used by:** Python MCP server and Go bridge.

**Formats:**

```bash
# SQLite (default)
DATABASE_URL=file:store/messages.db?_foreign_keys=on

# PostgreSQL
DATABASE_URL=postgres://user:password@localhost:5432/dbname

# Supabase (with SSL)
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
```

**Required Migration:** `000_create_bridge_tables.sql`

### Sessions Database (WHATSAPP_SESSION_DATABASE_URL)

**Purpose:** Stores WhatsApp authentication, device keys, contacts, and sync state.

**Used by:** Go bridge only (whatsmeow session storage).

**Fallback Behavior:**
1. If `WHATSAPP_SESSION_DATABASE_URL` is set → use it
2. Else if `DATABASE_URL` is set → use it
3. Else → use SQLite: `file:store/whatsapp.db`

**Formats:**

```bash
# PostgreSQL
WHATSAPP_SESSION_DATABASE_URL=postgres://user:password@localhost:5432/dbname

# Supabase (with SSL - required)
WHATSAPP_SESSION_DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
```

**Required Migration:** `010_create_whatsmeow_session_tables.sql` (13 tables)

**Important:**
- Must use Supabase **service key** (not anon key) for session tables
- Session tables have RLS enabled with deny-all policies by default
- Only `service_role` can access session tables

### Supabase Configuration

**SUPABASE_URL**
- Required when using Supabase Python SDK
- Format: `https://xxxxx.supabase.co`
- Find in: Supabase Dashboard → Settings → API

**SUPABASE_KEY**
- Required when using Supabase Python SDK
- Use **service role key** for session tables (bypasses RLS)
- Find in: Supabase Dashboard → Settings → API
- Never use anon key for production

## OAuth Configuration

### GOOGLE_CLIENT_ID

**Purpose:** OAuth 2.0 client ID for authentication.

**Format:** `xxxxxxxxxxxxx.apps.googleusercontent.com`

**Setup:**
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Choose "Web application" or "Desktop app"
4. Copy Client ID

**Storage:**
```bash
# Create secret
echo -n 'YOUR_CLIENT_ID.apps.googleusercontent.com' | \
  gcloud secrets create whatsapp-mcp-google-client-id \
  --replication-policy=automatic \
  --data-file=-
```

### OAUTH_AUDIENCE

**Purpose:** OAuth audience for token validation.

**Format:** Should match `GOOGLE_CLIENT_ID` for Google ID tokens.

**Storage:**
```bash
# Create secret (same value as GOOGLE_CLIENT_ID)
echo -n 'YOUR_CLIENT_ID.apps.googleusercontent.com' | \
  gcloud secrets create whatsapp-mcp-oauth-audience \
  --replication-policy=automatic \
  --data-file=-
```

## GCS Configuration

### GCS_SESSION_BUCKET

**Purpose:** GCS bucket name for session backup (SQLite only).

**Important:**
- Only works with SQLite session storage
- Automatically disabled when using Postgres/Supabase for sessions
- Bridge logs: "GCS session backup is only for SQLite, skipping"

**Format:** `your-project-id-whatsapp-mcp-sessions`

**Setup:**
```bash
gcloud storage buckets create gs://your-bucket-name \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### GCS_SESSION_OBJECT_NAME

**Purpose:** Object name for session database in GCS.

**Default:** `whatsapp.db`

**Format:** `whatsapp.db` or custom name

## Creating Secrets in Secret Manager

### Using gcloud CLI

```bash
# Basic secret creation
echo -n 'secret-value' | \
  gcloud secrets create SECRET_NAME \
  --replication-policy=automatic \
  --data-file=-

# Example: Session DSN
echo -n 'postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require' | \
  gcloud secrets create whatsapp-mcp-session-dsn \
  --replication-policy=automatic \
  --data-file=-

# Update existing secret
echo -n 'new-value' | \
  gcloud secrets versions add SECRET_NAME \
  --data-file=-
```

### Grant Service Account Access

```bash
# Grant access to specific secret
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Local Development (.env)

Create a `.env` file in the project root:

```bash
# Copy template
cp .env.example .env

# Edit with your values
# Minimal local setup (uses defaults):
MCP_TRANSPORT=sse

# With Supabase:
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-service-key

# With separate session database:
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
WHATSAPP_SESSION_DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres?sslmode=require
```

## Cloud Run Deployment

### Using cloudrun.yaml

Uncomment and configure secrets in `cloudrun.yaml` or `gcp/cloudrun.yaml`:

```yaml
env:
  # Database secrets
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: whatsapp-mcp-database-url
        key: latest
  - name: WHATSAPP_SESSION_DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: whatsapp-mcp-session-dsn
        key: latest
  # Supabase secrets
  - name: SUPABASE_URL
    valueFrom:
      secretKeyRef:
        name: whatsapp-mcp-supabase-url
        key: latest
  - name: SUPABASE_KEY
    valueFrom:
      secretKeyRef:
        name: whatsapp-mcp-supabase-key
        key: latest
```

### Using gcloud CLI

```bash
gcloud run deploy whatsapp-mcp \
  --image=REGION-docker.pkg.dev/PROJECT/REPO/whatsapp-mcp:TAG \
  --region=REGION \
  --update-secrets=\
DATABASE_URL=whatsapp-mcp-database-url:latest,\
WHATSAPP_SESSION_DATABASE_URL=whatsapp-mcp-session-dsn:latest,\
GOOGLE_CLIENT_ID=whatsapp-mcp-google-client-id:latest,\
OAUTH_AUDIENCE=whatsapp-mcp-oauth-audience:latest
```

## Terraform Configuration

Terraform automatically creates these secrets:

| Resource | Secret Name | Purpose |
|----------|-------------|---------|
| `google_secret_manager_secret.database_url` | `whatsapp-mcp-database-url` | Messages database |
| `google_secret_manager_secret.session_dsn` | `whatsapp-mcp-session-dsn` | Session database |
| `google_secret_manager_secret.supabase_url` | `whatsapp-mcp-supabase-url` | Supabase URL |
| `google_secret_manager_secret.supabase_key` | `whatsapp-mcp-supabase-key` | Supabase key |
| `google_secret_manager_secret.oauth_client_id` | `whatsapp-mcp-oauth-client-id` | OAuth client |
| `google_secret_manager_secret.oauth_client_secret` | `whatsapp-mcp-oauth-client-secret` | OAuth secret |

**After Terraform Apply:**

```bash
# Update secret values
echo -n 'actual-value' | \
  gcloud secrets versions add whatsapp-mcp-session-dsn \
  --data-file=-
```

## Security Best Practices

1. **Never commit secrets to version control**
   - Keep `.env` in `.gitignore`
   - Use Secret Manager for production

2. **Use appropriate key types**
   - Session tables: **service key** (required)
   - Python SDK: service key or anon key
   - Clients: anon key only

3. **Enable RLS on session tables**
   - Already configured in migration `010_create_whatsmeow_session_tables.sql`
   - Deny-all policies by default
   - Only `service_role` has access

4. **Rotate secrets regularly**
   - OAuth: Every 90 days
   - Supabase keys: Every 180 days
   - Database passwords: Every 180 days

5. **Use SSL/TLS**
   - Always include `?sslmode=require` for Supabase connections
   - Verified automatically in Go bridge startup

6. **Monitor access**
   - Enable audit logging in Secret Manager
   - Set up security alerts for unusual access
   - Review Cloud Run logs regularly

## Troubleshooting

### Check Secret Values

```bash
# List secrets
gcloud secrets list

# View secret metadata
gcloud secrets describe SECRET_NAME

# Access secret value (requires secretAccessor role)
gcloud secrets versions access latest --secret=SECRET_NAME
```

### Verify Service Account Access

```bash
# List IAM policies for secret
gcloud secrets get-iam-policy SECRET_NAME

# Should show service account with secretAccessor role
```

### Test Database Connections

```bash
# Test messages database
psql "$DATABASE_URL" -c "SELECT 1"

# Test session database
psql "$WHATSAPP_SESSION_DATABASE_URL" -c "SELECT to_regclass('public.devices')"
```

### Check Bridge Logs

```bash
# Local
# Look for these log lines:
# "Using Postgres session store"
# "Postgres session DSN host: db.xxxxx.supabase.co"
# "✓ Session tables validated successfully"

# Cloud Run
gcloud run services logs read whatsapp-mcp \
  --region=us-central1 \
  --limit=100
```

### API Endpoints for Diagnostics

```bash
# Check session backend status
curl http://localhost:8080/api/session-backend

# Response:
# {
#   "backend": "postgres",
#   "session_tables_ok": true,
#   "session_host": "db.xxxxx.supabase.co",
#   "message_backend": "postgres",
#   "message_tables_ok": true,
#   "errors": []
# }

# Check authentication status
curl http://localhost:8080/api/auth-status
```

## References

- [Main README](./README.md) - General setup and usage
- [GCP Deployment Guide](./gcp/README.md) - Cloud Run deployment
- [Migrations README](./whatsapp-mcp-server/migrations/README.md) - Database migrations
- [Environment Template](./gcp/env-template.yaml) - Complete env var reference
- [Docker Compose](./docker-compose.yml) - Docker configuration examples
