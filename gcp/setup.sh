#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
DB_INSTANCE_NAME="${DB_INSTANCE_NAME:-whatsapp-mcp-db}"
DB_NAME="${DB_NAME:-whatsapp_mcp}"
DB_USER="${DB_USER:-whatsapp_user}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-whatsapp-mcp-sa}"
BUCKET_NAME="${GCS_BUCKET_NAME:-}"
SECRET_PREFIX="${SECRET_PREFIX:-whatsapp-mcp}"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it from https://cloud.google.com/sdk/docs/install"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed. Some features may not work. Install with: brew install jq (macOS) or apt-get install jq (Linux)"
    fi

    if [ -z "$PROJECT_ID" ]; then
        print_error "GCP_PROJECT_ID environment variable is not set."
        echo "Please set it with: export GCP_PROJECT_ID=your-project-id"
        exit 1
    fi

    if [ -z "$BUCKET_NAME" ]; then
        BUCKET_NAME="${PROJECT_ID}-whatsapp-mcp-sessions"
        print_warning "GCS_BUCKET_NAME not set, using default: ${BUCKET_NAME}"
    fi

    # Check if user is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "No active gcloud authentication found. Please run: gcloud auth login"
        exit 1
    fi

    # Set the project
    gcloud config set project "$PROJECT_ID"

    print_info "Prerequisites check passed!"
}

# Function to enable required APIs
enable_apis() {
    print_info "Enabling required GCP APIs..."

    local apis=(
        "run.googleapis.com"
        "sqladmin.googleapis.com"
        "storage-api.googleapis.com"
        "storage-component.googleapis.com"
        "secretmanager.googleapis.com"
        "artifactregistry.googleapis.com"
        "cloudbuild.googleapis.com"
        "compute.googleapis.com"
        "servicenetworking.googleapis.com"
        "cloudresourcemanager.googleapis.com"
    )

    for api in "${apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            print_info "API $api is already enabled"
        else
            print_info "Enabling $api..."
            gcloud services enable "$api" --project="$PROJECT_ID"
        fi
    done

    print_info "All required APIs enabled!"
}

# Function to create service account
create_service_account() {
    print_info "Creating service account..."

    local sa_email="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

    if gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" &> /dev/null; then
        print_info "Service account $sa_email already exists"
    else
        print_info "Creating service account $SERVICE_ACCOUNT_NAME..."
        gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
            --display-name="WhatsApp MCP Service Account" \
            --project="$PROJECT_ID"
    fi

    # Grant necessary roles
    print_info "Granting IAM roles to service account..."

    local roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
    )

    for role in "${roles[@]}"; do
        if gcloud projects get-iam-policy "$PROJECT_ID" \
            --flatten="bindings[].members" \
            --filter="bindings.role:$role AND bindings.members:serviceAccount:$sa_email" \
            --format="value(bindings.role)" | grep -q "$role"; then
            print_info "Role $role already granted to service account"
        else
            print_info "Granting role $role..."
            gcloud projects add-iam-policy-binding "$PROJECT_ID" \
                --member="serviceAccount:$sa_email" \
                --role="$role" \
                --condition=None \
                --quiet
        fi
    done

    echo "$sa_email"
}

# Function to create Cloud SQL instance
create_cloud_sql() {
    print_info "Creating Cloud SQL instance..."

    if gcloud sql instances describe "$DB_INSTANCE_NAME" --project="$PROJECT_ID" &> /dev/null; then
        print_info "Cloud SQL instance $DB_INSTANCE_NAME already exists"
    else
        print_info "Creating Cloud SQL PostgreSQL instance (this may take several minutes)..."
        gcloud sql instances create "$DB_INSTANCE_NAME" \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region="$REGION" \
            --root-password="$(openssl rand -base64 32)" \
            --storage-type=SSD \
            --storage-size=10GB \
            --storage-auto-increase \
            --backup-start-time=03:00 \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=4 \
            --maintenance-release-channel=production \
            --project="$PROJECT_ID"

        print_info "Waiting for instance to be ready..."
        sleep 10
    fi

    # Create database
    if gcloud sql databases describe "$DB_NAME" --instance="$DB_INSTANCE_NAME" --project="$PROJECT_ID" &> /dev/null; then
        print_info "Database $DB_NAME already exists"
    else
        print_info "Creating database $DB_NAME..."
        gcloud sql databases create "$DB_NAME" \
            --instance="$DB_INSTANCE_NAME" \
            --project="$PROJECT_ID"
    fi

    # Create user
    if gcloud sql users list --instance="$DB_INSTANCE_NAME" --project="$PROJECT_ID" | grep -q "$DB_USER"; then
        print_info "Database user $DB_USER already exists"
        print_warning "User password not changed. To reset, use: gcloud sql users set-password"
    else
        local db_password="$(openssl rand -base64 32)"
        print_info "Creating database user $DB_USER..."
        gcloud sql users create "$DB_USER" \
            --instance="$DB_INSTANCE_NAME" \
            --password="$db_password" \
            --project="$PROJECT_ID"

        echo "$db_password" > /tmp/db_password_temp.txt
        print_info "Database password saved temporarily to /tmp/db_password_temp.txt"
    fi

    # Get connection name
    local connection_name=$(gcloud sql instances describe "$DB_INSTANCE_NAME" \
        --project="$PROJECT_ID" \
        --format="value(connectionName)")

    echo "$connection_name"
}

# Function to create GCS bucket
create_gcs_bucket() {
    print_info "Creating GCS bucket..."

    local sa_email="$1"

    if gsutil ls -b "gs://${BUCKET_NAME}" &> /dev/null; then
        print_info "Bucket gs://${BUCKET_NAME} already exists"
    else
        print_info "Creating bucket gs://${BUCKET_NAME}..."
        gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${BUCKET_NAME}"

        # Enable versioning
        gsutil versioning set on "gs://${BUCKET_NAME}"
    fi

    # Grant service account access
    print_info "Granting storage.objectAdmin role to service account on bucket..."
    gsutil iam ch "serviceAccount:${sa_email}:roles/storage.objectAdmin" "gs://${BUCKET_NAME}"

    print_info "Bucket created and configured!"
}

# Function to create secrets in Secret Manager
create_secrets() {
    print_info "Creating secrets in Secret Manager..."

    local connection_name="$1"

    # Read database password if it was just created
    local db_password=""
    if [ -f /tmp/db_password_temp.txt ]; then
        db_password=$(cat /tmp/db_password_temp.txt)
        rm /tmp/db_password_temp.txt
    else
        print_warning "Database password not found. You'll need to set DATABASE_URL manually."
        read -sp "Enter database password for $DB_USER (or press Enter to skip): " db_password
        echo
    fi

    # Create DATABASE_URL secret
    if [ -n "$db_password" ]; then
        local database_url="postgresql://${DB_USER}:${db_password}@localhost/${DB_NAME}?host=/cloudsql/${connection_name}"

        if gcloud secrets describe "${SECRET_PREFIX}-database-url" --project="$PROJECT_ID" &> /dev/null; then
            print_info "Secret ${SECRET_PREFIX}-database-url already exists, adding new version..."
            echo -n "$database_url" | gcloud secrets versions add "${SECRET_PREFIX}-database-url" --data-file=- --project="$PROJECT_ID"
        else
            print_info "Creating secret ${SECRET_PREFIX}-database-url..."
            echo -n "$database_url" | gcloud secrets create "${SECRET_PREFIX}-database-url" \
                --data-file=- \
                --replication-policy="automatic" \
                --project="$PROJECT_ID"
        fi
    fi

    # Prompt for other secrets
    print_info "You'll need to create additional secrets for:"
    echo "  - ${SECRET_PREFIX}-supabase-url (required for current app configuration)"
    echo "  - ${SECRET_PREFIX}-supabase-key (required for current app configuration)"
    echo "  - ${SECRET_PREFIX}-oauth-client-id (if OAuth is enabled)"
    echo "  - ${SECRET_PREFIX}-oauth-client-secret (if OAuth is enabled)"
    echo ""
    echo "Create them with:"
    echo "  echo -n 'YOUR_VALUE' | gcloud secrets create SECRET_NAME --data-file=- --project=$PROJECT_ID"

    print_info "Secrets setup complete!"
}

# Function to print summary
print_summary() {
    local sa_email="$1"
    local connection_name="$2"

    echo ""
    echo "=========================================="
    echo "  WhatsApp MCP GCP Setup Summary"
    echo "=========================================="
    echo ""
    echo "Project ID: $PROJECT_ID"
    echo "Region: $REGION"
    echo ""
    echo "Cloud SQL:"
    echo "  Instance: $DB_INSTANCE_NAME"
    echo "  Database: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Connection: $connection_name"
    echo ""
    echo "GCS Bucket: gs://${BUCKET_NAME}"
    echo ""
    echo "Service Account: $sa_email"
    echo ""
    echo "Next Steps:"
    echo "1. Review gcp/DATABASE_SETUP.md for database migration steps"
    echo "2. Create additional secrets (SUPABASE_URL, SUPABASE_KEY, OAuth credentials)"
    echo "3. Update gcp/env-template.yaml with your configuration"
    echo "4. Deploy to Cloud Run using gcloud run deploy"
    echo ""
    echo "Connect to database with Cloud SQL Proxy:"
    echo "  cloud-sql-proxy $connection_name &"
    echo "  psql \"host=localhost user=$DB_USER dbname=$DB_NAME\""
    echo ""
    echo "=========================================="
}

# Main execution
main() {
    print_info "Starting WhatsApp MCP GCP Setup..."
    echo ""

    check_prerequisites
    enable_apis

    sa_email=$(create_service_account)
    connection_name=$(create_cloud_sql)
    create_gcs_bucket "$sa_email"
    create_secrets "$connection_name"

    print_summary "$sa_email" "$connection_name"

    print_info "Setup complete!"
}

# Run main function
main "$@"
