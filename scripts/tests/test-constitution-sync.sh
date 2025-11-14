#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

echo "🧪 Running constitution sync tests..."

# Test 1: Script can start without crashing
echo "Testing script startup..."
output=$(timeout 5s bash scripts/sync-constitution.sh --dry-run 2>&1 || true)
if ! echo "$output" | grep -q "Starting Constitution Sync"; then
    echo "❌ Script failed to start"
    echo "Output: $output"
    exit 1
fi
echo "✅ Script starts successfully"

# Test 2: Dry run produces output
echo "Testing dry-run output..."
output=$(timeout 10s bash scripts/sync-constitution.sh --dry-run --allow-missing 2>&1 || true)
if ! echo "$output" | grep -q "DRY RUN MODE"; then
    echo "❌ Dry-run failed to produce expected output"
    echo "Output: $output"
    exit 1
fi
echo "✅ Dry-run produces expected output"

# Test 3: Check mode works on synced files
echo "Testing check mode on synced files..."
if ! timeout 10s bash scripts/sync-constitution.sh --check >/dev/null 2>&1; then
    echo "❌ Check mode failed on synced files"
    exit 1
fi
echo "✅ Check mode works on synced files"

echo "🎉 All tests passed!"
