#!/bin/bash
# Verify Agent Data session readiness using the shared server-side gate.

set -euo pipefail

BASE_URL="${AGENT_DATA_URL:-https://vps.incomexsaigoncorp.vn/api}"
API_KEY="${AGENT_DATA_API_KEY:-${API_KEY:-${AGENT_DATA_API_KEY_LOCAL:-}}}"
AGENT_NAME="${AGENT_NAME:-codex}"
TRANSPORT="${AGENT_TRANSPORT:-cli-selftest}"
SESSION_ID="${SESSION_ID:-session-ready-$(date +%s)}"
SENTINEL_QUERY="${SENTINEL_QUERY:-agent data access confirmation}"

if [ -z "${API_KEY}" ] && [ -f /opt/incomex/docker/.env ]; then
    API_KEY=$(grep -m1 '^API_KEY=' /opt/incomex/docker/.env | cut -d= -f2 || true)
fi

if [ -z "${API_KEY}" ]; then
    echo "STATUS=NOT_READY"
    echo "failure_stage=auth"
    echo "classification=backend_down"
    echo "error=AGENT_DATA_API_KEY is not set"
    exit 2
fi

HEALTH_TMP=$(mktemp)
READY_TMP=$(mktemp)
CHAT_TMP=$(mktemp)
trap 'rm -f "$HEALTH_TMP" "$READY_TMP" "$CHAT_TMP"' EXIT

HEALTH_HTTP=$(curl -s -o "$HEALTH_TMP" -w "%{http_code}" --max-time 15 \
    -H "X-API-Key: $API_KEY" \
    "$BASE_URL/health" 2>/dev/null || echo "000")

READY_PAYLOAD=$(SESSION_ID="$SESSION_ID" AGENT_NAME="$AGENT_NAME" TRANSPORT="$TRANSPORT" python3 - <<'PY'
import json
import os

print(json.dumps({
    "session_id": os.environ["SESSION_ID"],
    "agent": os.environ["AGENT_NAME"],
    "transport": os.environ["TRANSPORT"],
}))
PY
)

READY_HTTP=$(curl -s -o "$READY_TMP" -w "%{http_code}" --max-time 30 \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -X POST "$BASE_URL/session-ready" \
    -d "$READY_PAYLOAD" 2>/dev/null || echo "000")

CHAT_PAYLOAD=$(SESSION_ID="$SESSION_ID" SENTINEL_QUERY="$SENTINEL_QUERY" python3 - <<'PY'
import json
import os

print(json.dumps({
    "message": os.environ["SENTINEL_QUERY"],
    "session_id": os.environ["SESSION_ID"],
}))
PY
)

CHAT_HTTP=$(curl -s -o "$CHAT_TMP" -w "%{http_code}" --max-time 30 \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -X POST "$BASE_URL/chat" \
    -d "$CHAT_PAYLOAD" 2>/dev/null || echo "000")

STATUS=$(python3 - "$READY_TMP" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("NOT_READY")
    raise SystemExit(0)

print(data.get("status", "NOT_READY"))
PY
)

FAILURE_STAGE=$(python3 - "$READY_TMP" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("response_parse")
    raise SystemExit(0)

print(data.get("failure_stage") or "none")
PY
)

CLASSIFICATION=$(python3 - "$READY_TMP" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("backend_down")
    raise SystemExit(0)

print(data.get("classification") or "none")
PY
)

SENTINEL_HITS=$(python3 - "$READY_TMP" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("0")
    raise SystemExit(0)

print(data.get("sentinel_hits", 0))
PY
)

ROUTE_CONTEXT=$(python3 - "$CHAT_TMP" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("0")
    raise SystemExit(0)

print(len(data.get("context", [])))
PY
)

ERROR_MSG=$(python3 - "$READY_TMP" <<'PY'
import json
import sys

try:
    data = json.load(open(sys.argv[1]))
except Exception:
    print("Unable to parse session-ready response")
    raise SystemExit(0)

print((data.get("error") or "").replace("\n", " ").strip())
PY
)

echo "STATUS=$STATUS"
echo "failure_stage=$FAILURE_STAGE"
echo "classification=$CLASSIFICATION"
echo "health_http=$HEALTH_HTTP"
echo "session_ready_http=$READY_HTTP"
echo "chat_http=$CHAT_HTTP"
echo "sentinel_hits=$SENTINEL_HITS"
echo "route_context=$ROUTE_CONTEXT"
echo "session_id=$SESSION_ID"
if [ -n "$ERROR_MSG" ]; then
    echo "error=$ERROR_MSG"
fi

if [ "$STATUS" = "PASS" ] && [ "$READY_HTTP" = "200" ] && [ "$CHAT_HTTP" = "200" ]; then
    exit 0
fi

exit 1
