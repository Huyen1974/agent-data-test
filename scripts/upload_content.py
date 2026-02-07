#!/usr/bin/env python3
"""Upload all content files (context packs, playbooks, status docs) to Agent Data."""

import sys
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
API_KEY = "test-key-local"
CONTENT_DIR = Path(__file__).parent.parent / "content"

DOCUMENTS = [
    # Context Packs
    (
        "docs/context-packs/governance.md",
        "context-packs/governance.md",
        "Context Pack: Governance",
        ["context-pack", "governance", "v3"],
    ),
    (
        "docs/context-packs/web-frontend.md",
        "context-packs/web-frontend.md",
        "Context Pack: Web Frontend",
        ["context-pack", "frontend", "v3"],
    ),
    (
        "docs/context-packs/infrastructure.md",
        "context-packs/infrastructure.md",
        "Context Pack: Infrastructure",
        ["context-pack", "infrastructure", "v3"],
    ),
    (
        "docs/context-packs/agent-data.md",
        "context-packs/agent-data.md",
        "Context Pack: Agent Data",
        ["context-pack", "agent-data", "v3"],
    ),
    (
        "docs/context-packs/directus.md",
        "context-packs/directus.md",
        "Context Pack: Directus",
        ["context-pack", "directus", "v3"],
    ),
    (
        "docs/context-packs/current-sprint.md",
        "context-packs/current-sprint.md",
        "Context Pack: Current Sprint",
        ["context-pack", "sprint", "v3"],
    ),
    # Playbooks
    (
        "docs/playbooks/assembly-task.md",
        "playbooks/assembly-task.md",
        "Playbook: Assembly Task",
        ["playbook", "frontend", "v3"],
    ),
    (
        "docs/playbooks/infrastructure-change.md",
        "playbooks/infrastructure-change.md",
        "Playbook: Infrastructure Change",
        ["playbook", "infrastructure", "v3"],
    ),
    (
        "docs/playbooks/investigation.md",
        "playbooks/investigation.md",
        "Playbook: Investigation",
        ["playbook", "investigation", "v3"],
    ),
    (
        "docs/playbooks/new-integration.md",
        "playbooks/new-integration.md",
        "Playbook: New Integration",
        ["playbook", "integration", "v3"],
    ),
    # Status Documents
    (
        "docs/status/system-inventory.md",
        "status/system-inventory.md",
        "System Inventory",
        ["status", "inventory", "v3"],
    ),
    (
        "docs/status/dot-tools-registry.md",
        "status/dot-tools-registry.md",
        "DOT Tools Registry",
        ["status", "tools", "v3"],
    ),
    (
        "docs/status/connection-matrix.md",
        "status/connection-matrix.md",
        "Connection Matrix",
        ["status", "connections", "v3"],
    ),
]


def upload_or_update(client, doc_id, file_path, title, tags):
    """Upload a document, or update if it already exists."""
    content = file_path.read_text(encoding="utf-8")
    parent_id = "/".join(doc_id.split("/")[:-1])
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    # Try create
    body = {
        "document_id": doc_id,
        "parent_id": parent_id,
        "content": {"mime_type": "text/markdown", "body": content},
        "metadata": {"title": title, "tags": tags},
    }
    resp = client.post(f"{BASE_URL}/documents", json=body, headers=headers, timeout=30)

    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"  + {doc_id} — created (rev {data.get('revision', 1)})")
        return True

    if resp.status_code == 409:
        # Already exists — update
        update_body = {
            "document_id": doc_id,
            "patch": {
                "content": {"mime_type": "text/markdown", "body": content},
                "metadata": {"title": title, "tags": tags},
            },
            "update_mask": ["content", "metadata"],
        }
        resp2 = client.put(
            f"{BASE_URL}/documents/{doc_id}",
            json=update_body,
            headers=headers,
            timeout=30,
        )
        if resp2.status_code == 200:
            data = resp2.json()
            print(f"  ~ {doc_id} — updated (rev {data.get('revision', '?')})")
            return True
        print(f"  ! {doc_id} — update failed: {resp2.status_code} {resp2.text[:200]}")
        return False

    print(f"  ! {doc_id} — create failed: {resp.status_code} {resp.text[:200]}")
    return False


def main():
    success = 0
    failed = 0

    with httpx.Client() as client:
        # Check server is up
        try:
            r = client.get(f"{BASE_URL}/health", timeout=5)
            print(f"Agent Data: {r.json().get('status', 'unknown')}\n")
        except Exception as e:
            print(f"ERROR: Cannot reach Agent Data at {BASE_URL}: {e}")
            sys.exit(1)

        for doc_id, rel_path, title, tags in DOCUMENTS:
            file_path = CONTENT_DIR / rel_path
            if not file_path.exists():
                print(f"  ? {doc_id} — file not found: {file_path}")
                failed += 1
                continue
            if upload_or_update(client, doc_id, file_path, title, tags):
                success += 1
            else:
                failed += 1

    print(f"\nResults: {success} success, {failed} failed, {success + failed} total")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
