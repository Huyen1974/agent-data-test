# Context Pack: Infrastructure

> Load this pack for any GCP, deployment, or infrastructure task.

## Purpose
Complete reference for all GCP services, endpoints, and infrastructure patterns.

## Prerequisites
- Context Pack: Governance (for SA rules and hybrid principle)
- gcloud CLI authenticated

## GCP Project
| Key | Value |
|-----|-------|
| Project ID | `github-chatgpt-ggcloud` |
| Default Region | `asia-southeast1` |
| Service Account | `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com` |

**CRITICAL**: Only ONE Service Account. Never create new ones (GC-LAW 1.3).

## Services Inventory

### Cloud Run: agent-data-test
| Property | Value |
|----------|-------|
| URL | `https://agent-data-test-pfne2mqwja-as.a.run.app` |
| Region | asia-southeast1 |
| Memory | 512Mi |
| Auth | IAM (requires identity token) |
| Port | 8080 (internal), mapped by Cloud Run |
| Image | Built from Dockerfile in repo root |
| SA | chatgpt-deployer@... |

**Deploy command:**
```bash
gcloud run deploy agent-data-test \
  --source . \
  --region asia-southeast1 \
  --service-account chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com \
  --allow-unauthenticated=no \
  --memory 512Mi \
  --timeout 300
```

### Qdrant Vector Database
| Property | Value |
|----------|-------|
| Cluster ID | `529a17a6-01b8-4304-bc5c-b936aec8fca9` |
| Endpoint | `https://529a17a6-...us-east4-0.gcp.cloud.qdrant.io` |
| Region | us-east4 (GCP) |
| Account ID | `b7093834-20e9-4206-8ea0-025b6994b319` |
| Auth | API key (from Secret Manager: `qdrant_api`) |

### Secret Manager
| Secret Name | Purpose |
|-------------|---------|
| `agent-data-api-key` | API key for write operations |
| `qdrant_api` | Qdrant client authentication |
| `Qdrant_cloud_management_key` | Qdrant cloud management API |

### GCS Buckets
| Bucket | Purpose |
|--------|---------|
| `huyen1974_agent_data_artifacts_test` | Container images |
| `huyen1974_agent_data_knowledge_test` | Knowledge documents |
| `huyen1974_agent_data_logs_test` | App logs |
| `huyen1974_agent_data_qdrant_snapshots_test` | Qdrant backups |
| `huyen1974_agent_data_source_test` | Source documents |
| `huyen1974_agent_data_tfstate_test` | Terraform state |

### Cloud Scheduler
| Job | Schedule | Purpose |
|-----|----------|---------|
| ping-qdrant | */10 * * * * | Keep Qdrant cluster warm |

### Cloud Functions
- `timer_callback` — Called by Cloud Scheduler to ping Qdrant

## Local Development

### Starting Services
```bash
# Quick start (uses dot tools)
dot/bin/dot-ai-start

# Manual start
cd ~/Documents/Manual\ Deploy/agent-data-test
source venv/bin/activate
uvicorn agent_data.server:app --host 0.0.0.0 --port 8000
```

### Local Ports
| Port | Service |
|------|---------|
| 8000 | Agent Data API |
| 8001 | MCP HTTP Server |
| 8055 | Directus (Docker) |

### Environment Files
- `.env.local` — Local dev environment variables
- `.env.example` — Template with all required vars

## Hybrid Configuration
```
Local URL:  http://localhost:8000    (priority)
Cloud URL:  https://agent-data-test-pfne2mqwja-as.a.run.app  (fallback)
```
Both must ALWAYS be configured. See Governance pack for rules.

## DOT Tools
| Command | Purpose |
|---------|---------|
| `dot-ai-start` | Start all local services |
| `dot-ai-stop` | Stop all local services |
| `dot-ai-test-all` | Run connection tests |

## Deployment Checklist
1. Verify local tests pass: `dot-ai-test-all`
2. Deploy: `gcloud run deploy ...` (see command above)
3. Verify cloud: `curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" https://agent-data-test-pfne2mqwja-as.a.run.app/health`
4. Test CRUD on cloud endpoint
5. Update rollback playbook if needed

## Related Documents
- `docs/playbooks/infrastructure-change.md` — Change procedure
- `docs/status/system-inventory.md` — Current system state
- `docs/rollback_playbook.md` — Cloud Run rollback procedure
