"""
Create v3 directory structure in Agent Data knowledge base.
Creates 19 folder README documents via POST /documents.
"""

import json
import sys
import httpx

BASE_URL = "http://localhost:8000"
API_KEY = "test-key-local"

FOLDERS = [
    # docs/foundation
    ("docs/foundation/README.md", "docs", "Foundation", "Core rules and architecture that rarely change."),
    ("docs/foundation/constitution/README.md", "docs/foundation", "Constitution", "Immutable project principles and values."),
    ("docs/foundation/laws/README.md", "docs/foundation", "Laws", "Coding standards, naming conventions, and mandatory rules."),
    ("docs/foundation/architecture/README.md", "docs/foundation", "Architecture", "System architecture decisions and diagrams."),

    # docs/plans
    ("docs/plans/README.md", "docs", "Plans", "Forward-looking plans and specifications."),
    ("docs/plans/blueprints/README.md", "docs/plans", "Blueprints", "High-level feature blueprints and designs."),
    ("docs/plans/sprints/README.md", "docs/plans", "Sprints", "Sprint plans, goals, and tracking."),
    ("docs/plans/processes/README.md", "docs/plans", "Processes", "Standard operating procedures and workflows."),
    ("docs/plans/specs/README.md", "docs/plans", "Specs", "Detailed technical specifications."),

    # docs/operations
    ("docs/operations/README.md", "docs", "Operations", "Day-to-day operational records."),
    ("docs/operations/sessions/README.md", "docs/operations", "Sessions", "Work session reports and logs."),
    ("docs/operations/research/README.md", "docs/operations", "Research", "Research findings and analysis."),
    ("docs/operations/decisions/README.md", "docs/operations", "Decisions", "Decision records (ADRs)."),
    ("docs/operations/lessons/README.md", "docs/operations", "Lessons", "Lessons learned and retrospectives."),

    # Top-level folders
    ("docs/context-packs/README.md", "docs", "Context Packs", "Pre-built context bundles for AI agent onboarding."),
    ("docs/playbooks/README.md", "docs", "Playbooks", "Step-by-step guides for common tasks."),
    ("docs/status/README.md", "docs", "Status", "Current project status and dashboards."),
    ("docs/discussions/README.md", "docs", "Discussions", "Open discussions and proposals."),
    ("docs/templates/README.md", "docs", "Templates", "Document templates for consistent formatting."),
]


def create_folder_doc(path: str, parent_id: str, title: str, description: str) -> dict:
    """Create a folder README document."""
    content = f"# {title}\n\n{description}\n"
    body = {
        "document_id": path,
        "parent_id": parent_id,
        "content": {"mime_type": "text/markdown", "body": content},
        "metadata": {"title": title, "tags": ["folder", "v3-structure"]},
    }
    return body


def main():
    created = 0
    failed = 0
    skipped = 0

    with httpx.Client(timeout=30.0) as client:
        for path, parent_id, title, description in FOLDERS:
            body = create_folder_doc(path, parent_id, title, description)
            try:
                resp = client.post(
                    f"{BASE_URL}/documents",
                    json=body,
                    headers={"X-API-Key": API_KEY},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    rev = data.get("revision", "?")
                    print(f"  PASS  {path} (rev {rev})")
                    created += 1
                elif resp.status_code == 409:
                    print(f"  SKIP  {path} (already exists)")
                    skipped += 1
                else:
                    print(f"  FAIL  {path} -> HTTP {resp.status_code}: {resp.text[:200]}")
                    failed += 1
            except Exception as e:
                print(f"  FAIL  {path} -> {e}")
                failed += 1

    print(f"\nDone: {created} created, {skipped} skipped, {failed} failed (total {len(FOLDERS)})")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
