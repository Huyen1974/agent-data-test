#!/usr/bin/env python3
import datetime
import os
import shutil
import subprocess
import sys


def run_cmd(args):
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True)
    except Exception:
        return None


def to_plain_with_pandoc(path):
    r = run_cmd(["pandoc", "-f", "markdown", "-t", "plain", path])
    if r and r.returncode == 0:
        return r.stdout
    return None


def main():
    # File paths
    target = "/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid/nhap_cursor/ALL_LAWs_edit.md"
    canonical = "/Users/nmhuyen/Documents/Infor/Kế hoạch liên quan/Langdroid_Agent data/TÀI LIỆU QUY PHẠM/ALL_LAWs.md"

    # Check files exist
    if not os.path.isfile(target):
        print(f"❌ Target file not found: {target}")
        sys.exit(1)
    if not os.path.isfile(canonical):
        print(f"❌ Canonical file not found: {canonical}")
        sys.exit(1)

    # Check pandoc availability
    if not run_cmd(["pandoc", "--version"]):
        print("❌ pandoc not found. Install with: brew install pandoc")
        sys.exit(2)

    # Read original content
    with open(target, encoding="utf-8") as f:
        original = f.read()

    # Create backup and temp files
    now = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = f"{target}.bak.{now}"
    temp_path = f"{target}.tmp.{now}"

    # Backup original
    shutil.copy2(target, backup_path)
    print(f"✅ Backup created: {backup_path}")

    # Apply minimal cleanup
    lines = original.splitlines()

    # 1) Remove trailing whitespace on all lines
    cleaned_lines = [line.rstrip() for line in lines]

    # 2) Optionally replace inline TABs at L4 and L279 with single space
    # (Line numbers are 1-based, so index 3 and 278)
    if len(cleaned_lines) > 3:
        # L4: Replace tabs with single space
        cleaned_lines[3] = cleaned_lines[3].replace("\t", " ")

    if len(cleaned_lines) > 278:
        # L279: Replace tabs with single space
        cleaned_lines[278] = cleaned_lines[278].replace("\t", " ")

    # Reconstruct content
    cleaned = "\n".join(cleaned_lines)
    if original.endswith("\n"):
        cleaned += "\n"

    # Write temp file
    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(cleaned)

    # Parity checks using pandoc
    print("🔍 Running parity checks...")

    # Check 1: original-edit vs temp
    plain_orig = to_plain_with_pandoc(target)
    plain_temp = to_plain_with_pandoc(temp_path)
    plain_canon = to_plain_with_pandoc(canonical)

    if not all([plain_orig, plain_temp, plain_canon]):
        print("❌ Pandoc conversion failed")
        os.remove(temp_path)
        sys.exit(3)

    # Generate diff paths for reporting
    diff_edit_vs_temp = f"{target}.diff_edit_vs_temp.{now}"
    diff_canon_vs_temp = f"{target}.diff_canon_vs_temp.{now}"

    # Check parity - primary focus is preserving current edit file content
    edit_vs_temp_ok = plain_orig == plain_temp

    # Note: canonical comparison for info only since edit file is already GFM-formatted
    canon_vs_temp_ok = plain_canon == plain_temp

    # Write diff files for review
    with open(diff_edit_vs_temp, "w", encoding="utf-8") as f:
        if edit_vs_temp_ok:
            f.write("No differences - plain text identical\n")
        else:
            f.write("=== ORIGINAL EDIT ===\n")
            f.write(plain_orig)
            f.write("\n=== CLEANED TEMP ===\n")
            f.write(plain_temp)

    with open(diff_canon_vs_temp, "w", encoding="utf-8") as f:
        if canon_vs_temp_ok:
            f.write("No differences - plain text identical\n")
        else:
            f.write("=== CANONICAL (INFO ONLY) ===\n")
            f.write(plain_canon)
            f.write("\n=== CLEANED TEMP ===\n")
            f.write(plain_temp)

    # Report results
    print("📋 Parity check results:")
    print(f"   Original edit vs temp: {'✅ PASS' if edit_vs_temp_ok else '❌ FAIL'}")
    print(
        f"   Canonical vs temp:     {'ℹ️ INFO' if canon_vs_temp_ok else 'ℹ️ DIFF'} (GFM vs original format)"
    )
    print(f"   Diff (edit vs temp):   {diff_edit_vs_temp}")
    print(f"   Diff (canon vs temp):  {diff_canon_vs_temp}")

    # Accept if current edit content is preserved (canonical diff expected due to GFM)
    if edit_vs_temp_ok:
        # Atomic replace
        shutil.move(temp_path, target)
        print("🎉 SUCCESS - Minimal cleanup completed")
        print("   ✅ Trailing whitespace removed")
        print("   ✅ Inline TABs (L4, L279) → single space")
        print("   ✅ Content parity verified")
        print(f"   📁 Backup: {backup_path}")
    else:
        # Abort - restore original and report
        os.remove(temp_path)
        print("🛑 ABORTED - Content parity check failed")
        print("   Original file unchanged")
        print(f"   📁 Backup: {backup_path}")
        sys.exit(4)


if __name__ == "__main__":
    main()
