# Cloud SQL Database Setup Guide

This guide covers setting up and connecting to Cloud SQL PostgreSQL for the WhatsApp MCP server.

## Prerequisites

- GCP project with Cloud SQL instance created (via `gcp/setup.sh` or Terraform)
- `gcloud` CLI installed and authenticated
- Cloud SQL Proxy installed (for local connections)
- `psql` PostgreSQL client installed

## Installing Cloud SQL Proxy

### macOS
```bash
brew install cloud-sql-proxy
```

### Linux
```bash
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/
```

### Verify Installation
```bash
cloud-sql-proxy --version
```

## Connecting to Cloud SQL

### Step 1: Get Connection Name

Retrieve your Cloud SQL instance connection name:

```bash
gcloud sql instances describe whatsapp-mcp-db \
  --project=YOUR_PROJECT_ID \
  --format="value(connectionName)"
```

The format is: `PROJECT_ID:REGION:INSTANCE_NAME`

### Step 2: Start Cloud SQL Proxy

Run the proxy in a terminal (keep it running):

```bash
cloud-sql-proxy YOUR_PROJECT_ID:REGION:INSTANCE_NAME
```

Or run in the background:

```bash
cloud-sql-proxy YOUR_PROJECT_ID:REGION:INSTANCE_NAME &
```

The proxy creates a Unix socket at `/cloudsql/YOUR_PROJECT_ID:REGION:INSTANCE_NAME` by default.

### Step 3: Connect with psql

Connect to the database:

```bash
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp"
```

You'll be prompted for the password. If you used `setup.sh`, the password was displayed in the output or saved temporarily.

### Creating the Database Schema

Before running the WhatsApp bridge, you must create the required database schema. The bridge validates that the `chats` and `messages` tables exist on startup.

#### Run the Base Migration

From your local repository, run the base schema migration:

```bash
# Ensure Cloud SQL Proxy is running, then:
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

#### Verify Schema Creation

Check that the tables were created successfully:

```bash
# List all tables
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" -c "\dt"

# Verify chats table
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" -c "\d chats"

# Verify messages table
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" -c "\d messages"

# Check indexes
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" -c "\di"
```

You should see:
- `chats` table with columns: jid, name, last_message_time
- `messages` table with columns: id, chat_jid, sender, content, timestamp, is_from_me, media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length
- Indexes: idx_chats_last_message_time, idx_messages_chat_timestamp, idx_messages_sender

### Alternative: TCP Connection

Start proxy with TCP port:

```bash
cloud-sql-proxy YOUR_PROJECT_ID:REGION:INSTANCE_NAME --port=5432
```

Connect via TCP:

```bash
psql "host=127.0.0.1 port=5432 user=whatsapp_user dbname=whatsapp_mcp"
```

## Running Additional Migrations

After creating the base schema with `000_create_bridge_tables.sql`, you can apply additional migrations for enhanced functionality.

### Step 1: Verify Connection

First, ensure you can connect to the database:

```bash
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" -c "SELECT version();"
```

### Step 2: Run Additional Migration Scripts

Navigate to the migrations directory and run additional SQL scripts:

```bash
cd whatsapp-mcp-server/migrations

# Run the chat list view migration (after base schema is created)
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f 001_create_chat_list_view.sql
```

### Step 3: Verify Migration

Check that the view was created:

```bash
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -c "\dv chat_list"
```

### Running All Migrations in Order

If you have multiple migration files, run them in order:

```bash
# Run base schema first (required)
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# Then run additional migrations
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f whatsapp-mcp-server/migrations/001_create_chat_list_view.sql
```

## Configuring Cloud Run

### Step 1: Set DATABASE_URL Secret

The DATABASE_URL must use the Cloud SQL Unix socket path:

```bash
CONNECTION_NAME="YOUR_PROJECT_ID:REGION:INSTANCE_NAME"
DB_USER="whatsapp_user"
DB_PASSWORD="your_db_password"
DB_NAME="whatsapp_mcp"

# Create or update the secret
echo -n "postgresql://${DB_USER}:${DB_PASSWORD}@localhost/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}" | \
  gcloud secrets create whatsapp-mcp-database-url \
    --data-file=- \
    --replication-policy=automatic \
    --project=YOUR_PROJECT_ID
```

Or update existing secret:

```bash
echo -n "postgresql://${DB_USER}:${DB_PASSWORD}@localhost/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}" | \
  gcloud secrets versions add whatsapp-mcp-database-url \
    --data-file=- \
    --project=YOUR_PROJECT_ID
```

### Step 2: Configure Cloud Run with Cloud SQL

When deploying to Cloud Run, add the Cloud SQL connection:

```bash
gcloud run deploy whatsapp-mcp-server \
  --image=gcr.io/YOUR_PROJECT_ID/whatsapp-mcp-server:latest \
  --region=us-central1 \
  --add-cloudsql-instances=YOUR_PROJECT_ID:REGION:INSTANCE_NAME \
  --update-secrets=DATABASE_URL=whatsapp-mcp-database-url:latest \
  --service-account=whatsapp-mcp-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --project=YOUR_PROJECT_ID
```

Key flags:
- `--add-cloudsql-instances`: Connects Cloud Run to Cloud SQL
- `--update-secrets`: Mounts DATABASE_URL from Secret Manager
- `--service-account`: Uses service account with Cloud SQL Client role

### Step 3: Verify Cloud Run Connection

Check Cloud Run logs after deployment:

```bash
gcloud run services logs read whatsapp-mcp-server \
  --region=us-central1 \
  --project=YOUR_PROJECT_ID \
  --limit=50
```

Look for successful database connection messages.

## Supabase Compatibility

**Important**: The current application code in `whatsapp-mcp-server/config.py` requires `SUPABASE_URL` and `SUPABASE_KEY` environment variables even when using Cloud SQL with a `postgresql://` connection string.

### Option 1: Use Supabase (Recommended for current code)

Set these additional secrets:

```bash
# Create Supabase URL secret
echo -n "https://your-project.supabase.co" | \
  gcloud secrets create whatsapp-mcp-supabase-url \
    --data-file=- \
    --project=YOUR_PROJECT_ID

# Create Supabase Key secret
echo -n "your-supabase-anon-key" | \
  gcloud secrets create whatsapp-mcp-supabase-key \
    --data-file=- \
    --project=YOUR_PROJECT_ID
```

Add to Cloud Run deployment:

```bash
gcloud run deploy whatsapp-mcp-server \
  --update-secrets=DATABASE_URL=whatsapp-mcp-database-url:latest,\
SUPABASE_URL=whatsapp-mcp-supabase-url:latest,\
SUPABASE_KEY=whatsapp-mcp-supabase-key:latest \
  ...
```

### Option 2: Modify Code for Direct PostgreSQL

Alternatively, update `whatsapp-mcp-server/config.py` to support direct PostgreSQL connections without Supabase dependencies by creating a native PostgreSQL adapter.

## Troubleshooting

### Error: required tables missing: [chats messages]

**Symptom**: Bridge fails to start with error message: `required tables missing: [chats messages]. The schema must be created externally`

**Solution**: Run the base schema migration:

```bash
# Ensure Cloud SQL Proxy is running
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

**Verification**: Check that tables exist:

```bash
# List all tables
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" -c "\dt"

# Query the tables to confirm they work
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -c "SELECT COUNT(*) FROM chats;"
psql "host=localhost user=whatsapp_user dbname=whatsapp_mcp" \
  -c "SELECT COUNT(*) FROM messages;"
```

If the tables exist but you still see the error, check database permissions and ensure the connection string is correct.

### Error: Cloud SQL connection failed

**Symptom**: `could not connect to server: No such file or directory`

**Solution**: Ensure Cloud SQL Proxy is running and the socket path is correct:

```bash
cloud-sql-proxy YOUR_PROJECT_ID:REGION:INSTANCE_NAME &
ls -la /cloudsql/YOUR_PROJECT_ID:REGION:INSTANCE_NAME/.s.PGSQL.5432
```

### Error: password authentication failed

**Symptom**: `FATAL: password authentication failed for user "whatsapp_user"`

**Solution**: Reset the database user password:

```bash
gcloud sql users set-password whatsapp_user \
  --instance=whatsapp-mcp-db \
  --password=NEW_PASSWORD \
  --project=YOUR_PROJECT_ID
```

Update the DATABASE_URL secret with the new password.

### Error: database "whatsapp_mcp" does not exist

**Solution**: Create the database:

```bash
gcloud sql databases create whatsapp_mcp \
  --instance=whatsapp-mcp-db \
  --project=YOUR_PROJECT_ID
```

### Error: Cloud SQL Admin API has not been used

**Solution**: Enable the API:

```bash
gcloud services enable sqladmin.googleapis.com --project=YOUR_PROJECT_ID
```

### Cloud Run: Connection refused or timeout

**Symptoms**:
- `connection refused`
- `timeout`
- Logs show failed database connections

**Checklist**:
1. Verify `--add-cloudsql-instances` flag is set correctly
2. Ensure service account has `roles/cloudsql.client` role
3. Check DATABASE_URL secret format uses `/cloudsql/` socket path
4. Verify SUPABASE_URL and SUPABASE_KEY secrets are set (if required by app)
5. Review Cloud Run service logs for detailed error messages

### Permission denied for schema public

**Solution**: Grant necessary permissions:

```sql
GRANT ALL PRIVILEGES ON DATABASE whatsapp_mcp TO whatsapp_user;
GRANT ALL ON SCHEMA public TO whatsapp_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO whatsapp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO whatsapp_user;
```

## Security Best Practices

1. **Use IAM Authentication** (optional, advanced):
   ```bash
   gcloud sql users create whatsapp_user@YOUR_PROJECT_ID.iam \
     --instance=whatsapp-mcp-db \
     --type=CLOUD_IAM_USER \
     --project=YOUR_PROJECT_ID
   ```

2. **Restrict IP Access**: Configure authorized networks in Cloud SQL settings

3. **Enable SSL**: Enforce SSL connections for enhanced security

4. **Rotate Passwords**: Regularly update database passwords and Secret Manager versions

5. **Backup Policy**: Enable automated backups (configured by default in setup.sh)

## Monitoring and Maintenance

### View Cloud SQL Metrics

```bash
gcloud sql operations list \
  --instance=whatsapp-mcp-db \
  --project=YOUR_PROJECT_ID
```

### Check Database Size

```sql
SELECT pg_size_pretty(pg_database_size('whatsapp_mcp'));
```

### Backup Database

Manual backup:

```bash
gcloud sql backups create \
  --instance=whatsapp-mcp-db \
  --project=YOUR_PROJECT_ID
```

List backups:

```bash
gcloud sql backups list \
  --instance=whatsapp-mcp-db \
  --project=YOUR_PROJECT_ID
```

## Additional Resources

- [Cloud SQL for PostgreSQL Documentation](https://cloud.google.com/sql/docs/postgres)
- [Cloud SQL Proxy Documentation](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Connecting from Cloud Run](https://cloud.google.com/sql/docs/postgres/connect-run)
- [Best Practices for Cloud SQL](https://cloud.google.com/sql/docs/postgres/best-practices)
