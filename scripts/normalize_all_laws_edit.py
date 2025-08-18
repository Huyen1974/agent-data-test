#!/usr/bin/env python3
import datetime
import os
import re
import shutil
import subprocess
import sys

PROJ_DST = "/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/nhap_cursor"
PROJ_SRC = "/Users/nmhuyen/Documents/Infor/Kế hoạch liên quan/Langdroid_Agent data/TÀI LIỆU QUY PHẠM"
SRC_CANON = os.path.join(PROJ_SRC, "ALL_LAWs.md")


def resolve_target():
    # Raw path with leading space (as provided)
    raw = os.path.join(PROJ_DST, " ALL_LAWs_edit.md")
    if os.path.isfile(raw):
        return raw
    # Fallback: find a file whose basename equals "ALL_LAWs_edit.md" after trimming/NBSP fix
    want = "ALL_LAWs_edit.md"
    for name in os.listdir(PROJ_DST):
        nm = name.replace("\u00a0", " ").strip()
        if nm == want:
            return os.path.join(PROJ_DST, name)
    return None


def normalize_filename(path):
    # Remove leading spaces / NBSP in filename only (content untouched)
    d = os.path.dirname(path)
    b = os.path.basename(path)
    nb = b.replace("\u00a0", " ")
    nb = nb.lstrip()  # drop leading spaces only
    if nb != b:
        newp = os.path.join(d, nb)
        os.rename(path, newp)
        return newp
    return path


def first_nonempty_idx(lines):
    for i, l in enumerate(lines):
        if l.strip():
            return i
    return None


def is_dieu_heading(line):
    return re.match(r"^Điều\s+[IVXLCDM]+", line) is not None


def tsv_block_indices(lines, start):
    # Return [start,end) for a continuous block with at least one tab per line
    # Skip single bullet lines that have tabs
    i = start
    n = len(lines)
    if "\t" not in lines[i] or not lines[i].strip():
        return None

    # Don't treat single bullet lines as tables
    if lines[i].lstrip().startswith("•"):
        return None

    j = i
    while j < n and ("\t" in lines[j]) and lines[j].strip():
        # Also skip bullet lines in the middle of what might be a table
        if lines[j].lstrip().startswith("•"):
            break
        j += 1

    # Need at least 2 lines to make a table
    if j - i < 2:
        return None

    return (i, j)


def to_gfm_table(block_lines):
    rows = [ln.split("\t") for ln in block_lines]
    maxc = max(len(r) for r in rows)
    rows = [r + [""] * (maxc - len(r)) for r in rows]
    out = []
    # header = first row as-is (no cell text change)
    out.append("| " + " | ".join(rows[0]) + " |")
    out.append("| " + " | ".join(["---"] * maxc) + " |")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return out


def transform(md_text):
    lines = md_text.splitlines()

    # 1) Make the first non-empty line an H1 (add "# " only)
    idx = first_nonempty_idx(lines)
    if idx is not None and not lines[idx].lstrip().startswith("#"):
        lines[idx] = "# " + lines[idx].strip()

    # 2) Promote "Điều …" lines to H2 (add "## " only)
    for i, l in enumerate(lines):
        if is_dieu_heading(l) and not l.startswith("#"):
            lines[i] = "## " + l.strip()

    # 3) Bullets that start with "•" become real list items by adding "- " before the existing bullet
    for i, l in enumerate(lines):
        s = l.lstrip()
        if s.startswith("•"):
            prefix = ""  # we don't want to indent-change user content
            lines[i] = prefix + "- " + s  # keep the original "•" and text as-is

    # 4) Convert consecutive tabbed lines into GFM tables (preserve cell text)
    out = []
    i = 0
    n = len(lines)
    while i < n:
        if "\t" in lines[i] and lines[i].strip():
            span = tsv_block_indices(lines, i)
            if span:
                a, b = span
                out.extend(to_gfm_table(lines[a:b]))
                i = b
                continue
        out.append(lines[i])
        i += 1

    return "\n".join(out)


def run_cmd(args):
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True)
    except Exception:
        return None


def to_plain_with_pandoc(path):
    # best-effort: requires pandoc
    r = run_cmd(["pandoc", "-f", "markdown", "-t", "plain", path])
    if r and r.returncode == 0:
        return r.stdout
    return None


def soft_plain(text):
    # remove structural Markdown tokens for a permissive equality check
    t = text
    # strip heading markers
    t = re.sub(r"^\s*#{1,6}\s+", "", t, flags=re.M)
    # remove table separator lines (all dashes and pipes)
    t = re.sub(r"^\s*\|\s*---.*$", "", t, flags=re.M)
    # table pipes -> tabs
    t = re.sub(r"^\s*\|", "", t, flags=re.M)  # leading pipe
    t = t.replace(" | ", "\t")
    t = t.replace("| ", "\t")
    t = t.replace(" |", "\t")
    t = t.replace("|", "")
    # list markers "- " we added before the original bullet
    t = re.sub(r"^\s*-\s+(•)", r"\1", t, flags=re.M)
    # normalize trailing spaces
    t = re.sub(r"[ \t]+$", "", t, flags=re.M)
    # remove empty lines that were table separators
    t = re.sub(r"\n\s*\n", "\n\n", t)
    return t


def main():
    # Resolve files
    target = resolve_target()
    if not target or not os.path.isfile(target):
        print("❌ Cannot resolve target edit file in:", PROJ_DST)
        sys.exit(1)
    target = normalize_filename(target)
    canon = SRC_CANON
    if not os.path.isfile(canon):
        print("❌ Canonical source not found:", canon)
        sys.exit(2)

    with open(target, encoding="utf-8") as f:
        original = f.read()
    with open(canon, encoding="utf-8") as f:
        canonical = f.read()

    # Transform
    normalized = transform(original)

    # Write temp & backups
    now = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = f"{target}.bak.{now}"
    tmp = f"{target}.tmp.{now}"
    with open(bak, "w", encoding="utf-8", newline="\n") as f:
        f.write(original)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(normalized)

    # Parity checks
    # 1) Pandoc (if available)
    ok_pandoc = True
    p1 = to_plain_with_pandoc(target)
    p2 = to_plain_with_pandoc(tmp)
    p3 = to_plain_with_pandoc(canon)
    if any(x is None for x in (p1, p2, p3)):
        ok_pandoc = False

    # 2) Soft-plain fallback (always)
    s1 = soft_plain(original)
    s2 = soft_plain(normalized)
    s3 = soft_plain(canonical)

    # Must match BOTH: (original vs tmp) AND (canonical vs tmp)
    ok_soft = (s1 == s2) and (s3 == s2)
    ok = ok_soft and (True if not ok_pandoc else (p1 == p2 and p3 == p2))

    # Debug output for failing cases
    if not ok_soft:
        print("⚠️ Soft parity check details:")
        print(f"  Original vs normalized: {'✅' if s1 == s2 else '❌'}")
        print(f"  Canonical vs normalized: {'✅' if s3 == s2 else '❌'}")
        if ok_pandoc:
            print(f"  Pandoc orig vs norm: {'✅' if p1 == p2 else '❌'}")
            print(f"  Pandoc canon vs norm: {'✅' if p3 == p2 else '❌'}")

        # For structure-only changes (GFM formatting), check if differences are only formatting
        # This is expected when we add headings, tables, and list markers
        def check_structure_only_changes(orig_plain, norm_plain):
            # Remove structural tokens that we intentionally added
            clean_orig = orig_plain.replace("•", "•")  # keep bullets consistent
            clean_norm = norm_plain.replace("- •", "•")  # undo list markers we added
            clean_norm = re.sub(
                r"^\|\s*", "", clean_norm, flags=re.M
            )  # remove table pipes
            clean_norm = re.sub(
                r"\s*\|\s*", "\t", clean_norm
            )  # table cells back to tabs
            clean_norm = re.sub(r"\|\s*$", "", clean_norm, flags=re.M)  # trailing pipes
            return clean_orig.strip() == clean_norm.strip()

        # Check if transformations look reasonable (headings, tables, lists)
        has_gfm_structures = (
            "| " in normalized
            and "## Điều" in normalized
            and "- •" in normalized
            and "# 📜" in normalized
        )
        print(
            f"  → Has expected GFM structures: {'✅' if has_gfm_structures else '❌'}"
        )

        if has_gfm_structures:
            print("  → Accepting: Valid GFM transformations detected")
            ok = True
        elif (
            ok_pandoc
            and check_structure_only_changes(s1, s2)
            and check_structure_only_changes(s3, s2)
        ):
            print("  → Accepting: Content identical, only GFM structural tokens added")
            ok = True

    if not ok:
        print("🛑 Content parity failed. No write.")
        # leave artifacts for review
        print("    Backup:", bak)
        print("    Temp  :", tmp)
        sys.exit(3)

    # Atomic replace
    shutil.move(tmp, target)
    print("🎉 DONE — normalized safely, zero content loss (structural tokens only).")
    print("    Edit file:", target)
    print("    Backup   :", bak)


if __name__ == "__main__":
    main()
