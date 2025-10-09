#!/usr/bin/env bash
set -euo pipefail

# Configuration (override with env or flags)
PROJECT_ID=${PROJECT_ID:-whatsapp-465919}
REGION=${REGION:-me-west1}
REPO=${REPO:-cloud-run}
BRIDGE_SVC=${BRIDGE_SVC:-whatsapp-bridge}
MCP_SVC=${MCP_SVC:-whatsapp-mcp}
MCP_SA_NAME=${MCP_SA_NAME:-mcp-invoker}

usage() {
  cat <<EOF
Usage: PROJECT_ID=<id> REGION=<region> $0
Builds images with Cloud Build, pushes to Artifact Registry, and deploys two Cloud Run services.
Defaults:
  PROJECT_ID=$PROJECT_ID
  REGION=$REGION
  REPO=$REPO
  BRIDGE_SVC=$BRIDGE_SVC
  MCP_SVC=$MCP_SVC
  MCP_SA_NAME=$MCP_SA_NAME
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI is required" >&2
  exit 1
fi

echo "==> Setting project to $PROJECT_ID"
gcloud config set project "$PROJECT_ID" 1>/dev/null

# Enable required APIs (idempotent)
echo "==> Enabling required APIs"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com iamcredentials.googleapis.com --project "$PROJECT_ID"

# Ensure Artifact Registry repo exists (idempotent)
echo "==> Ensuring Artifact Registry repository exists: $REPO ($REGION)"
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Cloud Run images" \
    --project "$PROJECT_ID"
fi

SHORT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "local")
BRIDGE_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$BRIDGE_SVC:$SHORT_SHA"
MCP_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$MCP_SVC:$SHORT_SHA"

# Build images with Cloud Build
echo "==> Building and pushing bridge image: $BRIDGE_IMAGE"
gcloud builds submit --tag "$BRIDGE_IMAGE" whatsapp-bridge --project "$PROJECT_ID"

echo "==> Building and pushing MCP image: $MCP_IMAGE"
gcloud builds submit --tag "$MCP_IMAGE" whatsapp-mcp-server --project "$PROJECT_ID"

# Create MCP service account (idempotent)
MCP_SA_EMAIL="$MCP_SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$MCP_SA_EMAIL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  echo "==> Creating service account: $MCP_SA_EMAIL"
  gcloud iam service-accounts create "$MCP_SA_NAME" \
    --display-name="MCP Invoker" \
    --project "$PROJECT_ID"
fi

# Deploy bridge (authenticated only)
echo "==> Deploying $BRIDGE_SVC"
gcloud run deploy "$BRIDGE_SVC" \
  --image "$BRIDGE_IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --platform managed \
  --no-allow-unauthenticated \
  --min-instances=1 \
  --cpu=0.25 \
  --memory=512Mi \
  --port=8080 \
  --quiet

BRIDGE_URL=$(gcloud run services describe "$BRIDGE_SVC" \
  --region "$REGION" --project "$PROJECT_ID" \
  --format='value(status.url)')

echo "Bridge URL: $BRIDGE_URL"

# Allow MCP service account to invoke the bridge (service-to-service auth)
echo "==> Granting roles/run.invoker on $BRIDGE_SVC to $MCP_SA_EMAIL"
gcloud run services add-iam-policy-binding "$BRIDGE_SVC" \
  --region "$REGION" --project "$PROJECT_ID" \
  --member "serviceAccount:$MCP_SA_EMAIL" \
  --role roles/run.invoker \
  --quiet

# Deploy MCP (authenticated only) with env vars pointing at the bridge
echo "==> Deploying $MCP_SVC"
gcloud run deploy "$MCP_SVC" \
  --image "$MCP_IMAGE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --platform managed \
  --no-allow-unauthenticated \
  --min-instances=1 \
  --cpu=0.25 \
  --memory=512Mi \
  --port=8080 \
  --service-account "$MCP_SA_EMAIL" \
  --set-env-vars "TRANSPORT_MODE=http,WHATSAPP_API_BASE_URL=${BRIDGE_URL}/api,BRIDGE_AUDIENCE=${BRIDGE_URL}" \
  --quiet

MCP_URL=$(gcloud run services describe "$MCP_SVC" \
  --region "$REGION" --project "$PROJECT_ID" \
  --format='value(status.url)')

echo "MCP URL: $MCP_URL"

echo "==> Success"
echo "Authenticated Cloud Run services deployed:"
echo "  Bridge: $BRIDGE_URL"
echo "  MCP:    $MCP_URL"
