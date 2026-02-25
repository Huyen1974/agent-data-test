#!/usr/bin/env python3
"""
Detect orphan vectors via Agent Data /kb/audit-sync API.

Calls the VPS Agent Data audit-sync endpoint (dry-run, no auto-heal)
which correctly compares Qdrant vector document_ids against Firestore
KB documents. Reports orphans (vectors without docs) and ghosts
(docs without vectors).

Environment:
  AGENT_DATA_URL   Base URL (default: https://vps.incomexsaigoncorp.vn/api)
  AGENT_DATA_KEY   API key for X-API-Key header

Exit codes:
  0 — Clean or advisory-only (orphans found but threshold not exceeded)
  1 — Error (API unreachable, auth failed, etc.)
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request
import urllib.error


def _print(msg: str) -> None:
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def _ssl_context() -> ssl.SSLContext | None:
    """Build SSL context, trying certifi first (macOS needs this)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None  # Ubuntu/CI has system certs


def main() -> int:
    base_url = os.getenv(
        "AGENT_DATA_URL", "https://vps.incomexsaigoncorp.vn/api"
    ).rstrip("/")
    api_key = os.getenv("AGENT_DATA_KEY", "").strip()

    if not api_key:
        _print("[ERROR] AGENT_DATA_KEY not set")
        return 1

    url = f"{base_url}/kb/audit-sync"
    body = json.dumps({"auto_heal": False}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
    )

    _print(f"[INFO] Calling {url}")

    try:
        ctx = _ssl_context()
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        _print(f"[ERROR] API returned HTTP {e.code}: {e.read().decode()[:500]}")
        return 1
    except Exception as e:
        _print(f"[ERROR] API request failed: {e}")
        return 1

    total_docs = data.get("total_documents", 0)
    total_vecs = data.get("total_vectors", 0)
    orphan_ids = data.get("orphan_vector_document_ids", [])
    orphan_count = data.get("orphan_count", len(orphan_ids))
    ghost_ids = data.get("documents_without_vectors", [])
    ghost_count = data.get("ghost_count", len(ghost_ids))
    status = data.get("status", "unknown")

    _print(f"[INFO] Documents: {total_docs}, Vectors: {total_vecs}")
    _print(f"[INFO] Status: {status}")

    if orphan_ids:
        for oid in orphan_ids:
            _print(f"[WARNING] Orphan vector (no Firestore doc): {oid}")
        _print(f"[INFO] Orphan vectors: {orphan_count}")
    else:
        _print("[INFO] No orphan vectors detected.")

    if ghost_ids:
        for gid in ghost_ids:
            _print(f"[WARNING] Ghost document (no Qdrant vector): {gid}")
        _print(f"[INFO] Ghost documents: {ghost_count}")

    if data.get("recommendations"):
        for rec in data["recommendations"]:
            _print(f"[INFO] Recommendation: {rec}")

    # Advisory only — never fail CI for data issues
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
