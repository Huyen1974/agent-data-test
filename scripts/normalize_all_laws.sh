#!/usr/bin/env bash
set -euo pipefail

PROJ="/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid"
SRC="$PROJ/nhap_cursor/ALL_LAWs.md"
DOCX="$PROJ/nhap_cursor/ALL_LAWs.docx"
NOW="$(date +%Y%m%dT%H%M%S)"
BAK="$PROJ/nhap_cursor/ALL_LAWs.bak.$NOW.md"
TMP="$PROJ/nhap_cursor/ALL_LAWs.normalized.tmp.md"
PLAIN_SRC="$PROJ/nhap_cursor/ALL_LAWs.orig.plain.txt"
PLAIN_TMP="$PROJ/nhap_cursor/ALL_LAWs.norm.plain.txt"
DIFF_PLAIN="$PROJ/nhap_cursor/ALL_LAWs.plain.diff"
DIFF_RAW="$PROJ/nhap_cursor/ALL_LAWs.raw.diff"
NBSP_AUDIT="$PROJ/nhap_cursor/ALL_LAWs.nbsp_audit.txt"
HEAD_MD="$PROJ/nhap_cursor/ALL_LAWs.md.headings.txt"
HEAD_DOCX="$PROJ/nhap_cursor/ALL_LAWs.word.headings.txt"
HEAD_AUDIT="$PROJ/nhap_cursor/ALL_LAWs.heading_audit.diff"

# 0) dquote safety for integrated shells
export RPROMPT="" || true
stty sane || true

cd "$PROJ"
[ -f "$SRC" ] && [ -s "$SRC" ] || { echo "❌ Missing or empty: $SRC"; exit 1; }

# 1) Tools check
if ! command -v pandoc >/dev/null 2>&1; then
  echo "❌ pandoc not found. Install: brew install pandoc"; exit 2
fi
FORMATTER=""
if command -v mdformat >/dev/null 2>&1; then
  FORMATTER="mdformat"
elif command -v prettier >/dev/null 2>&1; then
  FORMATTER="prettier"
else
  echo "ℹ️ No formatter found; will normalize minimal whitespace only."
  FORMATTER="none"
fi

# 2) Backup original
cp -p "$SRC" "$BAK"

# 3) Copy -> TMP and normalize NBSP safely (log occurrences)
cp "$SRC" "$TMP"
# Count NBSP (U+00A0) - using hexdump and awk for macOS compatibility
hexdump -C "$TMP" | awk '/c2 a0/ {count++} END {print count+0}' > "$NBSP_AUDIT.count"
NBSP_COUNT="$(cat "$NBSP_AUDIT.count" | tr -d " ")"
# Find line numbers with NBSP for audit
python3 -c "
import sys
with open('$TMP', 'rb') as f:
    content = f.read()
text = content.decode('utf-8')
lines = text.split('\n')
nbsp_lines = []
for i, line in enumerate(lines, 1):
    if '\u00a0' in line:
        nbsp_lines.append(f'Line {i}: {line}')
with open('$NBSP_AUDIT', 'w') as f:
    f.write(f'NBSP count: {content.count(b\"\xc2\xa0\")}\n')
    if nbsp_lines:
        f.write('Lines with NBSP:\n')
        f.write('\n'.join(nbsp_lines))
    else:
        f.write('No NBSP found.')
" && NBSP_COUNT="$(head -1 "$NBSP_AUDIT" | awk '{print $3}')"
if [ "${NBSP_COUNT}" -gt 0 ]; then
  # replace NBSP with regular spaces
  perl -CS -pe "s/\x{00A0}/ /g" "$TMP" > "$TMP.nbspfix" && mv "$TMP.nbspfix" "$TMP"
fi

# 4) Run formatter on TMP (in-place)
case "$FORMATTER" in
  mdformat)
    # keep long lines to avoid semantic re-wrapping issues
    mdformat --wrap=no "$TMP"
    ;;
  prettier)
    # write to a new file then replace to avoid partial writes
    TMP2="$TMP.prettier"
    prettier --parser markdown "$TMP" > "$TMP2"
    mv -f "$TMP2" "$TMP"
    ;;
  none)
    # minimal cleanup: trim trailing spaces only (non-semantic)
    sed -E "s/[[:space:]]+$//" "$TMP" > "$TMP.tr" && mv "$TMP.tr" "$TMP"
    ;;
esac

# 5) Prove plain-text equivalence (semantic no-loss)
pandoc -f markdown -t plain "$SRC" > "$PLAIN_SRC"
pandoc -f markdown -t plain "$TMP" > "$PLAIN_TMP"
if diff -u "$PLAIN_SRC" "$PLAIN_TMP" > "$DIFF_PLAIN"; then
  echo "✅ Plain-text equivalence: OK"
else
  echo "🛑 Plain-text differs! See $DIFF_PLAIN. Restoring original; no write."
  mv -f "$BAK" "$SRC"
  exit 3
fi

# Additionally show raw MD diff (for reviewer eyes only)
diff -u "$SRC" "$TMP" > "$DIFF_RAW" || true

# 6) Atomic replace original with normalized TMP
mv -f "$TMP" "$SRC"
[ -s "$SRC" ] || { echo "❌ Unexpected empty after write."; mv -f "$BAK" "$SRC"; exit 4; }

# 7) Coverage audit vs Word (if DOCX exists)
if [ -f "$DOCX" ]; then
  # Extract simple headings/hints from docx and md
  pandoc -t plain "$DOCX" | awk "NF" > "$HEAD_DOCX"
  grep -E "^(#|##|###|####|#####|######) " "$SRC" > "$HEAD_MD" || true
  diff -u "$HEAD_DOCX" "$HEAD_MD" > "$HEAD_AUDIT" || true
  echo "ℹ️ Headings audit vs Word → $HEAD_AUDIT (non-empty diff means gaps/mismatch to review)."
else
  echo "ℹ️ Word doc not found; skipping coverage audit."
fi

echo "🎉 DONE — Safe normalization completed."
echo "   Backup     : $BAK"
echo "   Diff plain : $DIFF_PLAIN (should be empty/no changes)"
echo "   Diff raw   : $DIFF_RAW (structure-only changes allowed)"
echo "   NBSP audit : $NBSP_AUDIT"
echo "   Formatter  : $FORMATTER"
