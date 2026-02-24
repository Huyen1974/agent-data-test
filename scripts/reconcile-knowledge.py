#!/usr/bin/env python3
"""Reconcile Agent Data knowledge docs with Directus knowledge_documents.

Compares Agent Data knowledge/* documents with Directus knowledge_documents
and backfills any missing items. Designed to run as a periodic cron job
inside the agent-data Docker container (no external dependencies).

Usage: python3 reconcile-knowledge.py [--dry-run]
"""

import json
import os
import re
import sys
import time
import urllib.request
import uuid
from datetime import datetime

DIRECTUS = os.getenv("DIRECTUS_URL", "http://incomex-directus:8055")
AD = os.getenv("AGENT_DATA_URL", "http://localhost:8000")
AD_KEY = os.getenv("AGENT_DATA_API_KEY", "C38FE9FA-2BC6-4FBB-BA0C-981E8FB89450")
DIRECTUS_EMAIL = os.getenv("DIRECTUS_EMAIL", "admin@example.com")
DIRECTUS_PASSWORD = os.getenv("DIRECTUS_PASSWORD", "Directus@2026SecureNew!")

DRY_RUN = "--dry-run" in sys.argv


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def api(method, url, data=None, headers=None):
    """Generic HTTP request using urllib (no external deps)."""
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    resp = urllib.request.urlopen(req)
    raw = resp.read()
    return json.loads(raw) if raw else {}


def directus_login():
    """Authenticate with Directus and return access token."""
    result = api(
        "POST",
        f"{DIRECTUS}/auth/login",
        {"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD},
    )
    return result["data"]["access_token"]


def get_ad_knowledge_docs():
    """Fetch all knowledge/* non-folder docs from Agent Data."""
    result = api("GET", f"{AD}/kb/list", headers={"X-API-Key": AD_KEY})
    items = result.get("items", [])
    docs = []
    for item in items:
        doc_id = item.get("document_id", "")
        if doc_id.startswith("knowledge/") and not item.get("is_folder"):
            docs.append(item)
    return docs


def get_directus_knowledge_docs(token):
    """Fetch all knowledge_documents from Directus."""
    url = (
        f"{DIRECTUS}/items/knowledge_documents"
        "?limit=-1"
        "&fields=id,title,file_path,source_id,status,is_folder,content,date_updated"
    )
    result = api("GET", url, headers={"Authorization": f"Bearer {token}"})
    return result.get("data", [])


def get_ad_doc_content(doc_id):
    """Fetch full content of a single doc from Agent Data."""
    result = api("GET", f"{AD}/kb/get/{doc_id}", headers={"X-API-Key": AD_KEY})
    return result.get("content", ""), result.get("metadata", {})


def make_slug(file_path):
    """Generate slug from file_path: strip .md, replace / with -."""
    slug = file_path
    if slug.endswith(".md"):
        slug = slug[:-3]
    slug = slug.replace("/", "-")
    # Remove leading dash
    slug = slug.lstrip("-")
    return slug


def make_title(metadata, file_path):
    """Extract title from metadata or derive from file_path."""
    title = metadata.get("title", "")
    if title:
        return title
    # Derive from filename
    name = file_path.split("/")[-1]
    if name.endswith(".md"):
        name = name[:-3]
    return name.replace("-", " ").replace("_", " ")


def make_summary(content, max_len=200):
    """Create summary from first non-heading line of content."""
    if not content:
        return ""
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("---"):
            clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
            clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
            if len(clean) > max_len:
                clean = clean[:max_len] + "..."
            return clean
    return ""


def create_directus_doc(token, doc_id, content, metadata):
    """Create a knowledge_documents record in Directus."""
    title = make_title(metadata, doc_id)
    slug = make_slug(doc_id)
    summary = make_summary(content)

    payload = {
        "title": title,
        "slug": slug,
        "file_path": doc_id,
        "source_id": f"agentdata:{doc_id}",
        "content": content or "",
        "summary": summary,
        "status": "published",
        "category": "knowledge",
        "language": "vi",
        "visibility": "public",
        "is_folder": False,
        "is_current_version": True,
        "version_number": 1,
        "workflow_status": "published",
        "version_group_id": str(uuid.uuid4()),
    }

    result = api(
        "POST",
        f"{DIRECTUS}/items/knowledge_documents",
        payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return result


def update_directus_doc(token, dx_id, content, metadata):
    """Update an existing knowledge_documents record in Directus."""
    title = make_title(metadata, "")
    summary = make_summary(content)

    payload = {
        "content": content or "",
        "summary": summary,
        "status": "published",
    }
    if title:
        payload["title"] = title

    result = api(
        "PATCH",
        f"{DIRECTUS}/items/knowledge_documents/{dx_id}",
        payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    return result


def main():
    log("=== Agent Data → Directus Knowledge Reconciliation ===")
    if DRY_RUN:
        log("DRY RUN mode — no changes will be made")

    # Auth
    try:
        token = directus_login()
        log("Directus auth: OK")
    except Exception as e:
        log(f"ERROR: Directus auth failed: {e}")
        sys.exit(1)

    # Fetch both sides
    ad_docs = get_ad_knowledge_docs()
    log(f"Agent Data knowledge docs: {len(ad_docs)}")

    dx_docs = get_directus_knowledge_docs(token)
    log(f"Directus knowledge_documents: {len(dx_docs)}")

    # Build lookup: file_path → directus record
    dx_by_path = {}
    for d in dx_docs:
        fp = d.get("file_path", "")
        if fp:
            dx_by_path[fp] = d

    # Compare
    created = 0
    skipped = 0
    errors = 0
    dx_only = []

    for ad_doc in ad_docs:
        doc_id = ad_doc["document_id"]
        dx_rec = dx_by_path.pop(doc_id, None)

        if dx_rec is None:
            # Missing in Directus → CREATE
            log(f"  MISSING: {doc_id}")
            if not DRY_RUN:
                try:
                    content, metadata = get_ad_doc_content(doc_id)
                    create_directus_doc(token, doc_id, content, metadata)
                    log("    CREATED in Directus")
                    created += 1
                    time.sleep(0.5)
                except Exception as e:
                    log(f"    ERROR creating: {e}")
                    errors += 1
            else:
                created += 1
        else:
            skipped += 1

    # Remaining in dx_by_path = Directus-only docs (not in AD)
    for fp, rec in dx_by_path.items():
        if not rec.get("is_folder"):
            dx_only.append(fp)
            log(f"  DIRECTUS-ONLY: {fp} (id={rec.get('id')})")

    # Summary
    log("=== Summary ===")
    log(f"Agent Data docs:  {len(ad_docs)}")
    log(f"Directus docs:    {len(dx_docs)}")
    log(f"Already synced:   {skipped}")
    log(f"Created:          {created}" + (" (would create)" if DRY_RUN else ""))
    log(f"Errors:           {errors}")
    log(f"Directus-only:    {len(dx_only)}")

    if dx_only:
        log("Directus-only docs (not in AD):")
        for fp in sorted(dx_only):
            log(f"  - {fp}")

    if created == 0 and errors == 0:
        log("All in sync!")
    elif DRY_RUN:
        log(f"Would create {created} docs (run without --dry-run to fix)")


if __name__ == "__main__":
    main()
