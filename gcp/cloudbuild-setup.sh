#!/bin/bash

# Cloud Build Setup Script for WhatsApp MCP Server
# This script configures Cloud Build triggers, IAM permissions, and Artifact Registry

set -euo pipefail

# Configuration
SCRIPT_NAME="$(basename "$0")"
REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-whatsapp-mcp}"
SERVICE_NAME="${SERVICE_NAME:-whatsapp-mcp-server}"

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
    log_info "Configuring Cloud Build trigger..."

    local trigger_name="whatsapp-mcp-main-trigger"

    # Check if trigger already exists
    if gcloud builds triggers describe "${trigger_name}" \
        --project="${PROJECT_ID}" &>/dev/null; then
        log_warning "Trigger already exists: ${trigger_name}"
        log_info "Updating existing trigger..."

        # Delete and recreate to ensure correct configuration
        gcloud builds triggers delete "${trigger_name}" \
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
        log_info "GitHub connections found. Creating GitHub trigger..."

        # Get repository information
        local repo_owner repo_name
        read -rp "Enter GitHub repository owner: " repo_owner
        read -rp "Enter GitHub repository name: " repo_name

        gcloud builds triggers create github \
            --name="${trigger_name}" \
            --repo-owner="${repo_owner}" \
            --repo-name="${repo_name}" \
            --branch-pattern="^main$" \
            --build-config="cloudbuild.yaml" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}"

        log_success "Created GitHub trigger: ${trigger_name}"
    else
        log_info "No GitHub connections found. Creating Cloud Source Repository trigger..."

        # Use Cloud Source Repository
        gcloud builds triggers create cloud-source-repositories \
            --name="${trigger_name}" \
            --repo="whatsapp-mcp" \
            --branch-pattern="^main$" \
            --build-config="cloudbuild.yaml" \
            --region="${REGION}" \
            --project="${PROJECT_ID}" \
            --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE_NAME=${SERVICE_NAME}"

        log_success "Created Cloud Source Repository trigger: ${trigger_name}"
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

    create_cloudbuild_trigger
    echo ""

    # Optional: test manual build
    if test_manual_build; then
        echo ""
        verify_deployment
    fi

    echo ""
    log_success "Cloud Build setup completed successfully!"
    echo ""
    echo "================================"
    echo "Next Steps:"
    echo "================================"
    echo "1. Push your code to the main branch to trigger a build"
    echo "2. Monitor builds: gcloud builds list --project=${PROJECT_ID}"
    echo "3. View build logs: gcloud builds log <BUILD_ID>"
    echo "4. Check Cloud Run service: gcloud run services describe ${SERVICE_NAME} --region=${REGION}"
    echo "5. View logs: ${LOG_FILE}"
    echo ""
    echo "Manual build command:"
    echo "  gcloud builds submit --config=cloudbuild.yaml --project=${PROJECT_ID}"
    echo ""
    echo "Manual verification command:"
    echo "  curl \$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')/health"
    echo ""
}

# Run main function
main "$@"
