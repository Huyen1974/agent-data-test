"""Directus Sync Adapter — transforms Agent Data events into Directus API calls.

Subscribes to the EventBus and syncs document CRUD to Directus
knowledge_documents collection. Async, fire-and-forget.

Field mapping (Agent Data → Directus):
  document_id           → file_path, source_id (agentdata:{doc_id})
  metadata.title        → title
  content.body          → content
  first paragraph       → summary (≤200 chars)
  metadata.tags         → tags
  metadata.status       → status
  path segment[0]       → category
  revision              → version_number
  derived slug          → slug
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_DIRECTUS_URL = os.getenv("DIRECTUS_URL", "http://incomex-directus:8055").rstrip("/")
_DIRECTUS_TOKEN = os.getenv("DIRECTUS_ADMIN_TOKEN", "")
_COLLECTION = "knowledge_documents"
_AGENT_DATA_INTERNAL = os.getenv(
    "AGENT_DATA_INTERNAL_URL", "http://localhost:8000"
).rstrip("/")
_API_KEY = os.getenv("API_KEY", "")

# Only sync docs matching these prefixes to knowledge_documents.
# operations/*, test/* etc. are NOT knowledge and should not pollute
# the knowledge_documents collection.
_SYNC_PREFIXES = ("knowledge/",)


def _enabled() -> bool:
    """Check if Directus sync is configured."""
    return bool(_DIRECTUS_TOKEN)


def _should_sync(doc_id: str) -> bool:
    """Only sync documents matching _SYNC_PREFIXES to knowledge_documents."""
    return any(doc_id.startswith(p) for p in _SYNC_PREFIXES)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_slug(doc_id: str) -> str:
    """Derive URL-safe slug from document_id."""
    slug = doc_id
    # Strip common prefixes
    for prefix in ("docs/", "knowledge/"):
        if slug.startswith(prefix):
            slug = slug[len(prefix) :]
            break
    slug = slug.removesuffix(".md")
    slug = slug.lower().replace("/", "-").replace(" ", "-").replace("_", "-")
    slug = slug.strip("-")
    return slug


def _make_summary(content: str) -> str:
    """Extract first non-heading, non-empty paragraph (≤200 chars)."""
    if not content:
        return ""
    lines = content.split("\n")
    in_frontmatter = False
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        # Track YAML frontmatter (--- delimited)
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        # Track code blocks
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        # Strip markdown formatting
        clean = re.sub(r"\*\*|__|\*|_|`", "", stripped)
        return clean[:200]
    return content[:200]


def _make_category(doc_id: str) -> str:
    """Extract category from first path segment."""
    parts = doc_id.split("/")
    # Skip 'knowledge/' prefix if present
    if parts and parts[0] == "knowledge" and len(parts) > 1:
        return parts[1]
    return parts[0] if parts else "other"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_DIRECTUS_TOKEN}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Directus API helpers
# ---------------------------------------------------------------------------
async def _find_by_source_id(
    client: httpx.AsyncClient, source_id: str
) -> dict[str, Any] | None:
    """Find a Directus record by source_id."""
    resp = await client.get(
        f"{_DIRECTUS_URL}/items/{_COLLECTION}",
        params={
            "filter[source_id][_eq]": source_id,
            "fields": "id,title,source_id,file_path",
            "limit": 1,
        },
        headers=_headers(),
    )
    if resp.status_code != 200:
        logger.warning("Directus lookup failed: %d %s", resp.status_code, resp.text)
        return None
    data = resp.json().get("data", [])
    return data[0] if data else None


async def _fetch_document(doc_id: str) -> dict[str, Any] | None:
    """Fetch full document from Agent Data /kb/get endpoint."""
    url = f"{_AGENT_DATA_INTERNAL}/kb/get/{doc_id}"
    headers = {}
    if _API_KEY:
        headers["X-API-Key"] = _API_KEY
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code != 200:
        logger.warning("Failed to fetch doc %s: %d", doc_id, resp.status_code)
        return None
    return resp.json()


def _build_directus_payload(
    doc_id: str, doc_data: dict[str, Any], *, is_create: bool = False
) -> dict[str, Any]:
    """Build Directus-format payload from Agent Data document."""
    content = doc_data.get("content", "")
    metadata = doc_data.get("metadata", {})
    title = metadata.get("title", "") or doc_id.split("/")[-1].replace(
        "-", " "
    ).removesuffix(".md")
    tags = metadata.get("tags", [])
    status = metadata.get("status", "published")
    revision = doc_data.get("revision", 1)

    payload: dict[str, Any] = {
        "title": title,
        "slug": _make_slug(doc_id),
        "file_path": doc_id,
        "source_id": f"agentdata:{doc_id}",
        "content": content,
        "summary": _make_summary(content),
        "status": (
            status if status in ("draft", "published", "archived") else "published"
        ),
        "category": _make_category(doc_id),
        "tags": tags if isinstance(tags, list) else [],
        "language": "vi",
        "visibility": "public",
        "is_folder": False,
        "is_current_version": True,
        "version_number": revision,
        "workflow_status": "published",
    }

    if is_create:
        payload["version_group_id"] = str(uuid.uuid4())

    return payload


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------
async def handle_document_created(payload: dict[str, Any]) -> dict[str, Any]:
    """Sync a created document to Directus."""
    doc_id = payload.get("document_id", "")
    if not doc_id or not _enabled():
        return {
            "status": "skipped",
            "reason": "not configured" if not _enabled() else "no doc_id",
        }

    # Fetch full document
    doc_data = await _fetch_document(doc_id)
    if not doc_data:
        return {"status": "error", "reason": f"could not fetch {doc_id}"}

    source_id = f"agentdata:{doc_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check if already exists (upsert)
        existing = await _find_by_source_id(client, source_id)
        if existing:
            # Update instead
            directus_id = existing["id"]
            directus_payload = _build_directus_payload(
                doc_id, doc_data, is_create=False
            )
            resp = await client.patch(
                f"{_DIRECTUS_URL}/items/{_COLLECTION}/{directus_id}",
                json=directus_payload,
                headers=_headers(),
            )
            return {
                "status": "updated" if resp.status_code < 400 else "error",
                "directus_id": directus_id,
                "http_status": resp.status_code,
            }
        else:
            # Create new
            directus_payload = _build_directus_payload(doc_id, doc_data, is_create=True)
            resp = await client.post(
                f"{_DIRECTUS_URL}/items/{_COLLECTION}",
                json=directus_payload,
                headers=_headers(),
            )
            result: dict[str, Any] = {
                "status": "created" if resp.status_code < 400 else "error",
                "http_status": resp.status_code,
            }
            if resp.status_code < 400:
                result["directus_id"] = resp.json().get("data", {}).get("id")
            else:
                result["error"] = resp.text[:500]
            return result


async def handle_document_updated(payload: dict[str, Any]) -> dict[str, Any]:
    """Sync an updated document to Directus."""
    doc_id = payload.get("document_id", "")
    if not doc_id or not _enabled():
        return {
            "status": "skipped",
            "reason": "not configured" if not _enabled() else "no doc_id",
        }

    doc_data = await _fetch_document(doc_id)
    if not doc_data:
        return {"status": "error", "reason": f"could not fetch {doc_id}"}

    source_id = f"agentdata:{doc_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        existing = await _find_by_source_id(client, source_id)
        if existing:
            directus_id = existing["id"]
            directus_payload = _build_directus_payload(
                doc_id, doc_data, is_create=False
            )
            resp = await client.patch(
                f"{_DIRECTUS_URL}/items/{_COLLECTION}/{directus_id}",
                json=directus_payload,
                headers=_headers(),
            )
            return {
                "status": "updated" if resp.status_code < 400 else "error",
                "directus_id": directus_id,
                "http_status": resp.status_code,
            }
        else:
            # Document exists in AD but not Directus — create it
            return await handle_document_created(payload)


async def handle_document_deleted(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove a document from Directus when deleted from Agent Data."""
    doc_id = payload.get("document_id", "")
    if not doc_id or not _enabled():
        return {
            "status": "skipped",
            "reason": "not configured" if not _enabled() else "no doc_id",
        }

    source_id = f"agentdata:{doc_id}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        existing = await _find_by_source_id(client, source_id)
        if not existing:
            return {"status": "not_found", "source_id": source_id}

        directus_id = existing["id"]
        resp = await client.delete(
            f"{_DIRECTUS_URL}/items/{_COLLECTION}/{directus_id}",
            headers=_headers(),
        )
        return {
            "status": "deleted" if resp.status_code < 400 else "error",
            "directus_id": directus_id,
            "http_status": resp.status_code,
        }


# ---------------------------------------------------------------------------
# Registration — plug into EventBus
# ---------------------------------------------------------------------------
_HANDLERS = {
    "document.created": handle_document_created,
    "document.updated": handle_document_updated,
    "document.deleted": handle_document_deleted,
}


async def directus_sync_listener(event_type: str, payload: dict[str, Any]) -> None:
    """Main listener: dispatches to appropriate handler.

    Only syncs documents with paths matching _SYNC_PREFIXES (default:
    ``knowledge/``). Other paths (operations/*, test/*) are skipped.
    """
    doc_id = payload.get("document_id", "")
    if not _should_sync(doc_id):
        logger.debug("Directus sync skip (not knowledge): %s", doc_id)
        return

    handler = _HANDLERS.get(event_type)
    if not handler:
        return
    try:
        result = await handler(payload)
        logger.info(
            "Directus sync %s %s → %s",
            event_type,
            doc_id,
            result.get("status", "unknown"),
        )
    except Exception as exc:
        logger.error(
            "Directus sync error %s %s: %s",
            event_type,
            doc_id,
            exc,
        )
