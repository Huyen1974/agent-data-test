"""Orphan Vector Check ( skeleton ) — Plan V12 ID 2.4

Compares vector IDs in Qdrant against document IDs in Firestore to detect
orphaned vectors (present in Qdrant but missing in Firestore).

This is a placeholder implementation (skeleton). It wires up clients if
available, but returns mocked IDs for both sides so the script can run in
any environment. Replace the placeholder logic with real queries in a
follow‑up task.
"""

from __future__ import annotations

import os

from gcp_secrets import SecretAccessError, get_secret

try:  # Optional imports — script remains runnable without these
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore

try:
    from qdrant_client import QdrantClient  # type: ignore
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore


def _resolve_qdrant_key() -> str:
    direct = os.getenv("QDRANT_API_KEY")
    if direct:
        return direct
    secret_name = os.getenv("QDRANT_API_SECRET_NAME", "Qdrant_agent_data_N1D8R2vC0_5")
    if not secret_name:
        return ""
    try:
        return get_secret(secret_name)
    except SecretAccessError:  # pragma: no cover - diagnostics only
        return ""


def get_qdrant_ids(client: object) -> set[str]:
    """Return the set of vector IDs currently in Qdrant (placeholder).

    Args:
        client: A `QdrantClient` instance (unused in the placeholder).

    Returns:
        A set of IDs representing vectors in Qdrant.
    """

    # TODO: Replace with real Qdrant queries (e.g., scroll/list points)
    return {"vector_1", "vector_2", "orphan_vector_3"}


def get_firestore_ids(client: object) -> set[str]:
    """Return the set of document IDs present in Firestore (placeholder).

    Args:
        client: A Firestore client instance (unused in the placeholder).

    Returns:
        A set of IDs representing documents tracked in Firestore.
    """

    # TODO: Replace with real Firestore collection scan
    return {"vector_1", "vector_2"}


def main() -> int:
    # CI nudge: trigger Lint Only workflow after lint fixes
    # Initialize Qdrant client if library and env are available
    qdrant_url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_HOST")
    qdrant_api_key = _resolve_qdrant_key()
    qdrant_client = None
    if QdrantClient is not None and qdrant_url and qdrant_api_key:
        try:  # prefer REST for portability
            qdrant_client = QdrantClient(
                url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False
            )
        except Exception:
            qdrant_client = None

    # Initialize Firestore client if library available
    fs_client = None
    if firestore is not None:
        try:
            fs_client = firestore.Client()  # type: ignore[attr-defined]
        except Exception:
            fs_client = None

    # Placeholder: fetch IDs via mocked helpers
    q_ids = get_qdrant_ids(qdrant_client)
    fs_ids = get_firestore_ids(fs_client)

    # Orphans are vectors present in Qdrant but missing in Firestore
    orphans = sorted(q_ids - fs_ids)

    if orphans:
        print("Orphan vectors detected:")
        for oid in orphans:
            print(f"- {oid}")
    else:
        print("No orphan vectors found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
