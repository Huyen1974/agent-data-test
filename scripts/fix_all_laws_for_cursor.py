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
    raw = os.path.join(PROJ_DST, " ALL_LAWs_edit.md")
    if os.path.isfile(raw):
        return raw
    # fallback: find any file whose NBSP/space-trimmed name equals ALL_LAWs_edit.md
    want = "ALL_LAWs_edit.md"
    for name in os.listdir(PROJ_DST):
        nm = name.replace("\u00a0", " ").strip()
        if nm == want:
            return os.path.join(PROJ_DST, name)
    return None


def to_soft_plain(text: str) -> str:
    t = text
    # remove heading hashes
    t = re.sub(r"^\s*#{1,6}\s+", "", t, flags=re.M)
    # table pipes → tabs, remove fence lines
    t = re.sub(r"^\s*```.*$", "", t, flags=re.M)
    t = re.sub(r"^\s*\|", "", t, flags=re.M)
    t = t.replace(" | ", "\t").replace("| ", "\t").replace(" |", "\t").replace("|", "")
    # list marker we add before the existing bullet
    t = re.sub(r"^\s*-\s+(•)", r"\1", t, flags=re.M)
    # collapse runs of whitespace
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s+\n", "\n", t)
    return t.strip()


def pandoc_plain(path: str):
    try:
        r = subprocess.run(
            ["pandoc", "-f", "markdown", "-t", "plain", path],
            check=True,
            capture_output=True,
            text=True,
        )
        return r.stdout
    except Exception:
        return None


def split_lines(s):
    return s.splitlines()


def detect_2col_table(lines, i):
    # detect a contiguous GFM table block with exactly 2 cols
    def pipe_row(row):
        return (
            row.count("|") >= 2
            and not row.strip().startswith("```")
            and row.strip() != ""
        )

    n = len(lines)
    if not pipe_row(lines[i]):
        return None
    start = i
    while i < n and pipe_row(lines[i]):
        i += 1
    end = i
    block = lines[start:end]
    if len(block) < 2:
        return None

    # second line must be header separator with 2 columns
    def is_sep(row):
        t = row.strip().strip("|").strip()
        parts = [p.strip() for p in t.split("|")]
        if len(parts) < 2:
            return False
        return all(re.fullmatch(r":?-{3,}:?", p) for p in parts)

    if not is_sep(block[1]):
        return None

    # consistent 2 columns?
    def col_count(row):
        parts = row.split("|")
        if parts and parts[0].strip() == "" and row.strip().startswith("|"):
            parts = parts[1:]
        if parts and parts[-1].strip() == "" and row.strip().endswith("|"):
            parts = parts[:-1]
        return len(parts)

    cols = [col_count(r) for r in block]
    if len(set(cols)) != 1 or cols[0] != 2:
        return None
    return start, end, block


def parse_cells(row):
    parts = row.split("|")
    if parts and parts[0].strip() == "" and row.strip().startswith("|"):
        parts = parts[1:]
    if parts and parts[-1].strip() == "" and row.strip().endswith("|"):
        parts = parts[:-1]
    return [p.strip() for p in parts]


def transform(md: str) -> str:
    lines = split_lines(md)
    out = []
    i = 0
    n = len(lines)

    while i < n:
        det = detect_2col_table(lines, i)
        if det:
            a, b, block = det
            body = block[2:]
            # bullet-as-table case: every body row has first cell exactly "- •"
            bullets = []
            bullet_shape = True
            for row in body:
                c = parse_cells(row)
                if len(c) != 2 or c[0] != "- •":
                    bullet_shape = False
                    break
                bullets.append(c[1])
            if bullet_shape and len(bullets) >= 1:
                # convert to real list items
                for t in bullets:
                    out.append(f"- • {t}")
                i = b
                continue
            # not a bullet-table → keep original block
            out.extend(block)
            i = b
            continue

        # For safety and simplicity, if not a pipe row → copy through
        if not (lines[i].count("|") >= 2 and not lines[i].strip().startswith("```")):
            out.append(lines[i])
            i += 1
            continue

        # Otherwise, copy the row (we'll handle HP-05 in a separate pass)
        out.append(lines[i])
        i += 1

    txt = "\n".join(out)

    # HP-05 merge pass: Handle the specific HP-05 case conservatively
    # Instead of merging into table cell, just put the continuation sentence as a paragraph after the table
    hp05_lines = txt.splitlines()
    hp05_out = []
    i = 0
    n = len(hp05_lines)

    while i < n:
        line = hp05_lines[i]
        # Look for HP-05 row followed by continuation row starting with Vietnamese text
        if (
            i + 1 < n
            and re.match(r"^\|\s*HP-05\s*\|", line)
            and re.match(
                r"^\|\s*Trong trường hợp quy trình đồng bộ tự động", hp05_lines[i + 1]
            )
        ):

            # Keep the HP-05 row as is
            hp05_out.append(line)

            # Parse the continuation row to extract the sentence
            cont_cells = parse_cells(hp05_lines[i + 1])
            if len(cont_cells) >= 1:
                # Put the continuation sentence as a simple paragraph (not in table)
                continuation_sentence = cont_cells[
                    0
                ]  # "Trong trường hợp quy trình đồng bộ tự động..."
                hp05_out.append("")  # Empty line for separation
                hp05_out.append(continuation_sentence)
                i += 2  # Skip both rows
                continue

        hp05_out.append(line)
        i += 1

    new_txt = "\n".join(hp05_out)

    return new_txt


def main():
    target = resolve_target()
    if not target or not os.path.isfile(target):
        print("❌ Cannot resolve edit file in:", PROJ_DST)
        sys.exit(1)
    canon = SRC_CANON
    if not os.path.isfile(canon):
        print("❌ Canonical source not found:", canon)
        sys.exit(2)

    original = open(target, encoding="utf-8", errors="replace").read()
    canonical = open(canon, encoding="utf-8", errors="replace").read()
    fixed = transform(original)

    now = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    bak = f"{target}.bak.{now}"
    tmp = f"{target}.tmp.{now}"
    open(bak, "w", encoding="utf-8", newline="\n").write(original)
    open(tmp, "w", encoding="utf-8", newline="\n").write(fixed)

    # STRICT: pandoc plain
    def pplain(p):
        try:
            r = subprocess.run(
                ["pandoc", "-f", "markdown", "-t", "plain", p],
                check=True,
                capture_output=True,
                text=True,
            )
            return r.stdout
        except Exception:
            return None

    strict_ok = False
    p_orig = pplain(target)
    p_tmp = pplain(tmp)
    p_can = pplain(canon)
    if p_orig is not None and p_tmp is not None and p_can is not None:
        strict_ok = (p_orig == p_tmp) and (p_can == p_tmp)

    # SOFT fallback: token/whitespace-insensitive
    soft_ok = (to_soft_plain(original) == to_soft_plain(fixed)) and (
        to_soft_plain(canonical) == to_soft_plain(fixed)
    )

    if not (strict_ok or soft_ok):
        print("🛑 Semantic parity failed. No write.")
        print("Backup:", bak)
        print("Temp  :", tmp)
        sys.exit(3)

    # Atomic replace
    shutil.move(tmp, target)
    print("🎉 DONE — structure fixed for LLM understanding, text meaning preserved.")
    print("Edit file:", target)
    print("Backup   :", bak)
    print(f"Checks   : strict_ok={strict_ok}, soft_ok={soft_ok}")


if __name__ == "__main__":
    main()
