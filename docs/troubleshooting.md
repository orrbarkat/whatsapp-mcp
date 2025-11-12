# Troubleshooting

This guide covers common issues and their solutions for the WhatsApp MCP server.

## General Issues

### Permission Issues

**Issue**: Permission errors when running uv

**Solution**: Add uv to your PATH or use the full path to the executable
```bash
# Find uv location
which uv

# Use full path in Claude Desktop config
"command": "/full/path/to/uv"
```

### Automatic Bridge Management

With automatic bridge management, you only need the Python MCP server running - the Go bridge will start automatically when needed.

## Local Development Issues

### Bridge Startup Problems

**Issue**: Bridge auto-startup fails

**Solutions**:
- Check status dashboard at `http://localhost:8080/status` for detailed error information
- Ensure Go is installed and available in PATH: `which go`
- Verify the MCP server has permission to start the Go bridge process

**Issue**: Port already in use

**Solution**: Kill existing processes using the port
```bash
# Check what's using port 8080
lsof -i :8080

# Kill the bridge process
pkill -f 'go run main.go'

# Or kill by port
kill $(lsof -t -i:8080)
```

### Go Not Found

**Issue**: Error message indicates Go is not available

**Solution**: Install Go and ensure it's in your PATH
```bash
# macOS with Homebrew
brew install go

# Verify installation
which go
go version
```

## Database Issues

### Missing Tables Error

**Issue**: Bridge fails with error: `required tables missing: [chats messages]`

**Solution**: Run the base schema migration before starting the bridge
```bash
# For SQLite
sqlite3 whatsapp-bridge/store/messages.db < whatsapp-mcp-server/migrations/000_create_bridge_tables.sql

# For PostgreSQL
psql $DATABASE_URL -f whatsapp-mcp-server/migrations/000_create_bridge_tables.sql
```

**Verification**: Check that tables exist
```bash
# For SQLite
sqlite3 whatsapp-bridge/store/messages.db ".tables"

# For PostgreSQL
psql $DATABASE_URL -c "\dt"
```

### Database Connection Issues

**Issue**: Cannot connect to PostgreSQL database

**Solutions**:

1. **Test connection string**:
```bash
psql "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres" -c "SELECT 1;"
```

2. **Verify DATABASE_URL is set**:
```bash
echo $DATABASE_URL
```

3. **Check if .env file is loaded**:
```bash
./start-mcp.sh start  # Should show "Loading environment variables from .env file"
```

4. **For Supabase, ensure sslmode is set**:
```bash
echo $DATABASE_URL | grep sslmode=require
```

### Data Sync Issues

**Issue**: No messages loading

**Solution**: After initial authentication, it can take several minutes for message history to load. Wait and check status.

**Issue**: Missing recent messages

**Solution**: The bridge syncs incrementally; recent messages should appear within a few seconds. Check bridge logs for sync errors.

**Issue**: WhatsApp out of sync

**Solution**: Delete both database files and restart:
```bash
rm whatsapp-bridge/store/messages.db whatsapp-bridge/store/whatsapp.db
# Bridge will restart automatically when you use a WhatsApp tool
```

## Bridge and Connection Issues

### Status Monitoring

**Check Bridge Status**: Use the `check_bridge_status` MCP tool in Claude for real-time diagnostics

**Web Dashboard**: Visit `http://localhost:8080/status` for visual status monitoring

**API Diagnostics**: Access `http://localhost:8080/api/status` for JSON status data

### Bridge Not Running

**Issue**: Bridge process is not running

**Solutions**:
- Use any WhatsApp MCP tool to trigger automatic bridge startup
- Manually start bridge: `cd whatsapp-bridge && go run main.go`
- Check for port conflicts on 8080

### API Not Responsive

**Issue**: Bridge is running but API doesn't respond

**Solutions**:
- Check if the bridge is listening on port 8080: `lsof -i :8080`
- Verify firewall isn't blocking port 8080
- Check bridge logs for errors
- Restart the bridge process

## Authentication Issues

### QR Code Not Displaying

**Solutions**:
- Visit `http://localhost:8080/qr` in your browser instead of checking the terminal
- If the page shows "no QR code available", restart the bridge or use a WhatsApp tool to trigger authentication
- Wait 5-10 seconds after starting the bridge

### QR Code Expired

**Solution**: Refresh the QR code page or restart the bridge to generate a new QR code

### WhatsApp Already Logged In

**Solution**: If your session is already active, the bridge will automatically reconnect without showing a QR code. This is normal behavior.

### Device Limit Reached

**Issue**: Cannot link new device

**Solution**: WhatsApp limits linked devices. Remove an existing device:
1. Open WhatsApp on your phone
2. Go to Settings → Linked Devices
3. Remove an old device
4. Try scanning the QR code again

### Authentication Timeout

**Solution**: Try using the `check_bridge_status` tool which will attempt to restart the authentication process

### Re-authentication Required

**Issue**: Need to re-authenticate after ~20 days

**Solution**: This is normal WhatsApp behavior. Visit `http://localhost:8080/qr` and scan the new QR code with your phone.

## Port Issues

### Port Already in Use

**Issue**: Error indicates port is already in use

**Solutions**:

For bridge port (8080):
```bash
# Find process using port
lsof -i :8080

# Kill the process
kill $(lsof -t -i:8080)
```

For MCP server port (3000):
```bash
# Find process using port
lsof -i :3000

# Kill the process
kill $(lsof -t -i:3000)
```

### Multiple Instances Running

**Issue**: Multiple bridge or MCP server instances are running

**Solution**: Stop all instances and restart
```bash
# Stop bridge
pkill -f 'go run main.go'

# Stop MCP server
pkill -f 'uv run main.py'

# Or use the start script
./start-mcp.sh stop
```

## Supabase Issues

### Session Tables Missing

**Issue**: Bridge fails to start with Postgres/Supabase sessions

**Solution**: Run the session tables migration
```bash
psql "$WHATSAPP_SESSION_DATABASE_URL" -f whatsapp-mcp-server/migrations/010_create_whatsmeow_session_tables.sql
```

**Verification**:
```sql
SELECT to_regclass('public.devices');
-- Should return: "devices"
```

### RLS Permissions

**Issue**: Cannot access session tables

**Solution**: Ensure you're using the Supabase **service key**, not the anon key. Session tables have RLS enabled with deny-all policies by default.

```bash
# Check RLS permissions
psql "$WHATSAPP_SESSION_DATABASE_URL" -c "
SELECT grantee, privilege_type FROM information_schema.table_privileges
WHERE table_name = 'devices';
"
# Should show service_role has SELECT, INSERT, UPDATE, DELETE
```

### Connection String Format

**Issue**: Cannot connect to Supabase

**Solution**: Ensure connection string includes `?sslmode=require`
```bash
# Correct format
postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres?sslmode=require

# Verify
echo $WHATSAPP_SESSION_DATABASE_URL | grep sslmode=require
```

## Cloud Run Issues

### Deployment Failures

**Issue**: Cloud Run deployment fails

**Solutions**:

1. **Check API enablement**:
```bash
gcloud services list --enabled --project=YOUR_PROJECT_ID
```

2. **Verify service account permissions**:
```bash
gcloud projects get-iam-policy ${GCP_PROJECT_ID} \
  --flatten="bindings[].members" \
  --filter="bindings.members:whatsapp-mcp-sa"
```

3. **Check container build**:
```bash
gcloud builds list --limit=5
```

### Secret Access Issues

**Issue**: Cannot access secrets from Cloud Run

**Solutions**:

1. **Verify secrets exist**:
```bash
gcloud secrets list --project=YOUR_PROJECT_ID
```

2. **Check service account has access**:
```bash
gcloud secrets get-iam-policy SECRET_NAME --project=YOUR_PROJECT_ID
```

3. **Grant access if needed**:
```bash
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:whatsapp-mcp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Storage Permission Issues

**Issue**: Cannot access GCS bucket

**Solution**: Grant storage permissions at bucket level
```bash
gcloud storage buckets add-iam-policy-binding \
  gs://PROJECT_ID-whatsapp-sessions \
  --member="serviceAccount:whatsapp-mcp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### OAuth Errors

**Issue**: OAuth authentication failing

**Solutions**:

1. **Check token validity**:
```bash
# Generate a new token
TOKEN=$(gcloud auth print-identity-token --audiences=YOUR_CLIENT_ID.apps.googleusercontent.com)

# Test with health endpoint (should bypass OAuth)
curl -v "https://YOUR-SERVICE-URL/health"  # Should return 200 OK
```

2. **Verify audience configuration**:
- Ensure `OAUTH_AUDIENCE` matches your Google OAuth Client ID
- For Google ID tokens, audience claim equals the OAuth Client ID

3. **Check CORS settings** if accessing from browser

## Log Analysis

### View Bridge Logs

```bash
# If using start-mcp.sh
./start-mcp.sh logs bridge

# Or view log file directly
tail -f bridge.log

# For Cloud Run
gcloud run services logs read whatsapp-mcp --region=us-central1 --limit=50
```

### View MCP Server Logs

```bash
# If using start-mcp.sh
./start-mcp.sh logs mcp

# Or view log file directly
tail -f mcp_server.log
```

### Search Logs for Errors

```bash
# Local logs
grep -i error bridge.log
grep -i error mcp_server.log

# Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-mcp AND severity>=ERROR" --limit=50
```

## Clean Restart

If you're experiencing persistent issues, try a clean restart:

```bash
# Stop everything
./start-mcp.sh stop

# Remove old logs
rm -f bridge.log mcp_server.log

# Remove PIDs
rm -f bridge.pid mcp_server.pid

# Optional: Remove databases to start fresh (will lose all data!)
# rm -rf whatsapp-bridge/store/*.db

# Start fresh
./start-mcp.sh start
```

## Additional Resources

- **Status Monitoring**: See [status.md](status.md) for comprehensive status monitoring
- **Database Setup**: See [database.md](database.md) for database configuration
- **Migrations**: See [migrations.md](migrations.md) for schema setup
- **MCP Documentation**: [Model Context Protocol docs](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues)
- **Cloud Run Deployment**: See [deployment/cloud-run.md](deployment/cloud-run.md)
- **Docker Setup**: See [deployment/docker.md](deployment/docker.md)

## Getting Help

If you continue to experience issues:

1. Check the status dashboard for specific error messages
2. Review relevant logs for detailed error information
3. Verify all prerequisites are installed and configured
4. Ensure migrations have been applied
5. Check that all required ports are available
6. Verify environment variables are set correctly
