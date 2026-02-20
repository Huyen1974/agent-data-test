#!/usr/bin/env python3
"""Reconcile Directus tasks/comments with Agent Data.

Compares Directus records with Agent Data documents and backfills
any missing items. Designed to run as a periodic cron job.

Usage: python3 reconcile-tasks.py [--dry-run]
"""
import urllib.request
import json
import time
import sys
import os
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


def directus_api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{DIRECTUS}{path}", data=body, headers=headers, method=method)
    resp = urllib.request.urlopen(req)
    raw = resp.read()
    return json.loads(raw) if raw else {}


def ad_exists(doc_id):
    """Check if a document exists in Agent Data."""
    headers = {"X-API-Key": AD_KEY}
    req = urllib.request.Request(f"{AD}/kb/get/{doc_id}", headers=headers)
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        return bool(data and data.get("content"))
    except urllib.error.HTTPError:
        return False


def ad_upsert(payload):
    """Create/update a document in Agent Data."""
    headers = {"X-API-Key": AD_KEY, "Content-Type": "application/json"}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f"{AD}/documents?upsert=true", data=body, headers=headers, method="POST")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def main():
    log("=== Directus ↔ Agent Data Reconciliation ===")
    if DRY_RUN:
        log("DRY RUN mode — no changes will be made")

    # Auth
    try:
        result = directus_api("POST", "/auth/login", {"email": DIRECTUS_EMAIL, "password": DIRECTUS_PASSWORD})
        TOKEN = result["data"]["access_token"]
    except Exception as e:
        log(f"ERROR: Directus auth failed: {e}")
        sys.exit(1)

    # Get tasks
    tasks = directus_api("GET", "/items/tasks?limit=-1&fields=id,name,status,priority,assigned_to,description,content_targets,content_rules,content_checklist,content_plan,content_prompt,content_reports,content_verify,content_test&sort=id", token=TOKEN)
    all_tasks = tasks["data"]
    log(f"Directus tasks: {len(all_tasks)}")

    # Get comments
    comments = directus_api("GET", "/items/task_comments?limit=-1&fields=id,task_id,tab_scope,agent_type,action,content&sort=id", token=TOKEN)
    all_comments = comments["data"]
    log(f"Directus comments: {len(all_comments)}")

    # Check tasks
    missing_tasks = 0
    synced_tasks = 0
    for task in all_tasks:
        tid = task["id"]
        doc_id = f"operations/tasks/task-{tid}"
        if ad_exists(doc_id):
            synced_tasks += 1
        else:
            missing_tasks += 1
            log(f"  MISSING task-{tid}: {task.get('name', '?')}")
            if not DRY_RUN:
                name = task.get("name") or "Untitled"
                status = task.get("status") or ""
                priority = task.get("priority") or ""
                assigned = task.get("assigned_to") or ""
                desc = task.get("description") or ""
                sections = [f"# {name}", f"\n**Status:** {status}", f"**Priority:** {priority}", f"**Assigned to:** {assigned}", f"\n## Description\n{desc}"]
                for field in ["content_targets", "content_rules", "content_checklist", "content_plan", "content_prompt", "content_reports", "content_verify", "content_test"]:
                    label = field.replace("content_", "").capitalize()
                    val = task.get(field) or ""
                    sections.append(f"\n## {label}\n{val}")
                body = "\n".join(sections)
                try:
                    ad_upsert({
                        "document_id": doc_id,
                        "parent_id": "root",
                        "content": {"mime_type": "text/markdown", "body": body},
                        "metadata": {
                            "title": name, "status": status, "priority": priority,
                            "assigned_to": assigned, "source": "directus", "collection": "tasks"
                        },
                        "is_human_readable": True
                    })
                    log(f"    SYNCED task-{tid}")
                    time.sleep(1)
                except Exception as e:
                    log(f"    ERROR syncing task-{tid}: {e}")

    # Check comments
    missing_comments = 0
    synced_comments = 0
    for comment in all_comments:
        cid = comment["id"]
        doc_id = f"operations/tasks/comments/comment-{cid}"
        if ad_exists(doc_id):
            synced_comments += 1
        else:
            missing_comments += 1
            log(f"  MISSING comment-{cid}")
            if not DRY_RUN:
                agent_type = comment.get("agent_type") or "unknown"
                task_id = comment.get("task_id") or "?"
                tab_scope = comment.get("tab_scope") or ""
                action = comment.get("action") or ""
                content = comment.get("content") or ""
                body = f"## Comment by {agent_type}\n\n**Task:** #{task_id}\n**Tab:** {tab_scope}\n**Action:** {action}\n\n{content}"
                try:
                    ad_upsert({
                        "document_id": doc_id,
                        "parent_id": "root",
                        "content": {"mime_type": "text/markdown", "body": body},
                        "metadata": {
                            "title": f"Comment #{cid} on Task #{task_id}",
                            "task_id": str(task_id), "tab_scope": tab_scope,
                            "agent_type": agent_type, "action": action,
                            "source": "directus", "collection": "task_comments"
                        },
                        "is_human_readable": True
                    })
                    log(f"    SYNCED comment-{cid}")
                    time.sleep(1)
                except Exception as e:
                    log(f"    ERROR syncing comment-{cid}: {e}")

    # Summary
    log("=== Summary ===")
    log(f"Tasks:    {synced_tasks} synced, {missing_tasks} missing" + (" (fixed)" if missing_tasks and not DRY_RUN else ""))
    log(f"Comments: {synced_comments} synced, {missing_comments} missing" + (" (fixed)" if missing_comments and not DRY_RUN else ""))

    if missing_tasks == 0 and missing_comments == 0:
        log("All in sync!")
    elif DRY_RUN:
        log(f"Would sync {missing_tasks + missing_comments} items (run without --dry-run to fix)")


if __name__ == "__main__":
    main()
