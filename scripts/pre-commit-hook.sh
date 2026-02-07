#!/bin/sh
# Pre-commit hook: runs quick MCP E2E tests before allowing commit.
# Install: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
# Skip: git commit --no-verify

# Only run if local server is reachable
if ! curl -s --max-time 2 http://localhost:8000/health > /dev/null 2>&1; then
    echo "⏭ Local server not running — skipping pre-commit test"
    exit 0
fi

echo "🔍 Running quick MCP E2E tests..."
bash scripts/test_mcp_e2e.sh --target=local --quick
result=$?

if [ $result -ne 0 ]; then
    echo ""
    echo "❌ Pre-commit test FAILED — commit blocked."
    echo "   Fix the issues and try again, or use: git commit --no-verify"
    exit 1
fi

echo "✅ Pre-commit tests passed."
exit 0
