from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any

import google.auth
from google.auth.transport.requests import AuthorizedSession, Request

API = "https://artifactregistry.googleapis.com/v1"


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _parse_time(s: str) -> dt.datetime:
    # Handles formats like 2025-09-07T10:13:35.094079Z
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s)


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


def _create_tag(
    sess: AuthorizedSession,
    project: str,
    location: str,
    repo: str,
    package: str,
    tag: str,
    version_name: str,
) -> None:
    parent = f"projects/{project}/locations/{location}/repositories/{repo}/packages/{package}"
    url = f"{API}/{parent}/tags?tagId={tag}"
    body = {"version": version_name}
    resp = sess.post(url, json=body)
    # If already exists, ignore
    if resp.status_code in (200, 201):
        return
    if resp.status_code == 409:
        return
    resp.raise_for_status()


def handle(request):  # Cloud Functions v2 HTTP entrypoint
    project = os.getenv(
        "PROJECT_ID", os.getenv("GCP_PROJECT", "github-chatgpt-ggcloud")
    )
    location = os.getenv("REGION", "asia-southeast1")
    repo = os.getenv("AR_REPO", "agent-data-test-images")
    package = os.getenv("AR_PACKAGE", "agent-data-test")
    important_tags = {
        t.strip()
        for t in os.getenv("IMPORTANT_TAGS", "latest,stable").split(",")
        if t.strip()
    }
    ttl_days = int(os.getenv("TTL_DAYS", "14"))

    sess = _authed_session()
    versions = _list_versions(sess, project, location, repo, package)

    threshold = _utcnow() - dt.timedelta(days=ttl_days)
    stale_marked: list[tuple[str, str]] = []
    kept: int = 0

    for v in versions:
        name = v.get("name", "")  # full resource name
        ctime = v.get("createTime") or v.get("updateTime")
        if not ctime:
            continue
        created = _parse_time(ctime)
        tags = []
        for t in v.get("relatedTags", []) or []:
            # relatedTags elements have 'name' like 'latest' or 'sha-abc'
            tn = t.get("tag") or t.get("name")
            if tn:
                tags.append(tn)
        if important_tags.intersection(tags):
            kept += 1
            continue
        if created <= threshold:
            # tag format: stale-YYYYMMDD-<short>
            short = name.split("/")[-1].split("@").pop().replace(":", "_")[:12]
            tag = f"stale-{created.strftime('%Y%m%d')}-{short}"
            try:
                _create_tag(sess, project, location, repo, package, tag, name)
                stale_marked.append((name, tag))
            except Exception as e:  # pragma: no cover
                # Best effort
                stale_marked.append((name, f"ERROR:{e}"))
        else:
            kept += 1

    return (
        json.dumps(
            {
                "checked": len(versions),
                "kept": kept,
                "stale_tagged": len(stale_marked),
                "details": stale_marked[:50],
            }
        ),
        200,
        {"Content-Type": "application/json"},
    )
