"""Migrate old GitHub docs into V3 Firestore KB structure.

Reads from /api/docs/file (GitHub), writes to POST /documents (Firestore KB).
Does NOT delete originals — backward compatible.
"""

import os
import subprocess
import sys
import time

import httpx

BASE_URL = os.getenv(
    "AGENT_DATA_URL", "https://agent-data-test-812872501910.asia-southeast1.run.app"
)
API_KEY = os.getenv("API_KEY", "C38FE9FA-2BC6-4FBB-BA0C-981E8FB89450")

# Migration mapping: (old_path, new_v3_path, v3_parent)
MIGRATION_MAP = [
    # Foundation
    (
        "docs/ssot/constitution.md",
        "docs/foundation/constitution/constitution-v1.11e.md",
        "docs/foundation/constitution",
    ),
    (
        "docs/ssot/Law_of_data_and_connection.md",
        "docs/foundation/laws/data-connection-law.md",
        "docs/foundation/laws",
    ),
    # Blueprints → plans/blueprints
    (
        "docs/dev/blueprints/AGENCY_OS_E1_BLUEPRINT.md",
        "docs/plans/blueprints/agency-os-e1.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/ARCHITECTURE_DECISIONS.md",
        "docs/plans/blueprints/architecture-decisions.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/BUCKETS_MASTER_BLUEPRINT.md",
        "docs/plans/blueprints/buckets-master.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/BUSINESS_OS_BLUEPRINT.md",
        "docs/plans/blueprints/business-os.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/BUSINESS_OS_BLUEPRINT_Ver.OPUS.md",
        "docs/plans/blueprints/business-os-opus.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/DOT_V01_BLUEPRINT.md",
        "docs/plans/blueprints/dot-v01.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/E1_Plan.md",
        "docs/plans/blueprints/e1-plan.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/KNOWLEDGE HUB.md",
        "docs/plans/blueprints/knowledge-hub.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/Opus_buckets_reform_plan.md",
        "docs/plans/blueprints/opus-buckets-reform.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/PHASE_5_DIRECTUS_BLUEPRINT.md",
        "docs/plans/blueprints/phase-5-directus.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/PHULUC_16_E1_BLUEPRINT.md",
        "docs/plans/blueprints/phuluc-16-e1.md",
        "docs/plans/blueprints",
    ),
    (
        "docs/dev/blueprints/PHULUC_17_E1_BLUEPRINT.md",
        "docs/plans/blueprints/phuluc-17-e1.md",
        "docs/plans/blueprints",
    ),
    # Investigations → operations/research
    (
        "docs/dev/investigations/Antigravity_Phase3_Investigation_Report.md",
        "docs/operations/research/antigravity-phase3.md",
        "docs/operations/research",
    ),
    (
        "docs/dev/investigations/Claude_Phase3_Investigation_Report.md",
        "docs/operations/research/claude-phase3.md",
        "docs/operations/research",
    ),
    (
        "docs/dev/investigations/Codex_Phase3_Investigation_Report.md",
        "docs/operations/research/codex-phase3.md",
        "docs/operations/research",
    ),
    (
        "docs/dev/investigations/Phase3_0_Execution_Report.md",
        "docs/operations/research/phase3-execution.md",
        "docs/operations/research",
    ),
    (
        "docs/dev/investigations/TOOL_INVENTORY.md",
        "docs/operations/research/tool-inventory.md",
        "docs/operations/research",
    ),
    (
        "docs/dev/investigations/TaskB_Local_Verification_Report.md",
        "docs/operations/research/taskb-local-verification.md",
        "docs/operations/research",
    ),
    # Reports → operations/sessions
    (
        "docs/dev/reports/PHASE_C_CLOSURE_REPORT.md",
        "docs/operations/sessions/phase-c-closure.md",
        "docs/operations/sessions",
    ),
    # SSOT → plans/specs or plans/processes
    (
        "docs/dev/ssot/AI_ACTION_SETUP_GUIDE.md",
        "docs/plans/processes/ai-action-setup-guide.md",
        "docs/plans/processes",
    ),
    (
        "docs/dev/ssot/AI_AGENT_REGISTRY.md",
        "docs/plans/specs/ai-agent-registry.md",
        "docs/plans/specs",
    ),
    (
        "docs/dev/ssot/AI_AGENT_SETUP.md",
        "docs/plans/processes/ai-agent-setup.md",
        "docs/plans/processes",
    ),
    (
        "docs/dev/ssot/LOCAL_DEVELOPMENT_ENVIRONMENT.md",
        "docs/plans/processes/local-dev-environment.md",
        "docs/plans/processes",
    ),
    (
        "docs/dev/ssot/Web_List_to_do_01.md",
        "docs/plans/sprints/web-list-todo-01.md",
        "docs/plans/sprints",
    ),
    (
        "docs/dev/ssot/directus_schema_gd1.md",
        "docs/plans/specs/directus-schema-gd1.md",
        "docs/plans/specs",
    ),
    (
        "docs/dev/ssot/nuxt_view_model_0032.md",
        "docs/plans/specs/nuxt-view-model-0032.md",
        "docs/plans/specs",
    ),
    # Ops → plans/processes
    (
        "docs/ops/AI_GATEWAY_ADMIN_CHECKLIST.md",
        "docs/plans/processes/ai-gateway-admin-checklist.md",
        "docs/plans/processes",
    ),
    (
        "docs/ops/AI_GATEWAY_INSTRUCTIONS.md",
        "docs/plans/processes/ai-gateway-instructions.md",
        "docs/plans/processes",
    ),
    (
        "docs/ops/DIRECTUS_GOLDEN_STATE.md",
        "docs/plans/specs/directus-golden-state.md",
        "docs/plans/specs",
    ),
    (
        "docs/ops/DIRECTUS_PHASE6_HANDOVER.md",
        "docs/operations/sessions/directus-phase6-handover.md",
        "docs/operations/sessions",
    ),
    (
        "docs/ops/ENV_VARS_REFERENCE.md",
        "docs/plans/specs/env-vars-reference.md",
        "docs/plans/specs",
    ),
]


def get_token():
    """Get GCP identity token for Cloud Run auth."""
    result = subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def fetch_github_doc(client, token, path):
    """Fetch document content from GitHub API endpoint."""
    from urllib.parse import quote

    url = f"{BASE_URL}/api/docs/file?path={quote(path)}"
    try:
        resp = client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("content", data.get("body", ""))
        print(f"  FETCH ERROR {resp.status_code}: {path}")
        return None
    except Exception as e:
        print(f"  FETCH ERROR: {path} — {e}")
        return None


def upload_document(client, token, doc_id, parent_id, content, title):
    """Upload document to Firestore KB via REST API."""
    url = f"{BASE_URL}/documents"
    body = {
        "document_id": doc_id,
        "parent_id": parent_id,
        "content": {"mime_type": "text/markdown", "body": content},
        "metadata": {"title": title, "tags": ["migrated", "v3"]},
    }
    try:
        resp = client.post(
            url,
            json=body,
            timeout=15,
            headers={"Authorization": f"Bearer {token}", "X-API-Key": API_KEY},
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data.get("status", "ok"), data.get("revision", 0)
        if resp.status_code == 409:
            return "exists", 0
        print(f"  UPLOAD ERROR {resp.status_code}: {doc_id} — {resp.text[:200]}")
        return "error", 0
    except Exception as e:
        print(f"  UPLOAD ERROR: {doc_id} — {e}")
        return "error", 0


def main():
    token = get_token()
    if not token:
        print("ERROR: Could not get identity token")
        sys.exit(1)

    results = []
    success = 0
    skipped = 0
    errors = 0

    print(f"Migrating {len(MIGRATION_MAP)} documents...")
    print(f"Source: {BASE_URL}/api/docs/file")
    print(f"Target: {BASE_URL}/documents")
    print()

    with httpx.Client() as client:
        for old_path, new_path, parent_id in MIGRATION_MAP:
            title = (
                new_path.rsplit("/", 1)[-1].replace(".md", "").replace("-", " ").title()
            )
            print(f"  {old_path}")
            print(f"    → {new_path}")

            content = fetch_github_doc(client, token, old_path)
            if content is None:
                results.append((old_path, new_path, "FETCH_ERROR"))
                errors += 1
                continue

            if not content.strip():
                print("    SKIP: empty content")
                results.append((old_path, new_path, "EMPTY"))
                skipped += 1
                continue

            status, rev = upload_document(
                client, token, new_path, parent_id, content, title
            )
            if status == "exists":
                print("    SKIP: already exists")
                results.append((old_path, new_path, "EXISTS"))
                skipped += 1
            elif status in ("created", "ok"):
                print(f"    OK (rev {rev})")
                results.append((old_path, new_path, "MIGRATED"))
                success += 1
            else:
                results.append((old_path, new_path, "ERROR"))
                errors += 1

            time.sleep(0.2)  # Be nice to the API

    print(f"\n{'='*60}")
    print(f"Results: {success} migrated, {skipped} skipped, {errors} errors")
    print(f"{'='*60}")

    # Write migration log
    log_lines = ["# Migration Log: Old Docs → V3 Structure\n"]
    log_lines.append("Date: 2026-02-06 (WEB-50E)\n")
    log_lines.append(f"Total: {len(MIGRATION_MAP)} documents\n")
    log_lines.append(f"Migrated: {success}, Skipped: {skipped}, Errors: {errors}\n\n")
    log_lines.append("| Old Path | New V3 Path | Status |\n")
    log_lines.append("|----------|-------------|--------|\n")
    for old_p, new_p, status in results:
        log_lines.append(f"| `{old_p}` | `{new_p}` | {status} |\n")
    log_lines.append(
        "\nNote: Original documents NOT deleted. Both old and new paths remain accessible.\n"
    )

    log_content = "".join(log_lines)
    log_file = os.path.join(
        os.path.dirname(__file__), "..", "content", "migration-log.md"
    )
    with open(log_file, "w") as f:
        f.write(log_content)
    print(f"\nMigration log written to: {log_file}")

    # Also upload migration log to KB
    with httpx.Client() as client:
        log_status, _ = upload_document(
            client,
            token,
            "docs/archive/migration-log.md",
            "docs/archive",
            log_content,
            "Migration Log: Old Docs to V3",
        )
    print(f"Migration log uploaded to KB: {log_status}")


if __name__ == "__main__":
    main()
