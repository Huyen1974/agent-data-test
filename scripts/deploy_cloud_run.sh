#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="${PROJECT:-github-chatgpt-ggcloud}"
REGION="${REGION:-asia-southeast1}"
SERVICE="${SERVICE:-agent-data-test}"
REPO_ID="${REPO_ID:-agent-data-test-images}"
IMAGE_NAME="${IMAGE_NAME:-agent-data-test}"

REG_HOST="${REGION}-docker.pkg.dev"
IMG_BASE="${REG_HOST}/${PROJECT}/${REPO_ID}/${IMAGE_NAME}"
SHA="$(git rev-parse --short HEAD 2>/dev/null || date -u +%Y%m%d%H%M%S)"
IMG_TAG_SHA="${IMG_BASE}:${SHA}"
IMG_TAG_LATEST="${IMG_BASE}:latest"

echo "[LOG] Building image with Cloud Build: ${IMG_TAG_SHA}"
gcloud builds submit --tag "${IMG_TAG_SHA}" --project "${PROJECT}" --quiet
gcloud container images add-tag "${IMG_TAG_SHA}" "${IMG_TAG_LATEST}" --quiet || true

echo "[LOG] Updating Cloud Run service ${SERVICE} in ${REGION}"
gcloud run services update "${SERVICE}" \
  --platform=managed \
  --region="${REGION}" \
  --project="${PROJECT}" \
  --image="${IMG_TAG_SHA}" \
  --quiet

echo "[PASS] Deploy completed. Service now uses ${IMG_TAG_SHA}"
