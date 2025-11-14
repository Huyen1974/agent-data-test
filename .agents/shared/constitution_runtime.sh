#!/usr/bin/env bash
# Constitution Runtime Helper
# Provides snapshot building, SHA-256 verification, and preamble display for agent startup

set -euo pipefail

# Normalize CRLF to LF and trim trailing whitespace
const_norm() {
    awk '{ sub(/\r$/,""); gsub(/[[:space:]]+$/, ""); print }'
}

# Compute SHA-256 (cross-platform: macOS uses shasum, Linux uses sha256sum)
const_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 | awk '{print $1}'
    else
        echo "ERROR: No SHA-256 tool available" >&2
        return 1
    fi
}

# Extract a section from constitution file
# Usage: const_extract SECTION_ID < constitution_file
# Example: const_extract VII < docs/constitution/CONSTITUTION.md
const_extract() {
    local section_id="$1"

    # Strict regex for Roman numeral sections: "## Điều VII" or "## Section VII"
    # Anchored pattern: must have space or end-of-line after section ID
    # Extract from section start until next same-level heading (##)
    awk -v sect="$section_id" '
        BEGIN { in_section=0 }
        /^##[[:space:]]+(Điều|Section)[[:space:]]+/ {
            # Build strict pattern: section ID must be followed by space/colon/end-of-line
            # This prevents "VII" from matching "VIII" or "VIIA"
            pattern = "^##[[:space:]]+(Điều|Section)[[:space:]]+" sect "([[:space:]]|:|$)"
            if ($0 ~ pattern) {
                in_section=1
                print
                next
            }
            # If we hit another ## heading while in section, stop
            if (in_section) {
                exit
            }
        }
        in_section { print }
    ' | const_norm
}

# Build constitution snapshot from specified sections
# Usage: const_build_snapshot PATH SECTIONS OUTFILE
# Example: const_build_snapshot docs/constitution/CONSTITUTION.md "VII,IX" /tmp/constitution.snapshot.md
const_build_snapshot() {
    local const_path="$1"
    local sections="$2"
    local outfile="$3"

    if [[ ! -f "$const_path" ]]; then
        echo "ERROR: Constitution file not found: $const_path" >&2
        return 1
    fi

    # Create temp file
    local tmpfile
    tmpfile=$(mktemp)

    # Portable section splitting (Bash 3.2+ compatible)
    # Convert comma-separated string to newline-separated, then iterate
    printf '%s\n' "$sections" | tr ',' '\n' | while IFS= read -r section; do
        # Trim leading/trailing whitespace (portable: no xargs dependency)
        section=$(printf '%s' "$section" | awk '{gsub(/^[[:space:]]+|[[:space:]]+$/,"")}1')

        # Skip empty sections
        [[ -z "$section" ]] && continue

        echo "# Extracting Section: $section" >> "$tmpfile"
        echo "" >> "$tmpfile"
        const_extract "$section" < "$const_path" >> "$tmpfile"
        echo "" >> "$tmpfile"
        echo "---" >> "$tmpfile"
        echo "" >> "$tmpfile"
    done

    # Move to final location
    mv "$tmpfile" "$outfile"

    if [[ ! -s "$outfile" ]]; then
        echo "ERROR: Snapshot is empty: $outfile" >&2
        return 1
    fi
}

# Display constitution banner with Ask-Read-Cite-Act reminder
const_banner() {
    local path="${AGENT_CONSTITUTION_PATH:-unknown}"
    local sections="${AGENT_CONSTITUTION_SECTIONS:-unknown}"
    local snapshot="${AGENT_CONSTITUTION_SNAPSHOT:-unknown}"
    local sha="${AGENT_CONSTITUTION_SHA:-unknown}"

    cat <<'BANNER'
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🏛️  RUNTIME CONSTITUTION POLICY 🏛️                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
BANNER

    echo ""
    echo "📜 Source: $path"
    echo "🎯 Active Sections: $sections"
    echo "📸 Snapshot: $snapshot"
    echo "🔒 SHA-256: $sha"
    echo ""

    cat <<'PROCESS'
┌──────────────────────────────────────────────────────────────────────────────┐
│ ⚠️  MANDATORY PROCESS: Ask → Read → Cite → Act                              │
└──────────────────────────────────────────────────────────────────────────────┘

Before ANY sensitive operation (Qdrant, GCS, Secrets, Terraform):

  1️⃣  ASK:   "What does the constitution say about X?"
  2️⃣  READ:  Open and read the relevant section
  3️⃣  CITE:  Quote 2-3 lines from the constitution
  4️⃣  ACT:   Execute only if aligned with cited rules

❌ NEVER rely on memory or assumptions
✅ ALWAYS cite article & line before acting

PROCESS

    echo ""
}

# Display common operation checklists
const_checklist() {
    cat <<'CHECKLIST'
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📋 COMMON OPERATION CHECKLISTS                                              │
└──────────────────────────────────────────────────────────────────────────────┘

🔹 Qdrant Operations:
   □ Check QD-LAW for cluster naming (agent-data-vector-dev-useast4)
   □ Verify collection naming pattern: <env>_documents
   □ Confirm snapshot backup requirements (daily for prod, weekly for test)

🔹 GCS Bucket Operations:
   □ Check TF-LAW for naming: <standard-prefix>-agent-data-<purpose>-<env>
   □ Verify uniform_bucket_level_access = true (HP-02)
   □ Confirm lifecycle policy matches HP-CI-03

🔹 Secret Management:
   □ Check GH-LAW §5 for secret sync model
   □ Verify rotation policy: 90d (prod), 120d (test) per HP-SEC-02
   □ Confirm Secret Manager as source of truth (HP-05)

For complete rules, read: $AGENT_CONSTITUTION_PATH

CHECKLIST

    echo ""
}
