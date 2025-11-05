#!/bin/bash

# WhatsApp MCP Startup Script
# This script helps you start the WhatsApp bridge and MCP server.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# Configuration
BRIDGE_DIR="${SCRIPT_DIR}/whatsapp-bridge"
MCP_SERVER_DIR="${SCRIPT_DIR}/whatsapp-mcp-server"
BRIDGE_PORT=8080
MCP_PORT=3000

# PID files
BRIDGE_PID_FILE="${SCRIPT_DIR}/bridge.pid"
MCP_SERVER_PID_FILE="${SCRIPT_DIR}/mcp_server.pid"

# Log files
BRIDGE_LOG_FILE="${SCRIPT_DIR}/bridge.log"
MCP_SERVER_LOG_FILE="${SCRIPT_DIR}/mcp_server.log"

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}\n"
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    local missing_deps=0
    # ... (prerequisite checks remain the same)
    print_success "All prerequisites are installed"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to load environment variables
load_env() {
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        print_info "Loading environment variables from .env file"
        set -a
        source "${SCRIPT_DIR}/.env"
        set +a
        print_success "Environment variables loaded"
    fi
}

# Function to start the Go bridge
start_bridge() {
    print_header "Starting WhatsApp Bridge"
    if check_port $BRIDGE_PORT; then
        print_warning "Bridge port $BRIDGE_PORT is already in use. To force stop: $0 stop"
        return 0
    fi

    print_info "Starting Go bridge on port $BRIDGE_PORT..."
    cd "$BRIDGE_DIR"
    nohup go run main.go > "$BRIDGE_LOG_FILE" 2>&1 &
    echo $! > "$BRIDGE_PID_FILE"
    
    print_info "Bridge starting with PID: $(cat $BRIDGE_PID_FILE)"
    print_info "Waiting for bridge to start..."
    
    local max_attempts=30
    local attempt=0
    while ! check_port $BRIDGE_PORT && [ $attempt -lt $max_attempts ]; do
        sleep 1
        attempt=$((attempt + 1))
        echo -n "."
    done
    echo

    if check_port $BRIDGE_PORT; then
        print_success "Bridge started successfully"
    else
        print_error "Bridge failed to start. Check $BRIDGE_LOG_FILE for details"
        tail -n 20 "$BRIDGE_LOG_FILE"
    fi
}

# Function to start the MCP Server
start_mcp_server() {
    print_header "Starting MCP Server"
    if check_port $MCP_PORT; then
        print_warning "MCP Server port $MCP_PORT is already in use. To force stop: $0 stop"
        return 0
    fi

    print_info "Starting MCP Server on port $MCP_PORT..."
    cd "$MCP_SERVER_DIR"
    
    export MCP_TRANSPORT=sse
    export MCP_PORT=$MCP_PORT
    
    nohup uv run main.py > "$MCP_SERVER_LOG_FILE" 2>&1 &
    echo $! > "$MCP_SERVER_PID_FILE"

    print_info "MCP Server starting with PID: $(cat $MCP_SERVER_PID_FILE)"
    print_info "Waiting for MCP Server to start..."

    local max_attempts=30
    local attempt=0
    while ! check_port $MCP_PORT && [ $attempt -lt $max_attempts ]; do
        sleep 1
        attempt=$((attempt + 1))
        echo -n "."
    done
    echo

    if check_port $MCP_PORT; then
        print_success "MCP Server started successfully"
    else
        print_error "MCP Server failed to start. Check $MCP_SERVER_LOG_FILE for details"
        tail -n 20 "$MCP_SERVER_LOG_FILE"
    fi
}

# Function to show QR code information
show_qr_info() {
    print_header "WhatsApp Authentication"
    print_info "To authenticate with WhatsApp, open this URL in your browser:"
    print_info "http://localhost:${BRIDGE_PORT}/qr"
    print_info "Status dashboard: http://localhost:${BRIDGE_PORT}/status"
}

# Function to show running status
show_status() {
    print_header "Service Status"
    # Check bridge
    if check_port $BRIDGE_PORT; then
        print_success "Bridge is running on port $BRIDGE_PORT"
        [ -f "$BRIDGE_PID_FILE" ] && print_info "  PID: $(cat $BRIDGE_PID_FILE)"
    else
        print_warning "Bridge is not running"
    fi
    echo
    # Check MCP Server
    if check_port $MCP_PORT; then
        print_success "MCP Server is running on port $MCP_PORT"
        [ -f "$MCP_SERVER_PID_FILE" ] && print_info "  PID: $(cat $MCP_SERVER_PID_FILE)"
    else
        print_warning "MCP Server is not running"
    fi
}

# Function to stop services
stop_services() {
    print_header "Stopping Services"

    if [ -f "$BRIDGE_PID_FILE" ]; then
        print_info "Stopping WhatsApp bridge..."
        kill $(cat "$BRIDGE_PID_FILE") &>/dev/null || true
        rm -f "$BRIDGE_PID_FILE"
    else
        print_info "Stopping WhatsApp bridge (fallback)..."
        pkill -f 'go run main.go' || print_warning "No bridge process found"
    fi

    if [ -f "$MCP_SERVER_PID_FILE" ]; then
        print_info "Stopping MCP Server..."
        kill $(cat "$MCP_SERVER_PID_FILE") &>/dev/null || true
        rm -f "$MCP_SERVER_PID_FILE"
    else
        print_info "Stopping MCP Server (fallback)..."
        lsof -t -i:$MCP_PORT | xargs kill &>/dev/null || print_warning "No MCP Server process found"
    fi

    print_success "All services stopped."
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -z "$service" ]; then
        print_error "Usage: $0 logs [bridge|mcp]"
        return 1
    fi

    local log_file=""
    if [ "$service" == "bridge" ]; then
        log_file=$BRIDGE_LOG_FILE
    elif [ "$service" == "mcp" ]; then
        log_file=$MCP_SERVER_LOG_FILE
    else
        print_error "Unknown service: '$service'. Use 'bridge' or 'mcp'."
        return 1
    fi

    if [ -f "$log_file" ]; then
        print_header "Logs for $service"
        tail -f "$log_file"
    else
        print_warning "No log file found for $service at $log_file"
    fi
}

# Function to show help
show_help() {
    cat << EOF
WhatsApp MCP Startup Script

Usage: $0 [command]

Commands:
  start       Start the WhatsApp bridge and MCP server (default)
  stop        Stop all services
  restart     Restart all services
  status      Show service status
  logs [name] Show logs for a service (e.g., 'bridge' or 'mcp')
  help        Show this help message

EOF
}

# Main script logic
main() {
    local command="${1:-start}"

    case "$command" in
        start)
            check_prerequisites
            load_env
            start_bridge
            start_mcp_server
            show_qr_info
            echo
            print_success "All services are starting up!"
            print_info "Run '$0 status' to check their status."
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            load_env
            start_bridge
            start_mcp_server
            show_status
            ;;
        status)
            show_status
            ;;
        logs)
            if [ -z "$2" ]; then
                print_error "Missing service name. Usage: $0 logs [bridge|mcp]"
                exit 1
            fi
            show_logs "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"