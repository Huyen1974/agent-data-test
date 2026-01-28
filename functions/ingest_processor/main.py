"""
Cloud Function (2nd gen) to process async ingest tasks from Pub/Sub.

Expects Pub/Sub messages with JSON payload: {"gcs_uri": "gs://bucket/path"}

Performs minimal ingestion tasks:
- Downloads the object (best-effort) to verify access
- Writes/updates Firestore metadata document with status "completed"

Notes:
- Vectorization can be integrated later by invoking the project agent if desired.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import functions_framework

try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None  # type: ignore

try:
    from google.cloud import storage  # type: ignore
except Exception:  # pragma: no cover
    storage = None  # type: ignore


logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI '{uri}', expected gs://<bucket>/<object>")
    path = uri[len("gs://") :]
    if "/" not in path:
        raise ValueError(f"Invalid GCS URI '{uri}', missing object path")
    bucket, blob = path.split("/", 1)
    if not bucket or not blob:
        raise ValueError(f"Invalid GCS URI '{uri}', empty bucket or object")
    return bucket, blob


def _metadata_doc_id(gcs_uri: str) -> str:
    try:
        return Path(_parse_gcs_uri(gcs_uri)[1]).name
    except Exception:
        # Fallback sanitized id
        return Path(gcs_uri).name or "unknown"


def _download_if_possible(gcs_uri: str) -> str | None:
    if storage is None:  # pragma: no cover
        logger.warning("google-cloud-storage not available; skipping download")
        return None
    try:
        bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        with tempfile.TemporaryDirectory(prefix="ingest_") as tmpdir:
            local = Path(tmpdir) / (Path(blob_name).name or "object")
            blob.download_to_filename(str(local))
            # Return path for potential future processing
            return str(local)
    except Exception as e:  # pragma: no cover
        logger.error(
            json.dumps({"event": "download_error", "uri": gcs_uri, "error": str(e)})
        )
        return None


def _write_metadata(gcs_uri: str, status: str = "completed") -> dict[str, Any]:
    collection = os.getenv("METADATA_COLLECTION", "metadata_test")
    data = {
        "source_uri": gcs_uri,
        "ingestion_status": status,
        "timestamp_utc": datetime.now(UTC).isoformat(),
    }
    if firestore is None:  # pragma: no cover
        logger.warning("google-cloud-firestore not available; skipping metadata write")
        return data
    try:
        doc_id = _metadata_doc_id(gcs_uri)
        db = firestore.Client()  # type: ignore[attr-defined]
        db.collection(collection).document(doc_id).set(data)
        return data
    except Exception as e:  # pragma: no cover
        logger.error(
            json.dumps({"event": "firestore_error", "uri": gcs_uri, "error": str(e)})
        )
        return data


@functions_framework.cloud_event
def handle(event):
    """Handle Pub/Sub events with CloudEvent signature."""
    try:
        # Pub/Sub message schema under CloudEvent
        msg = (event.data or {}).get("message", {})
        raw = msg.get("data")
        payload: dict[str, Any] = {}
        if raw:
            try:
                payload = json.loads(base64.b64decode(raw).decode("utf-8"))
            except Exception:
                payload = {
                    "gcs_uri": base64.b64decode(raw).decode("utf-8", errors="ignore")
                }

        gcs_uri = (
            payload.get("gcs_uri") or payload.get("uri") or payload.get("path") or ""
        ).strip()
        if not gcs_uri:
            logger.error(json.dumps({"event": "invalid_message", "payload": payload}))
            return

        # Best-effort download to verify access; ignore failures
        _download_if_possible(gcs_uri)

        # Persist metadata as completed
        doc = _write_metadata(gcs_uri, status="completed")
        logger.info(
            json.dumps({"event": "ingest_done", "gcs_uri": gcs_uri, "metadata": doc})
        )
    except Exception as e:  # pragma: no cover
        logger.error(json.dumps({"event": "handler_error", "error": str(e)}))
