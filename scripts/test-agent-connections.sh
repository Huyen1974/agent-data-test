#!/bin/bash
# =============================================================================
# test-agent-connections.sh — Agent-level connection test suite
# Tests every connection path each AI agent uses in production.
# =============================================================================
# Usage: ./test-agent-connections.sh
# Deploy: /opt/incomex/scripts/test-agent-connections.sh
# =============================================================================

set -euo pipefail

# --- Config ---
AGENT_DATA_URL="${AGENT_DATA_URL:-http://172.18.0.5:8000}"
DIRECTUS_URL="${DIRECTUS_URL:-http://172.18.0.6:8055}"
OPS_URL="https://ops.incomexsaigoncorp.vn"

# Load keys from docker env
if [ -f /opt/incomex/docker/.env ]; then
    OPS_KEY=$(grep -m1 '^OPS_API_KEY=' /opt/incomex/docker/.env | cut -d= -f2 || echo "")
    AGENT_DATA_KEY=$(grep -m1 '^API_KEY=' /opt/incomex/docker/.env | cut -d= -f2 || echo "")
    DIRECTUS_TOKEN=$(grep -m1 '^AI_AGENT_TOKEN=' /opt/incomex/docker/.env | cut -d= -f2 || echo "")
fi

# Fallbacks
OPS_KEY="${OPS_KEY:-C38FE9FA-2BC6-4FBB-BA0C-981E8FB89450}"
AGENT_DATA_KEY="${AGENT_DATA_KEY:-$OPS_KEY}"

PASS=0
FAIL=0
TOTAL=0
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

pass() { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); printf "  ✅ %-50s %s\n" "$1" "$2"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); printf "  ❌ %-50s %s\n" "$1" "$2"; }

echo "============================================"
echo "AGENT CONNECTION TEST SUITE"
echo "Timestamp: $TS"
echo "============================================"
echo ""

# ===================================================================
# SECTION 1: AGENT DATA REST API (used by Claude Code, Codex, GPT)
# ===================================================================
echo "=== AGENT DATA REST API ==="

# 1.1: Health
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -H "X-API-Key: $AGENT_DATA_KEY" "$AGENT_DATA_URL/health")
[ "$HTTP" = "200" ] && pass "Health check" "HTTP $HTTP" || fail "Health check" "HTTP $HTTP"

# 1.2: Search (POST /chat)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
    -H "X-API-Key: $AGENT_DATA_KEY" -H "Content-Type: application/json" \
    -X POST "$AGENT_DATA_URL/chat" -d '{"message":"test connectivity"}')
[ "$HTTP" = "200" ] && pass "POST /chat (search_knowledge)" "HTTP $HTTP" || fail "POST /chat (search_knowledge)" "HTTP $HTTP"

# 1.3: List documents (GET /kb/list)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
    -H "X-API-Key: $AGENT_DATA_KEY" "$AGENT_DATA_URL/kb/list?prefix=knowledge/dev")
[ "$HTTP" = "200" ] && pass "GET /kb/list (list_documents)" "HTTP $HTTP" || fail "GET /kb/list (list_documents)" "HTTP $HTTP"

# 1.4: Get document (GET /documents/{id})
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -H "X-API-Key: $AGENT_DATA_KEY" "$AGENT_DATA_URL/documents/knowledge/dev/ssot/operating-rules.md")
[ "$HTTP" = "200" ] && pass "GET /documents/{id} (get_document)" "HTTP $HTTP" || fail "GET /documents/{id} (get_document)" "HTTP $HTTP"

# 1.5: MCP endpoint (POST /mcp — tool list)
BODY=$(curl -s --max-time 10 \
    -H "X-API-Key: $AGENT_DATA_KEY" -H "Content-Type: application/json" \
    -X POST "$AGENT_DATA_URL/mcp" \
    -d '{"jsonrpc":"2.0","method":"tools/list","id":1}')
TOOL_COUNT=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('result',{}).get('tools',[])))" 2>/dev/null || echo "0")
[ "$TOOL_COUNT" -ge 10 ] && pass "POST /mcp (MCP tool list)" "$TOOL_COUNT tools" || fail "POST /mcp (MCP tool list)" "$TOOL_COUNT tools"

# 1.6: Document CRUD (create → verify → delete)
CREATE_RESP=$(curl -s --max-time 10 \
    -H "X-API-Key: $AGENT_DATA_KEY" -H "Content-Type: application/json" \
    -X POST "$AGENT_DATA_URL/documents" \
    -d "{\"document_id\":\"test/agent-conn-test\",\"parent_id\":\"test\",\"content\":{\"mime_type\":\"text/markdown\",\"body\":\"# Test $TS\"},\"metadata\":{\"title\":\"Connection test\"}}")
CREATE_STATUS=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "error")
if [ "$CREATE_STATUS" = "created" ]; then
    pass "Document CRUD — create" "OK"
    # Delete cleanup
    DEL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -H "X-API-Key: $AGENT_DATA_KEY" -X DELETE "$AGENT_DATA_URL/documents/test/agent-conn-test")
    [ "$DEL_HTTP" = "200" ] && pass "Document CRUD — delete (cleanup)" "HTTP $DEL_HTTP" || fail "Document CRUD — delete (cleanup)" "HTTP $DEL_HTTP"
else
    fail "Document CRUD — create" "$CREATE_STATUS"
    TOTAL=$((TOTAL+1))  # Count the skipped delete
fi

echo ""

# ===================================================================
# SECTION 2: DIRECTUS API (direct, for server-side checks)
# ===================================================================
echo "=== DIRECTUS API (direct) ==="

# 2.1: Health
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$DIRECTUS_URL/server/health")
[ "$HTTP" = "200" ] && pass "Health check" "HTTP $HTTP" || fail "Health check" "HTTP $HTTP"

# 2.2: Get items (tasks)
if [ -n "$DIRECTUS_TOKEN" ]; then
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -H "Authorization: Bearer $DIRECTUS_TOKEN" "$DIRECTUS_URL/items/tasks?limit=1")
    [ "$HTTP" = "200" ] && pass "GET /items/tasks" "HTTP $HTTP" || fail "GET /items/tasks" "HTTP $HTTP"
else
    # Try without token (may fail, that's OK)
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$DIRECTUS_URL/items/tasks?limit=1")
    [ "$HTTP" = "200" ] && pass "GET /items/tasks (no token)" "HTTP $HTTP" || fail "GET /items/tasks (no token)" "HTTP $HTTP — needs AI_AGENT_TOKEN"
fi

echo ""

# ===================================================================
# SECTION 3: OPS PROXY — 23 collections
# ===================================================================
echo "=== OPS PROXY (23 collections) ==="

OPS_PASS=0
OPS_FAIL=0
for coll in tasks task_comments ai_tasks posts pages page_blocks help_articles help_collections navigation navigation_items navigation_navigation_items globals contacts organizations organizations_contacts organization_addresses feedbacks content_requests categories ai_discussions ai_discussion_comments knowledge_documents agent_views; do
    HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -H "X-API-Key: $OPS_KEY" "$OPS_URL/items/${coll}?limit=1")
    if [ "$HTTP" = "200" ]; then
        OPS_PASS=$((OPS_PASS+1))
        PASS=$((PASS+1))
    else
        OPS_FAIL=$((OPS_FAIL+1))
        FAIL=$((FAIL+1))
        printf "  ❌ %-40s HTTP %s\n" "$coll" "$HTTP"
    fi
    TOTAL=$((TOTAL+1))
done
echo "  OPS Proxy GET: $OPS_PASS/23 PASS"

# 3.1: RO collection POST (should block)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
    -H "X-API-Key: $OPS_KEY" -H "Content-Type: application/json" \
    -X POST "$OPS_URL/items/knowledge_documents" -d '{"test":1}')
[ "$HTTP" != "200" ] && pass "RO collection POST blocked" "HTTP $HTTP" || fail "RO collection POST NOT blocked" "HTTP $HTTP"

# 3.2: CRUD test (create comment → delete)
CID=$(curl -s --max-time 10 \
    -H "X-API-Key: $OPS_KEY" -H "Content-Type: application/json" \
    -X POST "$OPS_URL/items/task_comments" \
    -d "{\"task_id\":7,\"content\":\"[test-agent-connections] $TS\",\"action\":\"comment\",\"tab_scope\":\"general\",\"agent_type\":\"script\"}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('id',''))" 2>/dev/null)
if [ -n "$CID" ] && [ "$CID" != "" ]; then
    pass "OPS Proxy CRUD — create comment" "#$CID"
    DEL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -H "X-API-Key: $OPS_KEY" -X DELETE "$OPS_URL/items/task_comments/$CID")
    [ "$DEL_HTTP" = "204" ] && pass "OPS Proxy CRUD — delete (cleanup)" "HTTP $DEL_HTTP" || fail "OPS Proxy CRUD — delete" "HTTP $DEL_HTTP"
else
    fail "OPS Proxy CRUD — create comment" "No ID returned"
    TOTAL=$((TOTAL+1))  # Count skipped delete
fi

# 3.3: Auth check (no key should fail)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$OPS_URL/items/tasks?limit=1")
[ "$HTTP" = "403" ] && pass "Auth check (no key → 403)" "HTTP $HTTP" || fail "Auth check (no key → 403)" "HTTP $HTTP"

# 3.4: Blocked path (should 404)
HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    -H "X-API-Key: $OPS_KEY" "$OPS_URL/items/directus_users?limit=1")
[ "$HTTP" = "404" ] && pass "Blocked collection → 404" "HTTP $HTTP" || fail "Blocked collection → 404" "HTTP $HTTP"

echo ""

# ===================================================================
# SUMMARY
# ===================================================================
echo "============================================"
echo "SUMMARY: $PASS/$TOTAL PASS ($FAIL failed)"
echo "============================================"

if [ $FAIL -eq 0 ]; then
    echo "ALL TESTS PASSED ✅"
    exit 0
else
    echo "SOME TESTS FAILED ❌"
    exit 1
fi
