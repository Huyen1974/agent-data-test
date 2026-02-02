"""
Timer Callback Cloud Function (S1 + S5)

Handles:
- S1: 5-minute timer expiry for pending_human discussions
- S5: Total failure fallback when all AI agents fail to respond

Deployed as Cloud Function with Cloud Scheduler trigger (*/1 * * * *)
"""

import json
import logging
import os
from datetime import datetime, timezone

import functions_framework
import requests

# Configure structured logging
logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)

# Environment variables
DIRECTUS_URL = os.getenv("DIRECTUS_URL", "https://directus-test-pfne2mqwja-as.a.run.app")
DIRECTUS_ADMIN_TOKEN = os.getenv("DIRECTUS_ADMIN_TOKEN", "")
TIMER_MINUTES = int(os.getenv("TIMER_MINUTES", "5"))
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")


def get_directus_headers():
    """Get headers for Directus API calls."""
    headers = {"Content-Type": "application/json"}
    if DIRECTUS_ADMIN_TOKEN:
        headers["Authorization"] = f"Bearer {DIRECTUS_ADMIN_TOKEN}"
    return headers


def get_expired_discussions():
    """Query Directus for discussions that have exceeded the timer."""
    try:
        # Calculate the cutoff time (5 minutes ago)
        cutoff_time = datetime.now(timezone.utc)

        # Query pending_human discussions
        response = requests.get(
            f"{DIRECTUS_URL}/items/ai_discussions",
            params={
                "filter[status][_eq]": "pending_human",
                "fields": "*,drafter_id.first_name,drafter_id.email",
            },
            headers=get_directus_headers(),
        )

        if response.status_code != 200:
            logger.error(
                json.dumps(
                    {
                        "action": "get_expired_discussions",
                        "error": "Failed to fetch discussions",
                        "status_code": response.status_code,
                        "response": response.text[:500],
                    }
                )
            )
            return []

        discussions = response.json().get("data", [])

        # Filter discussions older than TIMER_MINUTES
        expired = []
        for disc in discussions:
            date_updated = disc.get("date_updated") or disc.get("date_created")
            if date_updated:
                updated_time = datetime.fromisoformat(
                    date_updated.replace("Z", "+00:00")
                )
                elapsed_minutes = (cutoff_time - updated_time).total_seconds() / 60

                if elapsed_minutes >= TIMER_MINUTES:
                    disc["_elapsed_minutes"] = elapsed_minutes
                    expired.append(disc)

        logger.info(
            json.dumps(
                {
                    "action": "get_expired_discussions",
                    "total_pending": len(discussions),
                    "expired_count": len(expired),
                }
            )
        )

        return expired

    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "action": "get_expired_discussions",
                    "error": str(e),
                }
            )
        )
        return []


def check_ai_failure(discussion_id: str) -> bool:
    """
    Check if all AI agents have failed to respond (S5).
    Returns True if this is a total failure scenario.
    """
    try:
        response = requests.get(
            f"{DIRECTUS_URL}/items/ai_discussion_comments",
            params={
                "filter[discussion_id][_eq]": discussion_id,
                "filter[comment_type][_neq]": "human",
                "filter[comment_type][_neq]": "human_supreme",
            },
            headers=get_directus_headers(),
        )

        if response.status_code != 200:
            return False

        comments = response.json().get("data", [])

        # If no AI comments at all after timer expires, it's a total failure
        ai_comments = [
            c for c in comments if c.get("comment_type") not in ["human", "human_supreme"]
        ]

        return len(ai_comments) == 0

    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "action": "check_ai_failure",
                    "discussion_id": discussion_id,
                    "error": str(e),
                }
            )
        )
        return False


def auto_approve_discussion(discussion: dict) -> dict:
    """Auto-approve a discussion that has expired without human intervention."""
    discussion_id = discussion.get("id")

    try:
        # Check for total AI failure first (S5)
        is_total_failure = check_ai_failure(discussion_id)

        if is_total_failure:
            # S5: Total failure - mark as stalled_error
            new_status = "stalled_error"
            comment_content = (
                "**SYSTEM ALERT** Tat ca AI khong phan hoi sau "
                f"{TIMER_MINUTES} phut. Yeu cau can thiep cua nguoi dung."
            )

            # Send alert if email configured
            if ALERT_EMAIL:
                send_failure_alert(discussion)
        else:
            # S1: Normal auto-approval
            new_status = "resolved"
            comment_content = (
                f"**AUTO-APPROVE** Discussion da duoc tu dong phe duyet "
                f"sau {TIMER_MINUTES} phut khong co phan hoi tu User."
            )

        # Update discussion status
        update_response = requests.patch(
            f"{DIRECTUS_URL}/items/ai_discussions/{discussion_id}",
            headers=get_directus_headers(),
            json={
                "status": new_status,
                "auto_approved": not is_total_failure,
                "timer_expired_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        if update_response.status_code not in [200, 204]:
            logger.error(
                json.dumps(
                    {
                        "action": "auto_approve_discussion",
                        "discussion_id": discussion_id,
                        "error": "Failed to update status",
                        "status_code": update_response.status_code,
                    }
                )
            )
            return {"id": discussion_id, "success": False, "error": "Update failed"}

        # Create system comment
        comment_response = requests.post(
            f"{DIRECTUS_URL}/items/ai_discussion_comments",
            headers=get_directus_headers(),
            json={
                "discussion_id": discussion_id,
                "comment_type": "human_supreme",
                "content": comment_content,
                "round": discussion.get("round", 1),
                "decision": "approve" if not is_total_failure else None,
            },
        )

        logger.info(
            json.dumps(
                {
                    "action": "auto_approve_discussion",
                    "discussion_id": discussion_id,
                    "new_status": new_status,
                    "is_total_failure": is_total_failure,
                    "elapsed_minutes": discussion.get("_elapsed_minutes"),
                    "success": True,
                }
            )
        )

        return {
            "id": discussion_id,
            "success": True,
            "new_status": new_status,
            "is_total_failure": is_total_failure,
        }

    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "action": "auto_approve_discussion",
                    "discussion_id": discussion_id,
                    "error": str(e),
                }
            )
        )
        return {"id": discussion_id, "success": False, "error": str(e)}


def send_failure_alert(discussion: dict):
    """Send alert email for total AI failure (S5)."""
    # This is a placeholder - implement actual email sending
    # Could use SendGrid, Mailgun, or Cloud Tasks with email function
    logger.warning(
        json.dumps(
            {
                "action": "send_failure_alert",
                "discussion_id": discussion.get("id"),
                "topic": discussion.get("topic"),
                "alert_email": ALERT_EMAIL,
                "message": "SUPER SESSION ALERT: Total AI Failure",
            }
        )
    )


@functions_framework.http
def handle(request):
    """
    Cloud Function entry point.

    Called by Cloud Scheduler every minute to check for expired discussions.
    """
    logger.info(
        json.dumps(
            {
                "action": "timer_callback_start",
                "timer_minutes": TIMER_MINUTES,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # Get expired discussions
    expired = get_expired_discussions()

    if not expired:
        return {
            "status": "ok",
            "message": "No expired discussions",
            "processed": 0,
        }

    # Process each expired discussion
    results = []
    for discussion in expired:
        result = auto_approve_discussion(discussion)
        results.append(result)

    success_count = sum(1 for r in results if r.get("success"))
    failure_count = sum(1 for r in results if r.get("is_total_failure"))

    logger.info(
        json.dumps(
            {
                "action": "timer_callback_complete",
                "total_processed": len(results),
                "success_count": success_count,
                "failure_count": failure_count,
                "results": results,
            }
        )
    )

    return {
        "status": "ok",
        "processed": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }
