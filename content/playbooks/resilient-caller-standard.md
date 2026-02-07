# Resilient Caller Standard

## Purpose
Every external service call in the system MUST use resilient patterns to handle
transient failures (cold starts, timeouts, temporary outages) without crashing.

## Requirements

### 1. Retry with Exponential Backoff
- All external calls MUST retry on transient errors
- Standard config: 3 retries, exponential backoff 1s -> 2s -> 4s
- Retryable errors: timeout, 503, 504, 429, ConnectionError
- Library: `tenacity` (already installed)

### 2. Async Only
- All HTTP calls MUST use `httpx` (async), NOT `requests` (blocking)
- SDK calls (Qdrant, OpenAI) use sync clients with `@sync_retry` decorator
- Goal: 1 container handles 80-100 concurrent requests without blocking

### 3. Phonebook Pattern (No Hardcoded URLs)
- Code NEVER hardcodes service URLs
- Services auto-discovered from `SERVICE_{NAME}_URL` env vars
- Adding a new service = adding 1 env var, no code change
- Backward compatible with legacy vars (QDRANT_URL, OPENAI_API_URL)

Convention:
```
SERVICE_QDRANT_URL=https://xxx.qdrant.io
SERVICE_OPENAI_URL=https://api.openai.com/v1
SERVICE_DIRECTUS_URL=https://directus-xxx.a.run.app   # future
SERVICE_QDRANT_TIMEOUT=60                              # optional override
SERVICE_QDRANT_RETRIES=5                               # optional override
```

### 4. Health Endpoint
- Every Cloud Run service MUST expose `GET /health`
- Response MUST include per-service status detail
- Status: "healthy" (all OK), "degraded" (some services down, container running)
- Health checks cached for 30s to avoid excessive probing

### 5. Startup Probe
- Every Cloud Run service MUST configure a startup probe
- Path: `/health`
- Period: 5s, failure threshold: 12 (allows 60s warmup)
- Prevents traffic to unready containers (eliminates cold start errors)

### 6. Graceful Degradation
- Container MUST NOT crash if an external service is down
- Endpoints not requiring the down service continue working
- Endpoints requiring the down service return clear error messages
- /health reports "degraded" status with specific service failure details

## Implementation Reference
- Server module: `agent_data/resilient_client.py`
- Vector store retry: `agent_data/vector_store.py` (@sync_retry decorators)
- Client utility: `scripts/utils/resilient_fetch.py`
- Health endpoint: `agent_data/server.py` (GET /health)

## Nuxt/Frontend Retry
- `ofetch` (Nuxt built-in `$fetch`) has native `retry` option
- Default: 1 retry for GET/HEAD, 0 for mutation methods
- Configure: `$fetch('/api/data', { retry: 3 })` for custom retry count
- No additional library needed for frontend calls
