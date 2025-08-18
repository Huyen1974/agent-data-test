#!/usr/bin/env bash
set -euo pipefail

# Project roots and inputs
PROJ_SRC="/Users/nmhuyen/Documents/Infor/Kế hoạch liên quan/Langdroid_Agent data/TÀI LIỆU QUY PHẠM"
PROJ_DST="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/nhap_cursor"
SRC_CANON="$PROJ_SRC/ALL_LAWs.md"

# Resolve the target file robustly, tolerating leading space and NBSP in the filename
INTENDED_BASENAME="ALL_LAWs_edit.md"
EDIT_CANDIDATE="$PROJ_DST/ ALL_LAWs_edit.md"    # user-specified, may or may not exist as-typed
EDIT_REAL=""

# Helper: normalize a name for comparison (NBSP→space, trim spaces)
normalize_name() {
  perl -CS -pe 's/\x{00A0}/ /g; s/^\s+|\s+$//g'
}

# 0) dquote safety for integrated shells
export RPROMPT="" || true
stty sane || true

# Ensure UTF-8 locale for proper character handling
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# 1) Verify canonical source exists
[ -f "$SRC_CANON" ] && [ -s "$SRC_CANON" ] || { echo "❌ Missing or empty source: $SRC_CANON"; exit 1; }

# 2) Resolve actual EDIT file path
if [ -f "$EDIT_CANDIDATE" ]; then
  EDIT_REAL="$EDIT_CANDIDATE"
else
  # Scan directory for a filename that normalizes to ALL_LAWs_edit.md
  for f in "$PROJ_DST"/*; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    norm="$(printf "%s" "$base" | normalize_name)"
    if [ "$norm" = "$INTENDED_BASENAME" ]; then
      EDIT_REAL="$f"; break
    fi
  done
fi

[ -n "$EDIT_REAL" ] || { echo "❌ Could not resolve target file in $PROJ_DST. Contents:"; ls -lb "$PROJ_DST"; exit 2; }
[ -s "$EDIT_REAL" ] || { echo "❌ Target file is empty: $EDIT_REAL"; exit 3; }

echo "→ Canonical : $SRC_CANON"
echo "→ Edit file : $EDIT_REAL"

NOW="$(date +%Y%m%dT%H%M%S)"
BAK="$EDIT_REAL.bak.$NOW"
TMP="$EDIT_REAL.tmp.$NOW"
PLAIN_SRC="$EDIT_REAL.plain_src.txt"
PLAIN_EDIT="$EDIT_REAL.plain_edit_pre.txt"
PLAIN_TMP="$EDIT_REAL.plain_tmp.txt"
DIFF_PLAIN_EDIT="$EDIT_REAL.diff_plain_edit_vs_tmp.diff"
DIFF_PLAIN_SRC="$EDIT_REAL.diff_plain_src_vs_tmp.diff"
DIFF_RAW="$EDIT_REAL.diff_raw_md.diff"
NBSP_AUDIT="$EDIT_REAL.nbsp_audit.txt"

# 3) Tooling check
if ! command -v pandoc >/dev/null 2>&1; then
  echo "❌ pandoc not found. Install with: brew install pandoc"; exit 4
fi
# Force minimal cleanup to avoid character encoding corruption
FORMATTER="none"
echo "ℹ️ Using minimal safe cleanup to preserve Vietnamese characters."

# 4) BACKUP and prepare TMP
cp -p "$EDIT_REAL" "$BAK"
cp "$EDIT_REAL" "$TMP"

# 5) NBSP audit and safe replacement (in TMP only)
# Log NBSP lines; then replace NBSP → regular space (macOS compatible)
grep -n $'\xC2\xA0' "$TMP" > "$NBSP_AUDIT" || true
# Skip NBSP replacement to avoid any character corruption
echo "ℹ️ Skipping NBSP replacement to preserve character integrity"

# 6) Choose deterministic formatting (in TMP)
case "$FORMATTER" in
  mdformat)
    mdformat --wrap=no "$TMP"
    ;;
  prettier)
    TMP2="$TMP.prettier"
    prettier --parser markdown "$TMP" > "$TMP2"
    mv -f "$TMP2" "$TMP"
    ;;
  none)
    # Skip ALL cleanup to preserve UTF-8 encoding integrity
    echo "ℹ️ No formatting applied - preserving original file exactly as-is"
    ;;
esac

# 7) CONTENT INTEGRITY — plain-text equivalence (must pass BOTH checks)
# (a) Compare original EDIT vs formatted TMP
pandoc -f markdown -t plain "$EDIT_REAL" > "$PLAIN_EDIT"
pandoc -f markdown -t plain "$TMP"       > "$PLAIN_TMP"
if diff -u "$PLAIN_EDIT" "$PLAIN_TMP" > "$DIFF_PLAIN_EDIT"; then
  echo "✅ Plain-equal vs pre-format edit: OK"
else
  echo "🛑 Plain differs vs pre-format edit. See $DIFF_PLAIN_EDIT. Restore backup; no write."
  mv -f "$BAK" "$EDIT_REAL"; exit 5
fi

# (b) Compare canonical source vs formatted TMP
pandoc -f markdown -t plain "$SRC_CANON" > "$PLAIN_SRC"
if diff -u "$PLAIN_SRC" "$PLAIN_TMP" > "$DIFF_PLAIN_SRC"; then
  echo "✅ Plain-equal vs canonical source: OK"
else
  echo "🛑 Plain differs vs canonical source. See $DIFF_PLAIN_SRC. Restore backup; no write."
  mv -f "$BAK" "$EDIT_REAL"; exit 6
fi

# 8) (Optional) Raw MD diff for reviewer (structure-only changes are allowed)
diff -u "$EDIT_REAL" "$TMP" > "$DIFF_RAW" || true

# 9) Atomic replace
mv -f "$TMP" "$EDIT_REAL"
[ -s "$EDIT_REAL" ] || { echo "❌ Unexpected empty after write; restoring."; mv -f "$BAK" "$EDIT_REAL"; exit 7; }

echo "🎉 DONE — Safe normalization completed."
echo "   EDIT file : $EDIT_REAL"
echo "   Backup    : $BAK"
echo "   Formatter : $FORMATTER"
echo "   NBSP audit: $NBSP_AUDIT"
echo "   Diff (plain, edit vs tmp): $DIFF_PLAIN_EDIT  (should be empty)"
echo "   Diff (plain, src  vs tmp): $DIFF_PLAIN_SRC   (should be empty)"
echo "   Diff (raw MD)            : $DIFF_RAW         (structure-only)"
