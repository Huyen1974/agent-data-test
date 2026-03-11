import os
import subprocess
import sys
import time

import pytest
import requests
try:
    from google.cloud import firestore  # type: ignore
except ImportError:
    firestore = None  # S109: Firestore removed

pytestmark = pytest.mark.e2e


def _get_cloud_run_url() -> str:
    project = os.getenv("GCP_PROJECT_ID", "github-chatgpt-ggcloud")
    region = os.getenv("GCP_REGION", "asia-southeast1")
    service = os.getenv("GCP_RUN_SERVICE", "agent-data-test")
    cmd = [
        "gcloud",
        "run",
        "services",
        "describe",
        service,
        "--platform",
        "managed",
        "--region",
        region,
        "--project",
        project,
        "--format",
        "value(status.url)",
    ]
    url = subprocess.check_output(cmd, text=True).strip()
    assert url.startswith("http"), f"Unexpected Cloud Run URL: {url}"
    return url


@pytest.mark.skipif(
    not os.getenv("E2E_LIVE_ENABLE"), reason="Live E2E disabled (set E2E_LIVE_ENABLE=1)"
)
def test_ingestion_creates_firestore_metadata():
    # Allow disabling Firestore verification if runner has limited IAM
    if os.getenv("E2E_LIVE_REQUIRE_FIRESTORE") == "0":
        pytest.skip("Firestore verification disabled by env")
    bucket = "huyen1974-agent-data-knowledge-test"
    blob = "e2e_doc.txt"
    gcs_uri = f"gs://{bucket}/{blob}"

    # Upload test fixture to GCS
    subprocess.run(
        [sys.executable, "scripts/e2e_gcs_setup.py", "upload"],
        check=True,
        text=True,
    )

    db = firestore.Client()
    doc_id = blob
    collection = "metadata_test"
    doc_ref = db.collection(collection).document(doc_id)

    # Ensure clean state before test
    try:
        doc_ref.delete()
    except Exception:
        pass

    try:
        base_url = _get_cloud_run_url().rstrip("/")
        ingest_url = f"{base_url}/ingest"

        resp = requests.post(ingest_url, json={"text": gcs_uri}, timeout=60)
        assert (
            resp.status_code == 202
        ), f"Unexpected status: {resp.status_code}, body={resp.text}"

        # Poll Firestore for metadata document
        deadline = time.time() + 90
        found = False
        doc = None
        while time.time() < deadline:
            doc = doc_ref.get()
            if getattr(doc, "exists", False):
                found = True
                break
            time.sleep(2)

        assert found, "Metadata document not found in Firestore within timeout"
        data = doc.to_dict() if doc else {}
        assert (
            data.get("ingestion_status") == "completed"
        ), f"Unexpected metadata: {data}"
    finally:
        # Teardown: delete Firestore doc and remove GCS object
        try:
            doc_ref.delete()
        except Exception:
            pass
        subprocess.run(
            [sys.executable, "scripts/e2e_gcs_setup.py", "cleanup"],
            check=False,
            text=True,
        )
