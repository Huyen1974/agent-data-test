import subprocess
import time

import pytest
import requests

try:
    from google.cloud import firestore  # type: ignore
except ImportError:
    firestore = None  # S109: Firestore removed, tests will be skipped

import agent_data.main as _main  # noqa: F401

# Import server and agent modules to ensure coverage collection for package code
import agent_data.server as _server  # noqa: F401

# Mark this as an end-to-end test; exclude from unit-only CI runs
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def setup_and_teardown_gcs():
    # Upload fixture to GCS (best-effort; do not fail test if upload fails)
    subprocess.run(["python", "scripts/e2e_gcs_setup.py", "upload"], check=False)

    # Start API server
    server_process = subprocess.Popen(
        [
            "uvicorn",
            "agent_data.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to boot
    time.sleep(10)

    yield

    # Teardown: terminate server and cleanup GCS
    server_process.terminate()
    subprocess.run(["python", "scripts/e2e_gcs_setup.py", "cleanup"], check=False)


def test_full_ingestion_async_flow(setup_and_teardown_gcs):
    # Step 1: Ask the server to ingest from GCS (async)
    ingest_uri = "gs://huyen1974-agent-data-knowledge-test/e2e_doc.txt"
    r1 = requests.post(
        "http://127.0.0.1:8000/ingest",
        json={"text": ingest_uri},
        timeout=30,
    )
    assert r1.status_code == 202

    # Step 2: Poll Firestore for metadata completion
    db = firestore.Client()
    doc_ref = db.collection("metadata_test").document("e2e_doc.txt")
    deadline = time.time() + 90
    while time.time() < deadline:
        doc = doc_ref.get()
        if getattr(doc, "exists", False):
            data = doc.to_dict() or {}
            if data.get("ingestion_status") == "completed":
                return
        time.sleep(2)
    raise AssertionError("Metadata with status 'completed' not found in time")
