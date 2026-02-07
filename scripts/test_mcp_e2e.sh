#!/usr/bin/env bash
# MCP End-to-End Test Script for Agent Data
# Tests MCP tools via JSON-RPC POST /mcp endpoint
#
# Usage:
#   ./scripts/test_mcp_e2e.sh                        # local, quick
#   ./scripts/test_mcp_e2e.sh --target=local --quick  # same
#   ./scripts/test_mcp_e2e.sh --target=cloud --full   # cloud, full
#   ./scripts/test_mcp_e2e.sh --full                  # local, full

set -uo pipefail

# --- Argument parsing ---
TARGET="local"
MODE="quick"
for arg in "$@"; do
    case "$arg" in
        --target=local|local)   TARGET="local" ;;
        --target=cloud|cloud)   TARGET="cloud" ;;
        --quick)                MODE="quick" ;;
        --full)                 MODE="full" ;;
        -h|--help)
            echo "Usage: $0 [--target=local|cloud] [--quick|--full]"
            echo "  --target=local  Test against http://localhost:8000 (default)"
            echo "  --target=cloud  Test against Cloud Run"
            echo "  --quick         Core tests only: health, list, get, search (default)"
            echo "  --full          Full CRUD + vector sync tests"
            exit 0
            ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

PASS=0
FAIL=0
TOTAL=0

if [ "$TARGET" = "cloud" ]; then
    BASE_URL="https://agent-data-test-pfne2mqwja-as.a.run.app"
    API_KEY=$(gcloud secrets versions access latest --secret=agent-data-api-key --project=github-chatgpt-ggcloud 2>/dev/null || echo "")
    if [ -z "$API_KEY" ]; then
        echo "ERROR: Could not retrieve API key from Secret Manager"
        exit 1
    fi
else
    BASE_URL="http://localhost:8000"
    API_KEY="${API_KEY:-test-key-local}"
fi

echo "=== MCP E2E TEST (target=$TARGET, mode=$MODE) ==="
echo "URL: $BASE_URL"
echo ""

# --- Helper: JSON-RPC call ---
mcp_call() {
    local desc="$1"
    local method="$2"
    local params="$3"
    local check="$4"

    TOTAL=$((TOTAL + 1))
    printf "%d. %-40s " "$TOTAL" "$desc..."

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

# --- Helper: REST call ---
rest_call() {
    local desc="$1"
    local method="$2"
    local path="$3"
    local data="$4"
    local check="$5"

    TOTAL=$((TOTAL + 1))
    printf "%d. %-40s " "$TOTAL" "$desc..."

    local response
    if [ "$method" = "GET" ]; then
        response=$(curl -s "$BASE_URL$path" -H "X-API-Key: $API_KEY" 2>/dev/null)
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -X DELETE "$BASE_URL$path" -H "X-API-Key: $API_KEY" 2>/dev/null)
    else
        response=$(curl -s -X "$method" "$BASE_URL$path" \
            -H "Content-Type: application/json" \
            -H "X-API-Key: $API_KEY" \
            -d "$data" 2>/dev/null)
    fi

    if echo "$response" | python3 -c "$check" 2>/dev/null; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL"
        echo "   Response: $(echo "$response" | head -c 200)"
        FAIL=$((FAIL + 1))
    fi
}

# ============================
# QUICK TESTS (always run)
# ============================
echo "--- Core Tests ---"

# 1. Health check
rest_call "health" "GET" "/health" "" \
    "import sys,json; r=json.load(sys.stdin); assert r['status'] in ('healthy','degraded')"

# 2. MCP initialize
mcp_call "initialize" "initialize" "{}" \
    "import sys,json; r=json.load(sys.stdin); assert r['result']['protocolVersion']"

# 3. tools/list
mcp_call "tools/list" "tools/list" "{}" \
    "import sys,json; r=json.load(sys.stdin); assert len(r['result']['tools']) == 8"

# 4. list_documents
mcp_call "list_documents" "tools/call" \
    '{"name":"list_documents","arguments":{"path":"docs"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'items' in t"

# 5. get_document
mcp_call "get_document" "tools/call" \
    '{"name":"get_document","arguments":{"document_id":"docs/context-packs/governance.md"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert len(t) > 50"

# 6. search_knowledge
mcp_call "search_knowledge" "tools/call" \
    '{"name":"search_knowledge","arguments":{"query":"governance hybrid principle"}}' \
    "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert len(t) > 20"

# 7. Auth rejection
TOTAL=$((TOTAL + 1))
printf "%d. %-40s " "$TOTAL" "auth rejection..."
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

# ============================
# FULL TESTS (--full only)
# ============================
if [ "$MODE" = "full" ]; then
    echo ""
    echo "--- CRUD Tests ---"

    # 8. Upload document
    mcp_call "upload_document" "tools/call" \
        '{"name":"upload_document","arguments":{"path":"docs/test/e2e-51a","content":"# E2E Test 51A\nUNIQUE-SYNC-TOKEN-XYZ789","title":"E2E Test"}}' \
        "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'created' in t.lower()"

    # 9. Update document
    mcp_call "update_document" "tools/call" \
        '{"name":"update_document","arguments":{"path":"docs/test/e2e-51a","content":"# E2E Updated\nNEW-CONTENT-UPDATED-ABC456"}}' \
        "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'updated' in t.lower()"

    # 10. Delete document
    mcp_call "delete_document" "tools/call" \
        '{"name":"delete_document","arguments":{"path":"docs/test/e2e-51a"}}' \
        "import sys,json; r=json.load(sys.stdin); t=r['result']['content'][0]['text']; assert 'deleted' in t.lower()"

    echo ""
    echo "--- Vector Sync Tests ---"

    # 11. Upload for vector sync test
    rest_call "create sync-test doc" "POST" "/documents" \
        '{"document_id":"docs/test/vector-sync-e2e","parent_id":"docs/test","content":{"mime_type":"text/markdown","body":"VECTOR-SYNC-UNIQUE-TOKEN-E2E-51A"},"metadata":{"title":"Vector Sync Test"}}' \
        "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='created'"

    # 12. Search should find it
    sleep 1
    rest_call "search finds new doc" "POST" "/chat" \
        '{"message":"VECTOR-SYNC-UNIQUE-TOKEN-E2E-51A"}' \
        "import sys,json; r=json.load(sys.stdin); ctx=r.get('context',[]); assert any('vector-sync-e2e' in c.get('document_id','') for c in ctx), f'Not found in context: {ctx}'"

    # 13. Update content
    rest_call "update sync-test doc" "PUT" "/documents/docs/test/vector-sync-e2e" \
        '{"document_id":"docs/test/vector-sync-e2e","patch":{"content":{"mime_type":"text/markdown","body":"REPLACED-CONTENT-NEW-VERSION-E2E"}},"update_mask":["content"]}' \
        "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='updated'"

    # 14. Search finds NEW content
    sleep 1
    rest_call "search finds new content" "POST" "/chat" \
        '{"message":"REPLACED-CONTENT-NEW-VERSION-E2E"}' \
        "import sys,json; r=json.load(sys.stdin); ctx=r.get('context',[]); assert any('vector-sync-e2e' in c.get('document_id','') for c in ctx), f'Not found: {ctx}'"

    # 15. Delete document
    rest_call "delete sync-test doc" "DELETE" "/documents/docs/test/vector-sync-e2e" "" \
        "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='deleted'"

    # 16. Search should NOT find deleted doc
    sleep 1
    rest_call "search excludes deleted doc" "POST" "/chat" \
        '{"message":"VECTOR-SYNC-UNIQUE-TOKEN-E2E-51A"}' \
        "import sys,json; r=json.load(sys.stdin); ctx=r.get('context',[]); assert not any('vector-sync-e2e' in c.get('document_id','') for c in ctx), f'Still found: {ctx}'"

    echo ""
    echo "--- Move Test ---"

    # 17. Create doc for move test
    rest_call "create move-test doc" "POST" "/documents" \
        '{"document_id":"docs/test/move-src","parent_id":"docs/test","content":{"mime_type":"text/markdown","body":"MOVE-TEST-CONTENT-51A"},"metadata":{"title":"Move Test"}}' \
        "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='created'"

    # 18. Move to new parent (auto-create parent)
    rest_call "move document" "POST" "/documents/docs/test/move-src/move" \
        '{"new_parent_id":"docs/test/archive"}' \
        "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='moved'"

    # 19. Cleanup move test
    rest_call "delete moved doc" "DELETE" "/documents/docs/test/move-src" "" \
        "import sys,json; r=json.load(sys.stdin); assert r.get('status')=='deleted'"

    echo ""
    echo "--- Orphan Cleanup Test ---"

    # 20. Cleanup orphans (may return 503 if Qdrant unavailable)
    rest_call "cleanup-orphans" "POST" "/kb/cleanup-orphans" "{}" \
        "import sys,json; r=json.load(sys.stdin); assert ('removed' in r and 'remaining' in r) or 'detail' in r"
fi

# ============================
# SUMMARY
# ============================
echo ""
echo "=== RESULTS: $PASS/$TOTAL PASS, $FAIL FAIL ==="
if [ "$FAIL" -eq 0 ]; then
    echo "ALL TESTS PASSED"
else
    echo "SOME TESTS FAILED"
fi
exit "$FAIL"
