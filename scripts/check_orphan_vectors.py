#!/usr/bin/env python3
"""
Detect orphan vectors between Qdrant and Firestore.

Logic:
- Read Qdrant endpoint from env (QDRANT_URL) and API key via ADC (Secret Manager with env override).
- Connect to Qdrant collection `test_documents` and list all point IDs.
- Connect to Firestore collection `metadata_test` and list all document IDs.
- For IDs present in Qdrant but missing in Firestore, print [WARNING] lines.
- Always exit with code 0 (advisory only).

Intended to be run in CI with GCP Workload Identity Federation (ADC available).
"""

from __future__ import annotations

import os
import sys

from gcp_secrets import SecretAccessError, get_secret


def _load_qdrant_key() -> tuple[str, str]:
    direct = os.getenv("QDRANT_API_KEY", "").strip()
    if direct:
        return direct, "[INFO] Using Qdrant API key from environment override"
    secret_name = os.getenv("QDRANT_API_SECRET_NAME", "Qdrant_agent_data_N1D8R2vC0_5")
    if not secret_name:
        return "", "[WARNING] Qdrant secret name not configured"
    try:
        return (
            get_secret(secret_name).strip(),
            "[INFO] Qdrant API key fetched via Secret Manager",
        )
    except SecretAccessError as exc:  # pragma: no cover - network errors
        return "", f"[WARNING] Failed to load Qdrant API key: {exc}"


def _print(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def qdrant_ids(collection: str = "test_documents") -> tuple[set[str], str]:
    """Return (ids, note) from Qdrant, or (empty set, warning)."""
    url = os.getenv("QDRANT_URL", "").strip()
    key, note = _load_qdrant_key()
    if not url:
        return set(), "[WARNING] Qdrant URL not provided; skipping Qdrant scan"
    if not key:
        return set(), note
    try:
        from qdrant_client import QdrantClient  # type: ignore

        client = QdrantClient(url=url, api_key=key, prefer_grpc=False)
        ids: set[str] = set()
        offset = None
        while True:
            points, next_page = client.scroll(
                collection_name=collection,
                with_payload=False,
                with_vectors=False,
                limit=2048,
                offset=offset,
            )
            if not points:
                break
            for p in points:
                # QdrantClient returns models.Record with .id field
                pid = getattr(p, "id", None)
                if pid is None:
                    continue
                ids.add(str(pid))
            if not next_page:
                break
            offset = next_page
        return ids, f"[INFO] Qdrant scanned: {len(ids)} ids from '{collection}'"
    except Exception as e:  # pragma: no cover
        return set(), f"[WARNING] Qdrant scan failed: {e}"


def firestore_ids(collection: str = "metadata_test") -> tuple[set[str], str]:
    """Return (ids, note) from Firestore, or (empty set, warning)."""
    try:
        from google.cloud import firestore  # type: ignore

        db = firestore.Client()
        ids: set[str] = set()
        for ref in db.collection(collection).list_documents(page_size=2000):
            ids.add(ref.id)
        return ids, f"[INFO] Firestore scanned: {len(ids)} ids from '{collection}'"
    except Exception as e:  # pragma: no cover
        return set(), f"[WARNING] Firestore scan failed: {e}"


def main() -> int:
    q_ids, q_note = qdrant_ids()
    f_ids, f_note = firestore_ids()
    _print(q_note)
    _print(f_note)

    # Orphans: in Qdrant but not in Firestore
    orphans = sorted(q_ids - f_ids)
    if orphans:
        for oid in orphans:
            _print(f"[WARNING] Orphan vector id without metadata: {oid}")
        _print(f"[INFO] Total orphan vectors detected: {len(orphans)}")
    else:
        _print("[INFO] No orphan vectors detected.")

    # Always advisory; do not fail CI
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
