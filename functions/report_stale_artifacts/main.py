from __future__ import annotations

import json
import os
from typing import Any

import google.auth
import requests
from google.auth.transport.requests import AuthorizedSession, Request
from google.cloud import secretmanager  # type: ignore

API = "https://artifactregistry.googleapis.com/v1"


def _authed_session() -> AuthorizedSession:
    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    if not creds.valid:
        creds.refresh(Request())
    return AuthorizedSession(creds)


def _list_versions(
    sess: AuthorizedSession, project: str, location: str, repo: str, package: str
) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    parent = f"projects/{project}/locations/{location}/repositories/{repo}/packages/{package}"
    url = f"{API}/{parent}/versions"
    page_token = None
    while True:
        params = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token
        resp = sess.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        versions.extend(data.get("versions", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return versions


def _get_secret(project: str, name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    res = client.access_secret_version(
        request={"name": f"projects/{project}/secrets/{name}/versions/latest"}
    )
    return res.payload.data.decode("utf-8")


def handle(request):
    project = os.getenv(
        "PROJECT_ID", os.getenv("GCP_PROJECT", "github-chatgpt-ggcloud")
    )
    location = os.getenv("REGION", "asia-southeast1")
    repo = os.getenv("AR_REPO", "agent-data-test-images")
    package = os.getenv("AR_PACKAGE", "agent-data-test")
    slack_secret = os.getenv("SLACK_SECRET_NAME", "SLACK_WEBHOOK_URL")

    sess = _authed_session()
    versions = _list_versions(sess, project, location, repo, package)

    stale_versions: list[dict[str, Any]] = []
    for v in versions:
        tags = []
        for t in v.get("relatedTags", []) or []:
            tn = t.get("tag") or t.get("name")
            if tn:
                tags.append(tn)
        if any(str(t).startswith("stale-") for t in tags):
            stale_versions.append({"name": v.get("name", ""), "tags": tags})

    summary = {
        "total": len(versions),
        "stale": len(stale_versions),
        "items": stale_versions[:50],
    }

    # Send Slack notification if webhook available
    try:
        webhook = _get_secret(project, slack_secret)
        text = f"Artifact Registry Stale Report: {summary['stale']} stale of {summary['total']} total.\n"
        for it in summary["items"]:
            text += f"- {it['name']} tags={','.join(it['tags'])}\n"
        requests.post(webhook, json={"text": text}, timeout=10)
    except Exception:
        pass

    return json.dumps(summary), 200, {"Content-Type": "application/json"}
