#!/usr/bin/env bash
# MCP End-to-End Test Script for Agent Data
# Tests all 8 MCP tools via JSON-RPC POST /mcp endpoint
# Usage: ./scripts/test_mcp_e2e.sh [cloud|local]

set -euo pipefail

MODE="${1:-local}"
PASS=0
FAIL=0
TOTAL=0

if [ "$MODE" = "cloud" ]; then
    CLOUD="https://agent-data-test-pfne2mqwja-as.a.run.app"
    API_KEY=$(gcloud secrets versions access latest --secret=agent-data-api-key --project=mpc-rag-langroid 2>/dev/null || echo "")
    if [ -z "$API_KEY" ]; then
        echo "ERROR: Could not retrieve API key from Secret Manager"
        exit 1
    fi
    BASE_URL="$CLOUD"
else
    BASE_URL="http://localhost:8000"
    API_KEY="${API_KEY:-test-key-local}"
fi

echo "=== MCP E2E TEST ($MODE) ==="
echo "URL: $BASE_URL"
echo ""

mcp_call() {
    local desc="$1"
    local method="$2"
    local params="$3"
    local check="$4"

    TOTAL=$((TOTAL + 1))
    printf "%d. %-30s " "$TOTAL" "$desc..."

    local body="{\"jsonrpc\":\"2.0\",\"id\":$TOTAL,\"method\":\"$method\",\"params\":$params}"

    local response
    response=$(curl -s -X POST "$BASE_URL/mcp" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$body" 2>/dev/null)

    if echo "$response" | python3 -c "$check" 2>/dev/null; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL"
        echo "   Response: $(echo "$response" | head -c 200)"
        FAIL=$((FAIL + 1))
    fi
}

# 1. initialize
mcp_call "initialize" "initialize" "{}" \
    "import sys,json; r=json.load(sys.stdin); assert r['result']['protocolVersion']"

# 2. tools/list
mcp_call "tools/list" "tools/list" "{}" \
    "import sys,json; r=json.load(sys.stdin); assert len(r['result']['tools']) == 8"

# 3. search_knowledge
mcp_call "search_knowledge" "tools/call" \
    '{"name":"search_knowledge","arguments":{"query":"governance hybrid principle"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'governance' in t.lower() or 'hybrid' in t.lower()"

# 4. list_documents
mcp_call "list_documents" "tools/call" \
    '{"name":"list_documents","arguments":{"path":"docs/context-packs"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'governance' in t"

# 5. get_document
mcp_call "get_document" "tools/call" \
    '{"name":"get_document","arguments":{"document_id":"docs/context-packs/governance.md"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'Agents First' in t"

# 6. upload_document
mcp_call "upload_document" "tools/call" \
    '{"name":"upload_document","arguments":{"path":"e2e-test-50g","content":"# E2E Test 50G","title":"Test"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'created' in t.lower()"

# 7. update_document
mcp_call "update_document" "tools/call" \
    '{"name":"update_document","arguments":{"path":"e2e-test-50g","content":"# E2E Updated 50G"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'updated' in t.lower()"

# 8. delete_document (cleanup)
mcp_call "delete_document" "tools/call" \
    '{"name":"delete_document","arguments":{"path":"e2e-test-50g"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'deleted' in t.lower()"

# 9. Auth rejection (wrong key)
TOTAL=$((TOTAL + 1))
printf "%d. %-30s " "$TOTAL" "auth rejection..."
auth_resp=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/mcp" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: wrong-key-here" \
    -d '{"jsonrpc":"2.0","id":99,"method":"tools/list","params":{}}')
if [ "$auth_resp" = "401" ]; then
    echo "PASS"
    PASS=$((PASS + 1))
else
    echo "FAIL (expected 401, got $auth_resp)"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=== RESULTS: $PASS/$TOTAL PASS, $FAIL FAIL ==="
[ "$FAIL" -eq 0 ] && echo "ALL TESTS PASSED" || echo "SOME TESTS FAILED"
exit "$FAIL"
