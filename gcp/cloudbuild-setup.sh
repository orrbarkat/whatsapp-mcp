#!/bin/bash

# Cloud Build Setup Script for WhatsApp MCP Server
# This script configures Cloud Build triggers, IAM permissions, and Artifact Registry

set -euo pipefail

# Configuration
SCRIPT_NAME="$(basename "$0")"
REGION="${REGION:-europe-west6}"
REPOSITORY="${REPOSITORY:-whatsapp-mcp}"
SERVICE_NAME="${SERVICE_NAME:-whatsapp-mcp-server}"
SKIP_TRIGGER=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "${LOG_FILE}"
}

# Show usage information
show_usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS]

Cloud Build Setup Script for WhatsApp MCP Server
This script configures Cloud Build triggers, IAM permissions, and Artifact Registry
for automated deployment of the WhatsApp MCP Server to Google Cloud Run.

OPTIONS:
  --skip-trigger, --no-trigger    Skip Cloud Build trigger creation
                                  (useful when setting up infrastructure without
                                  configuring GitHub/CSR repository connections)
  --help, -h                      Show this help message and exit

EXAMPLES:
  # Full setup including triggers
  ${SCRIPT_NAME}

  # Setup infrastructure only, skip trigger creation
  ${SCRIPT_NAME} --skip-trigger

  # Setup with custom region and repository
  REGION=us-central1 REPOSITORY=my-repo ${SCRIPT_NAME}

PREREQUISITES:
  1. gcloud CLI installed and authenticated (gcloud auth login)
  2. Active GCP project configured (gcloud config set project PROJECT_ID)
  3. Required APIs will be enabled automatically:
     - cloudbuild.googleapis.com
     - run.googleapis.com
     - artifactregistry.googleapis.com
     - sqladmin.googleapis.com
     - secretmanager.googleapis.com
  4. For GitHub triggers: GitHub App connection configured in Cloud Build
     (https://console.cloud.google.com/cloud-build/connections)
  5. For CSR triggers: Cloud Source Repository created
     (gcloud source repos create whatsapp-mcp)

ENVIRONMENT VARIABLES:
  REGION         GCP region for resources (default: europe-west6)
  REPOSITORY     Artifact Registry repository name (default: whatsapp-mcp)
  SERVICE_NAME   Cloud Run service name (default: whatsapp-mcp-server)

For more information, see: gcp/README.md
EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --skip-trigger|--no-trigger)
                SKIP_TRIGGER=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo ""
                show_usage
                exit 1
                ;;
        esac
    done
}

# Get project information
get_project_info() {
    log_info "Fetching project information..."

    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "${PROJECT_ID}" ]]; then
        log_error "No active GCP project set. Run: gcloud config set project PROJECT_ID"
        exit 1
    fi

    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
    CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

    log_success "Project ID: ${PROJECT_ID}"
    log_success "Project Number: ${PROJECT_NUMBER}"
    log_success "Cloud Build Service Account: ${CLOUDBUILD_SA}"
}

# Initialize logging
init_logging() {
    LOG_FILE="/tmp/cloudbuild-setup-${PROJECT_ID}.log"
    echo "=== Cloud Build Setup Log ===" > "${LOG_FILE}"
    echo "Started at: $(date)" >> "${LOG_FILE}"
    echo "Project: ${PROJECT_ID}" >> "${LOG_FILE}"
    echo "" >> "${LOG_FILE}"
    log_info "Logging to: ${LOG_FILE}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    log_success "gcloud authentication: OK"

    # Check if project is set
    if [[ -z "${PROJECT_ID}" ]]; then
        log_error "No project set. Run: gcloud config set project PROJECT_ID"
        exit 1
    fi
    log_success "Project configured: ${PROJECT_ID}"

    # Check required APIs
    log_info "Checking required APIs..."
    local required_apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
    )

    local missing_apis=()
    for api in "${required_apis[@]}"; do
        if gcloud services list --enabled --filter="name:${api}" --format="value(name)" 2>/dev/null | grep -q "${api}"; then
            log_success "API enabled: ${api}"
        else
            log_warning "API not enabled: ${api}"
            missing_apis+=("${api}")
        fi
    done

    if [[ ${#missing_apis[@]} -gt 0 ]]; then
        log_info "Enabling missing APIs..."
        for api in "${missing_apis[@]}"; do
            log_info "Enabling ${api}..."
            gcloud services enable "${api}" --project="${PROJECT_ID}"
            log_success "Enabled: ${api}"
        done
    fi

    log_success "All required APIs are enabled"
}

# Create Artifact Registry repository
create_artifact_registry() {
    log_info "Checking Artifact Registry repository..."

    if gcloud artifacts repositories describe "${REPOSITORY}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" &>/dev/null; then
        log_success "Artifact Registry repository already exists: ${REPOSITORY}"
    else
        log_info "Creating Artifact Registry repository: ${REPOSITORY}"
        gcloud artifacts repositories create "${REPOSITORY}" \
            --repository-format=docker \
            --location="${REGION}" \
            --description="WhatsApp MCP Server container images" \
            --project="${PROJECT_ID}"
        log_success "Created Artifact Registry repository: ${REPOSITORY}"
    fi

    # Verify repository
    local repo_url="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}"
    log_success "Repository URL: ${repo_url}"
}

# Validate Artifact Registry exists
validate_artifact_registry() {
    log_info "Validating Artifact Registry repository..."

    if ! gcloud artifacts repositories describe "${REPOSITORY}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" &>/dev/null; then
        log_error "Artifact Registry repository '${REPOSITORY}' does not exist in region '${REGION}'"
        log_error ""
        log_error "To fix this issue, either:"
        log_error "  1. Run the full setup without --skip-trigger flag to create the repository:"
        log_error "     ${SCRIPT_NAME}"
        log_error ""
        log_error "  2. Or create the repository manually:"
        log_error "     gcloud artifacts repositories create ${REPOSITORY} \\"
        log_error "       --repository-format=docker \\"
        log_error "       --location=${REGION} \\"
        log_error "       --project=${PROJECT_ID}"
        exit 1
    fi

    log_success "Artifact Registry repository validated: ${REPOSITORY}"
}

# Grant IAM permissions to Cloud Build service account
grant_cloudbuild_permissions() {
    log_info "Configuring Cloud Build service account IAM permissions..."

    local roles=(
        "roles/run.admin"
        "roles/iam.serviceAccountUser"
        "roles/artifactregistry.writer"
    )

    log_info "Cloud Build Service Account: ${CLOUDBUILD_SA}"

    for role in "${roles[@]}"; do
        log_info "Checking role: ${role}"

        # Check if binding already exists
        if gcloud projects get-iam-policy "${PROJECT_ID}" \
            --flatten="bindings[].members" \
            --filter="bindings.role:${role} AND bindings.members:serviceAccount:${CLOUDBUILD_SA}" \
            --format="value(bindings.role)" 2>/dev/null | grep -q "${role}"; then
            log_success "Role already granted: ${role}"
        else
            log_info "Granting role: ${role}"
            gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
                --member="serviceAccount:${CLOUDBUILD_SA}" \
                --role="${role}" \
                --condition=None \
                --quiet
            log_success "Granted role: ${role}"
        fi
    done

    log_success "IAM permissions configured"
    echo ""
    log_info "Summary of roles granted to ${CLOUDBUILD_SA}:"
    for role in "${roles[@]}"; do
        echo "  - ${role}" | tee -a "${LOG_FILE}"
    done
}

# Create Cloud Build trigger
create_cloudbuild_trigger() {
    # Early return if SKIP_TRIGGER is set
    if [[ "${SKIP_TRIGGER}" == "true" ]]; then
        log_info "Skipping Cloud Build trigger creation (--skip-trigger flag set)"
        return 0
    fi

    log_info "Configuring Cloud Build trigger..."

    # Validate that Artifact Registry exists before creating triggers
    validate_artifact_registry

    local trigger_name="whatsapp-mcp-main-trigger"

    # Check if trigger already exists (with consistent region usage)
    if gcloud builds triggers describe "${trigger_name}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" &>/dev/null; then
        log_warning "Trigger already exists: ${trigger_name}"
        log_info "Updating existing trigger..."

        # Delete and recreate to ensure correct configuration (with consistent region usage)
        gcloud builds triggers delete "${trigger_name}" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --quiet
        log_info "Deleted existing trigger"
    fi

    # Detect repository type
    log_info "Detecting repository connection type..."

    # Check for GitHub connection
    local github_connections
    github_connections=$(gcloud builds connections list --region="${REGION}" --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || echo "")

    if [[ -n "${github_connections}" ]]; then
        # Handle GitHub connections
        local connections_array=()
        while IFS= read -r line; do
            [[ -n "$line" ]] && connections_array+=("$line")
        done <<< "${github_connections}"

        local connection_name=""
        local num_connections=${#connections_array[@]}

        if [[ ${num_connections} -eq 0 ]]; then
            # This shouldn't happen due to the outer check, but handle it anyway
            log_error "No GitHub App connections found."
            log_error ""
            log_error "A GitHub App connection is required to create triggers for GitHub-hosted repositories."
            log_error "To fix this issue, choose one of the following options:"
            log_error ""
            log_error "  1. Create a GitHub App connection in the Cloud Build console:"
            log_error "     https://console.cloud.google.com/cloud-build/connections"
            log_error ""
            log_error "  2. Use Cloud Source Repositories instead (requires creating a CSR repo):"
            log_error "     gcloud source repos create whatsapp-mcp"
            log_error ""
            log_error "  3. Skip trigger creation for now and set up manually later:"
            log_error "     ${SCRIPT_NAME} --skip-trigger"
            exit 1
        elif [[ ${num_connections} -eq 1 ]]; then
            connection_name="${connections_array[0]}"
            log_info "Found one GitHub connection: ${connection_name}"
        else
            log_info "Found ${num_connections} GitHub connections:"
            for i in "${!connections_array[@]}"; do
                echo "  $((i+1)). ${connections_array[i]}"
            done
            echo ""
            read -rp "Select connection number (1-${num_connections}): " selection

            if [[ ! "${selection}" =~ ^[0-9]+$ ]] || [[ ${selection} -lt 1 ]] || [[ ${selection} -gt ${num_connections} ]]; then
                log_error "Invalid selection. Exiting."
                exit 1
            fi

            connection_name="${connections_array[$((selection-1))]}"
            log_info "Selected connection: ${connection_name}"
        fi

        # Get the list of repositories for this connection
        local repositories
        repositories=$(gcloud builds repositories list --connection="${connection_name}" --region="${REGION}" --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || echo "")

        if [[ -z "${repositories}" ]]; then
            log_error "No repositories found for connection '${connection_name}'"
            log_error ""
            log_error "Please connect a repository to this GitHub App connection:"
            log_error "  https://console.cloud.google.com/cloud-build/repositories"
            log_error ""
            log_error "Or skip trigger creation for now:"
            log_error "  ${SCRIPT_NAME} --skip-trigger"
            exit 1
        fi

        local repositories_array=()
        while IFS= read -r line; do
            [[ -n "$line" ]] && repositories_array+=("$line")
        done <<< "${repositories}"

        local repo_name=""
        local num_repos=${#repositories_array[@]}

        if [[ ${num_repos} -eq 1 ]]; then
            repo_name="${repositories_array[0]}"
            log_info "Found one repository: ${repo_name}"
        else
            log_info "Found ${num_repos} repositories:"
            for i in "${!repositories_array[@]}"; do
                echo "  $((i+1)). ${repositories_array[i]}"
            done
            echo ""
            read -rp "Select repository number (1-${num_repos}): " selection

            if [[ ! "${selection}" =~ ^[0-9]+$ ]] || [[ ${selection} -lt 1 ]] || [[ ${selection} -gt ${num_repos} ]]; then
                log_error "Invalid selection. Exiting."
                exit 1
            fi

            repo_name="${repositories_array[$((selection-1))]}"
            log_info "Selected repository: ${repo_name}"
        fi

        local repository_resource="projects/${PROJECT_ID}/locations/${REGION}/connections/${connection_name}/repositories/${repo_name}"

        # Confirmation prompt
        echo ""
        log_info "About to create trigger with the following configuration:"
        echo "  Trigger name: ${trigger_name}"
        echo "  Connection: ${connection_name}"
        echo "  Repository: ${repo_name}"
        echo "  Branch pattern: ^main$"
        echo "  Build config: cloudbuild.yaml"
        echo "  Region: ${REGION}"
        echo ""
        read -rp "Proceed with trigger creation? (y/N): " confirm

        if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
            log_info "Trigger creation cancelled by user"
            exit 0
        fi

        log_info "Creating GitHub trigger for ${repository_resource}"

        # Create trigger with error handling
        if gcloud builds triggers create github \
            --name="${trigger_name}" \
            --repository="${repository_resource}" \
            --branch-pattern="^main$" \
            --build-config="cloudbuild.yaml" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}" 2>&1 | tee -a "${LOG_FILE}"; then
            log_success "Created GitHub trigger: ${trigger_name}"
        else
            local exit_code=$?
            log_error "Failed to create trigger (exit code: ${exit_code})"
            log_error ""
            log_error "Common causes and solutions:"
            log_error "  1. Repository not granted access to Cloud Build:"
            log_error "     - Visit: https://console.cloud.google.com/cloud-build/repositories"
            log_error "     - Ensure the repository is connected and has proper permissions"
            log_error ""
            log_error "  2. Insufficient IAM permissions:"
            log_error "     - Required role: roles/cloudbuild.builds.editor or higher"
            log_error "     - Visit: https://console.cloud.google.com/iam-admin/iam"
            log_error ""
            log_error "  3. Invalid region:"
            log_error "     - Current region: ${REGION}"
            log_error "     - Ensure the connection exists in this region"
            log_error ""
            log_error "  4. Connection or repository resource not found:"
            log_error "     - Visit: https://console.cloud.google.com/cloud-build/connections"
            log_error ""
            log_error "See full error details in: ${LOG_FILE}"
            exit 1
        fi
    else
        # No GitHub connections - error out instead of silently falling back to CSR
        log_error "No GitHub App connections found."
        log_error ""
        log_error "A GitHub App connection is required to create triggers for GitHub-hosted repositories."
        log_error "To fix this issue, choose one of the following options:"
        log_error ""
        log_error "  1. Create a GitHub App connection in the Cloud Build console:"
        log_error "     https://console.cloud.google.com/cloud-build/connections"
        log_error ""
        log_error "  2. Use Cloud Source Repositories instead (after creating a CSR repo):"
        log_error "     gcloud source repos create whatsapp-mcp"
        log_error "     Then set USE_CSR=true and re-run this script"
        log_error ""
        log_error "  3. Skip trigger creation for now and set up manually later:"
        log_error "     ${SCRIPT_NAME} --skip-trigger"
        exit 1
    fi

    # Describe trigger to confirm
    log_info "Trigger configuration:"
    gcloud builds triggers describe "${trigger_name}" \
        --project="${PROJECT_ID}" \
        --region="${REGION}" | tee -a "${LOG_FILE}"

    log_success "Cloud Build trigger configured successfully"
}

# Test manual build
test_manual_build() {
    log_info "Testing manual build..."

    echo ""
    log_warning "This will submit a build to Cloud Build and may incur charges."
    read -rp "Do you want to run a manual build test? (y/N): " response

    if [[ "${response}" =~ ^[Yy]$ ]]; then
        log_info "Submitting build to Cloud Build..."

        if gcloud builds submit \
            --config=cloudbuild.yaml \
            --project="${PROJECT_ID}" \
            --region="${REGION}" \
            --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}"; then
            log_success "Build completed successfully"
            return 0
        else
            log_error "Build failed. Check logs above for details."
            return 1
        fi
    else
        log_info "Skipping manual build test"
        log_info "To run manually: gcloud builds submit --config=cloudbuild.yaml --project=${PROJECT_ID}"
    fi
}

# Verify deployment
verify_deployment() {
    log_info "Verifying Cloud Run deployment..."

    # Get Cloud Run service URL
    local service_url
    service_url=$(gcloud run services describe "${SERVICE_NAME}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --format="value(status.url)" 2>/dev/null || echo "")

    if [[ -z "${service_url}" ]]; then
        log_warning "Cloud Run service not found: ${SERVICE_NAME}"
        log_info "The service will be created on the first successful build"
        return 0
    fi

    log_success "Cloud Run service URL: ${service_url}"

    # Test health endpoint
    log_info "Testing health endpoint..."
    if curl -sf "${service_url}/health" -o /dev/null; then
        log_success "Health check passed: ${service_url}/health"
    else
        log_warning "Health check failed or endpoint not available"
        log_info "Troubleshooting tips:"
        echo "  1. Check Cloud Run logs: gcloud run services logs read ${SERVICE_NAME} --region=${REGION}" | tee -a "${LOG_FILE}"
        echo "  2. Verify environment variables and secrets are configured" | tee -a "${LOG_FILE}"
        echo "  3. Check Cloud SQL connection: gcloud sql instances describe <INSTANCE_NAME>" | tee -a "${LOG_FILE}"
        echo "  4. Review build logs: gcloud builds log <BUILD_ID>" | tee -a "${LOG_FILE}"
    fi
}

# Main setup function
main() {
    # Parse command line arguments first
    parse_arguments "$@"

    echo "================================"
    echo "Cloud Build Setup for WhatsApp MCP"
    echo "================================"
    echo ""

    # Get project info first
    get_project_info

    # Initialize logging
    init_logging

    # Run setup steps
    check_prerequisites
    echo ""

    create_artifact_registry
    echo ""

    grant_cloudbuild_permissions
    echo ""

    # Only call create_cloudbuild_trigger if not skipping
    # (The function itself also checks SKIP_TRIGGER, but we control the call here too)
    if [[ "${SKIP_TRIGGER}" != "true" ]]; then
        create_cloudbuild_trigger
        echo ""
    else
        log_info "Trigger creation skipped (--skip-trigger flag set)"
        echo ""
    fi

    # Optional: test manual build (only if trigger was created)
    if [[ "${SKIP_TRIGGER}" != "true" ]]; then
        if test_manual_build; then
            echo ""
            verify_deployment
        fi
    fi

    echo ""
    log_success "Cloud Build setup completed successfully!"
    echo ""
    echo "================================"
    echo "Next Steps:"
    echo "================================"

    if [[ "${SKIP_TRIGGER}" == "true" ]]; then
        echo "Trigger creation was skipped. To create triggers later:"
        echo ""
        echo "Option 1: GitHub-hosted repository (recommended)"
        echo "  1. Create a GitHub App connection:"
        echo "     https://console.cloud.google.com/cloud-build/connections"
        echo "  2. Connect your repository through the console"
        echo "  3. Re-run this script without --skip-trigger flag:"
        echo "     ${SCRIPT_NAME}"
        echo ""
        echo "Option 2: Cloud Source Repositories"
        echo "  1. Create a Cloud Source Repository:"
        echo "     gcloud source repos create whatsapp-mcp"
        echo "  2. Set up repository mirroring or push your code to CSR"
        echo "  3. Manually create the trigger through the console or gcloud CLI"
        echo ""
        echo "Option 3: Manual trigger creation"
        echo "  Visit: https://console.cloud.google.com/cloud-build/triggers"
        echo ""
    else
        echo "1. Push your code to the main branch to trigger a build"
        echo "2. Monitor builds: gcloud builds list --project=${PROJECT_ID}"
        echo "3. View build logs: gcloud builds log <BUILD_ID>"
        echo "4. Check Cloud Run service: gcloud run services describe ${SERVICE_NAME} --region=${REGION}"
    fi

    echo ""
    echo "Common commands:"
    echo "  Manual build:"
    echo "    gcloud builds submit --config=cloudbuild.yaml --project=${PROJECT_ID} --region=${REGION}"
    echo ""
    echo "  View logs: ${LOG_FILE}"
    echo ""
    if [[ "${SKIP_TRIGGER}" != "true" ]]; then
        echo "  Health check (after deployment):"
        echo "    curl \$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')/health"
        echo ""
    fi
}

# Run main function
main "$@"
