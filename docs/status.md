# Status Monitoring

This guide covers the status monitoring capabilities of the WhatsApp MCP server.

## Overview

The WhatsApp MCP server includes comprehensive status monitoring through multiple interfaces:

- **MCP Resources**: JSON and HTML status data accessible via MCP clients
- **MCP Tools**: Interactive status checking tools callable from Claude
- **Web Dashboard**: Browser-based visual status monitoring
- **API Endpoints**: Direct JSON status queries

## Status Endpoints

### Web Dashboard

Access a visual status dashboard at `http://localhost:8080/status` when the bridge is running:

- Real-time bridge and authentication status
- Database statistics (message count, chat count, database size)
- Last sync timestamp
- Auto-refresh every 30 seconds
- Visual status indicators with color-coded badges

### QR Code Page

View the authentication QR code at `http://localhost:8080/qr`:

- Displays QR code for WhatsApp authentication
- Shows when QR code needs to be scanned
- Automatically updates when authentication state changes

### API Endpoints

**Status API**: `http://localhost:8080/api/status`
- Returns comprehensive JSON status data
- Includes bridge health, authentication state, database stats
- Used by MCP tools and resources

**Session Backend API**: `http://localhost:8080/api/session-backend`
- Returns session storage backend information
- Shows whether using SQLite or Postgres for sessions
- Includes validation status and connection details

## MCP Resources

Claude can access these resources for status information:

### whatsapp://sync-status

**Purpose**: Read-only JSON data source for status information

**Data Provided**:
- Bridge status (running, authenticated, API responsive)
- Sync statistics (message count, chat count)
- Database metrics (file size, existence)
- Last sync timestamp
- Error messages (if any)

**Use Case**: Static status reports for reference in conversations

**How to Access**: View available resources in Claude Desktop and access `whatsapp://sync-status`

### whatsapp://status-ui

**Purpose**: Rich HTML interface with visual status display

**Features**:
- Visual status cards with CSS styling
- Real-time data integration
- Color-coded status indicators
- Responsive grid layout
- Database statistics display

**Use Case**: Rich client UI for comprehensive status overview

**How to Access**: Access via Claude Desktop resource viewer

## MCP Tools

### get_sync_status

**Purpose**: Get comprehensive sync status including bridge health, database statistics, and last sync time

**Features**:
- Returns real-time status data
- Automatically starts bridge if not running
- Includes error reporting and troubleshooting guidance

**Usage**: Call the tool from Claude Desktop like any other MCP function

**Returns**:
- Bridge process status
- Authentication state
- Message and chat counts
- Database size
- Last sync time
- Error messages

### check_bridge_status

**Purpose**: Check the current status of the WhatsApp bridge and authentication

**Features**:
- Quick bridge health check
- Authentication state verification
- Automatic bridge startup if needed
- QR code availability status

**Usage**: Call when you need a quick status check

**Returns**:
- Bridge running status
- Authentication status
- QR code availability
- Error information

## Automatic Bridge Management

The MCP server includes automatic bridge management features:

- **Auto-startup**: All MCP tools automatically start the bridge if it's not running
- **Health Monitoring**: Continuous monitoring of bridge process and API responsiveness
- **Authentication Recovery**: Automatic QR code generation for re-authentication

## Status Data Provided

All monitoring interfaces show:

- **Bridge Status**: Process running, authenticated, API responsive
- **Sync Statistics**: Message count, chat count, database size
- **Timing**: Last sync time, current timestamp
- **Health**: Overall status (Ready/Not Ready), error messages
- **Database**: File size, existence check
- **Session Backend**: SQLite or Postgres, connection details

## Status Access Methods

1. **MCP Tools**: Call `get_sync_status` or `check_bridge_status` in Claude
2. **MCP Resources**: View `whatsapp://sync-status` or `whatsapp://status-ui` resources
3. **Web Interface**: Visit `http://localhost:8080/status` in your browser
4. **API Endpoint**: Access `http://localhost:8080/api/status` for JSON data

## Testing Status Monitoring

### Automatic Bridge Startup

No need to manually start the bridge! Just call any WhatsApp MCP tool and the bridge starts automatically.

### Testing Steps

1. **Setup MCP Server**: Configure in Claude Desktop (see main README)
2. **Test Auto-startup**: Call any WhatsApp tool (e.g., `check_bridge_status`)
3. **Access Interfaces**:
   - **Web Dashboard**: `http://localhost:8080/status` (after bridge starts)
   - **QR Authentication**: `http://localhost:8080/qr` (if authentication needed)
   - **MCP Resources**: Access via Claude Desktop
   - **MCP Tools**: Call status tools in Claude Desktop

### Manual Bridge Startup (Optional)

```bash
cd whatsapp-bridge && go run main.go
```

## Troubleshooting Status Monitoring

### Dashboard Not Loading

**Issue**: Status dashboard doesn't load

**Solution**: Ensure the bridge is running by calling a WhatsApp MCP tool first

### Status Shows "Not Ready"

**Issue**: Dashboard shows "Not Ready" status

**Solution**: Check individual status indicators for specific issues:
- Bridge process not running
- Authentication needed (scan QR code)
- Database connection issues

### Auto-refresh Not Working

**Issue**: Dashboard doesn't auto-refresh

**Solution**: Browser may have JavaScript disabled; manually refresh the page

### QR Code Not Displaying

**Issue**: QR code page shows "no QR code available"

**Solution**:
- Visit `http://localhost:8080/qr` instead of checking the terminal
- Restart the bridge or use a WhatsApp tool to trigger authentication
- If session is active, bridge will reconnect without showing QR code

## Monitoring Best Practices

1. **Regular Health Checks**: Use `get_sync_status` periodically to monitor system health
2. **Web Dashboard**: Keep dashboard open during active use for visual monitoring
3. **Error Tracking**: Check status after any connection issues or errors
4. **Authentication Monitoring**: Watch for authentication expiration (typically after ~20 days)
5. **Database Growth**: Monitor database size as message history grows

## Integration Benefits

- **Multiple Interfaces**: Four different ways to access status information
- **Flexibility**: Choose interface based on use case and environment
- **Reliability**: Fallback options ensure status is always accessible
- **Integration**: Seamlessly works with existing WhatsApp bridge
- **Real-time**: Live data from database and bridge process monitoring
- **Web Access**: Browser-based dashboard just like QR code interface
- **Mobile Friendly**: Responsive design works on all devices
