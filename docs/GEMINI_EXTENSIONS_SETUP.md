# Gemini Extensions Setup Guide

## Overview

This guide explains how to connect Google Gemini (AI Studio or Vertex AI) to the Agent Data Knowledge Manager API.

## Option A: Google AI Studio Gems (Recommended)

### Step 1: Access AI Studio
1. Go to [https://aistudio.google.com](https://aistudio.google.com)
2. Sign in with your Google account
3. Click **"Gems"** in the sidebar (or "Create" if prompted)

### Step 2: Create a New Gem
1. Click **"Create Gem"**
2. Configure basic settings:
   - **Name**: "Agent Data Assistant"
   - **Description**: "Knowledge search assistant connected to Agent Data RAG API"

### Step 3: Add Custom Action
1. In the Gem editor, click **"Advanced"** or **"Tools"**
2. Click **"Add Action"** or **"External Tools"**
3. Select **"Import OpenAPI"**
4. Enter the spec URL:
   ```
   https://vps.incomexsaigoncorp.vn/api/openapi.json
   ```

### Step 4: Configure Authentication
1. After importing, click on the action settings
2. Configure authentication:
   - **Type**: API Key
   - **Header Name**: `X-API-Key`
   - **Value**: (Get from Secret Manager)

### Step 5: Test the Gem
Ask questions like:
- "Search for Terraform IaC principles"
- "List all available documents"
- "Get the content of the constitution document"

---

## Option B: Vertex AI Extensions (Enterprise)

For enterprise deployment using Vertex AI:

### Step 1: Create Extension
1. Go to [Vertex AI Console](https://console.cloud.google.com/vertex-ai)
2. Navigate to **"Extensions"** → **"Create Extension"**

### Step 2: Configure Extension
```yaml
name: agent-data-extension
display_name: Agent Data Knowledge Manager
description: RAG-based knowledge search

manifest:
  name: agent_data
  description: Search and retrieve knowledge documents
  api_spec:
    open_api_uri: https://vps.incomexsaigoncorp.vn/api/openapi.json
  auth_config:
    api_key_config:
      name: X-API-Key
      secret_version: projects/PROJECT_ID/secrets/agent-data-api-key/versions/latest
```

### Step 3: Deploy Extension
```bash
gcloud ai extensions create agent-data-extension \
  --region=asia-southeast1 \
  --manifest-file=extension-manifest.yaml
```

### Step 4: Use in Gemini Chat
```python
from vertexai.preview import extensions

ext = extensions.Extension("projects/PROJECT/locations/REGION/extensions/agent-data-extension")

response = ext.execute(
    operation_id="searchKnowledge",
    operation_params={"query": "Terraform IaC principles"}
)
print(response)
```

---

## Available Actions

| Action | Description | Method | Endpoint |
|--------|-------------|--------|----------|
| `searchKnowledge` | RAG search | POST | /chat |
| `healthCheck` | Health check | GET | /health |
| `getSystemInfo` | System info | GET | /info |
| `listDocuments` | List docs tree | GET | /api/docs/tree |
| `getDocument` | Get document | GET | /api/docs/file |

---

## Troubleshooting

### "Extension import failed"
- Ensure OpenAPI spec is valid YAML
- Check all required fields are present
- Verify the spec URL is publicly accessible

### "Authentication error"
- Verify API key is correct
- Check Secret Manager permissions
- Ensure the key hasn't been rotated

### "Rate limited"
- Gemini has rate limits on external calls
- Wait 60 seconds between requests
- Consider implementing request queuing

### "CORS error" (for browser-based testing)
- Use server-side calls instead
- Or configure CORS on the Agent Data API

---

## API Endpoints

| Environment | URL |
|-------------|-----|
| Production | `https://agent-data-test-pfne2mqwja-as.a.run.app` |
| Local Dev | `http://localhost:8000` |

---

## Example Usage in AI Studio

### Prompt
```
You are an AI assistant with access to the Agent Data knowledge base.
When users ask questions about infrastructure, policies, or documentation,
use the searchKnowledge tool to find relevant information.

User: What is the HP-02 Terraform principle?
```

### Expected Response
```
Let me search the knowledge base for information about HP-02 Terraform.

[Calls searchKnowledge]

Based on the knowledge base, HP-02 (Terraform IaC) is a core principle that states:
"All resources managed via Terraform with focus on minimalism."

This principle requires that:
- All infrastructure is defined as code
- Terraform is the primary IaC tool
- Minimal resources are provisioned
- Changes go through proper review process

Source: constitution-v1.11e
```

---

## Support

- Documentation: https://ai.google.dev/docs
- Issues: GitHub repository issues
- Contact: ai-platform@example.com
