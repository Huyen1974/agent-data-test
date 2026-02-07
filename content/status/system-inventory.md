# Living Status: System Inventory

> Auto-maintained list of ALL services, URLs, versions, and their current state.

**Last Updated**: 2026-02-06

## Cloud Services

| Service | Type | URL | Region | Status |
|---------|------|-----|--------|--------|
| agent-data-test | Cloud Run | https://agent-data-test-pfne2mqwja-as.a.run.app | asia-southeast1 | ACTIVE |
| Qdrant Cloud | Vector DB | https://529a17a6-...us-east4-0.gcp.cloud.qdrant.io | us-east4 | ACTIVE |
| ping-qdrant | Cloud Scheduler | N/A (internal) | asia-southeast1 | ACTIVE (*/10 * * * *) |
| timer_callback | Cloud Function | N/A (triggered) | asia-southeast1 | ACTIVE |

## Local Services

| Service | Port | Start Command | Status |
|---------|------|--------------|--------|
| Agent Data API | 8000 | `uvicorn agent_data.server:app --port 8000` | ON (when dev) |
| MCP HTTP Server | 8001 | `uvicorn mcp_server.server:app --port 8001` | ON (when dev) |
| MCP STDIO | N/A | Via Claude Desktop config | ACTIVE |
| Directus | 8055 | Docker compose | ON (when needed) |

## Storage

| Resource | Type | Purpose |
|----------|------|---------|
| huyen1974_agent_data_artifacts_test | GCS Bucket | Container images |
| huyen1974_agent_data_knowledge_test | GCS Bucket | Knowledge documents |
| huyen1974_agent_data_logs_test | GCS Bucket | Application logs |
| huyen1974_agent_data_qdrant_snapshots_test | GCS Bucket | Qdrant backups |
| huyen1974_agent_data_source_test | GCS Bucket | Source documents |
| huyen1974_agent_data_tfstate_test | GCS Bucket | Terraform state |
| Firestore (default) | Document DB | KB documents, session data |

## Secrets

| Secret Name | Purpose | Last Rotated |
|-------------|---------|-------------|
| agent-data-api-key | API auth for write operations | — |
| qdrant_api | Qdrant client auth | — |
| Qdrant_cloud_management_key | Qdrant management API | — |

## Docker Images

| Image | Registry | Base |
|-------|----------|------|
| agent-data | agent-data-docker-repo (asia-southeast1) | python:3.11-slim-bookworm |

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| langroid | 0.58.0 | Multi-agent framework |
| FastAPI | >=0.104.1 | REST API |
| mcp | 1.12.0 | Model Context Protocol |
| qdrant-client | >=1.15.0 | Vector DB client |
| openai | >=1.97.0 | Embeddings |
| google-cloud-firestore | >=2.13.1 | Document storage |

## Service Account
- **Name**: chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com
- **Usage**: All Cloud Run deploys, GCS operations, GCP API calls
- **Rule**: ONLY SA allowed (GC-LAW 1.3)

## Configuration Files
| File | Location | Purpose |
|------|----------|---------|
| claude_desktop_config.json | ~/Library/Application Support/Claude/ | MCP server config for Claude Desktop |
| .env.local | Project root | Local environment variables |
| openapi.yaml | docs/api/ | OpenAPI 3.1 specification |
| Dockerfile | Project root | Cloud Run build config |
| Dockerfile.mcp | Project root | MCP HTTP server build config |
