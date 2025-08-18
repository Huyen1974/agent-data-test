#!/usr/bin/env bash
set -euo pipefail

# Project root
PROJ="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
DSTDIR="$PROJ/.cursor/law_files"
DEST="$DSTDIR/ALL_LAWs.md"

# 0) Guard against a stuck shell prompt
export RPROMPT="" || true
stty sane || true

# 1) Ensure directory exists
mkdir -p "$DSTDIR"

# 2) Create file only if missing
if [ ! -e "$DEST" ]; then
  # Minimal, safe placeholder — user will edit manually later
  {
    echo "# ALL_LAWs (Consolidated)"
    echo ""
    echo "<!-- Placeholder created for Cursor. The owner will edit this file manually. -->"
  } > "$DEST"
fi

# 3) Report status
echo "✓ law_files folder: $DSTDIR"
ls -l "$DSTDIR" || true

# 4) If the file exists but doesn't appear in the sidebar, print it so Cursor can read it now
if [ -f "$DEST" ]; then
  echo ""
  echo "=== BEGIN ALL_LAWs.md (for Cursor to read if UI doesn't show it) ==="
  sed -n '1,200p' "$DEST"
  echo "=== END ALL_LAWs.md ==="
else
  echo "✗ Could not find $DEST after creation attempt."
  exit 1
fi

# 5) (Optional) Try to open in Cursor app (safe to ignore if unsupported)
open -a "Cursor" "$DEST" 2>/dev/null || true
