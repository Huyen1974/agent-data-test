import json
import logging
import os
import time

import requests

from gcp_secrets import SecretAccessError, get_secret

# Configure structured logging
logging.basicConfig(format="%(message)s")
logger = logging.getLogger(__name__)

# Environment variables
PROJECT_ID = os.getenv("PROJECT_ID", "github-chatgpt-ggcloud")
ACC = os.getenv("QDRANT_ACCOUNT_ID")
CLUS = os.getenv("QDRANT_CLUSTER_ID")
AUTO_STOP_MINUTES = int(os.getenv("AUTO_STOP_MINUTES", "60"))
QDRANT_API_BASE = os.getenv(
    "QDRANT_API_BASE", "https://api.cloud.qdrant.io/api/cluster/v1"
)
QDRANT_BACKUP_BASE = os.getenv(
    "QDRANT_BACKUP_BASE", "https://api.cloud.qdrant.io/api/cluster/backup/v1"
)
MGMT_SECRET_DEFAULT = "Qdrant_cloud_management_key"


def _load_mgmt_key() -> str | None:
    direct = os.getenv("QDRANT_MGMT_KEY")
    if direct:
        return direct
    secret_name = os.getenv("QDRANT_MGMT_KEY_SECRET_NAME", MGMT_SECRET_DEFAULT)
    if not secret_name:
        return None
    try:
        return get_secret(secret_name)
    except SecretAccessError as exc:  # pragma: no cover - network errors
        logger.error(
            json.dumps(
                {
                    "error": "secret_access_failed",
                    "secret_name": secret_name,
                    "details": str(exc),
                }
            )
        )
        return None


QDRANT_MGMT_KEY = _load_mgmt_key()


def _ensure_mgmt_key() -> str | None:
    global QDRANT_MGMT_KEY
    if not QDRANT_MGMT_KEY:
        QDRANT_MGMT_KEY = _load_mgmt_key()
    return QDRANT_MGMT_KEY


def call_mgmt(method, path, **kwargs):
    """Make API call to Qdrant Management API with appropriate base URL."""
    mgmt_key = _ensure_mgmt_key()
    if not mgmt_key:
        logger.error(json.dumps({"error": "missing_management_key"}))
        return None
    headers = {
        "Authorization": f"apikey {mgmt_key}",
        "Content-Type": "application/json",
    }

    # Choose base URL based on path
    if "backups" in path or "tasks/" in path:
        base = QDRANT_BACKUP_BASE
    else:
        base = QDRANT_API_BASE

    url = f"{base}/{path.lstrip('/')}"

    try:
        response = requests.request(method, url, headers=headers, **kwargs)
        logger.info(
            json.dumps(
                {
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "headers_sent": {
                        k: v[:20] + "..." if len(v) > 20 else v
                        for k, v in headers.items()
                    },
                }
            )
        )

        if response.status_code == 200:
            return response
        else:
            logger.error(
                json.dumps(
                    {
                        "error": "api_call_failed",
                        "method": method,
                        "url": url,
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "headers_sent": {
                            k: v[:20] + "..." if len(v) > 20 else v
                            for k, v in headers.items()
                        },
                    }
                )
            )
            return None
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "error": "api_call_exception",
                    "method": method,
                    "url": url,
                    "exception": str(e),
                    "headers_sent": {
                        k: v[:20] + "..." if len(v) > 20 else v
                        for k, v in headers.items()
                    },
                }
            )
        )
        return None


def current_phase(acc, clus):
    """Get current cluster phase."""
    resp = call_mgmt("GET", f"accounts/{acc}/clusters/{clus}")
    if resp:
        data = resp.json()
        return data["cluster"]["state"]["phase"]
    return None


def do_backup(acc, clus):
    """Create backup - backup API is synchronous, no polling needed."""
    start_time = time.time()

    # Create backup
    backup_payload = {
        "backup": {
            "account_id": acc,
            "cluster_id": clus,
            "name": f"auto-{int(time.time())}",
        }
    }

    resp = call_mgmt("POST", f"accounts/{acc}/backups", json=backup_payload)
    if not resp:
        logger.error(json.dumps({"error": "backup_creation_failed"}))
        return {"error": "backup_creation_failed"}

    response_data = resp.json()
    backup_id = response_data["backup"]["id"]

    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info(
        json.dumps(
            {
                "action": "backup_completed",
                "backup_id": backup_id,
                "elapsed_ms": elapsed_ms,
            }
        )
    )

    return backup_id


def get_access_token():
    """Get access token from Google metadata server."""
    try:
        metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
        headers = {"Metadata-Flavor": "Google"}
        response = requests.get(metadata_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        logger.error(json.dumps({"action": "token_error", "error": str(e)}))
        return None


def update_secret_manager(secret_name: str, secret_value: str) -> bool:
    """Update Secret Manager secret using REST API."""
    try:
        access_token = get_access_token()
        if not access_token:
            return False

        url = f"https://secretmanager.googleapis.com/v1/projects/{PROJECT_ID}/secrets/{secret_name}:addVersion"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        data = {"payload": {"data": secret_value.encode("utf-8").hex()}}

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            version_info = response.json()
            version_id = version_info.get("name", "unknown").split("/")[-1]
            logger.info(
                json.dumps(
                    {
                        "action": "secret_updated",
                        "secret_name": secret_name,
                        "version_id": version_id,
                    }
                )
            )
            return True
        else:
            logger.error(
                json.dumps(
                    {
                        "action": "secret_update_error",
                        "secret_name": secret_name,
                        "status_code": response.status_code,
                        "error": response.text,
                    }
                )
            )
            return False

    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "action": "secret_update_exception",
                    "secret_name": secret_name,
                    "error": str(e),
                }
            )
        )
        return False


def stop():
    """Stop cluster: backup -> suspend -> wait for SUSPENDED."""
    start_time = time.time()

    # Check current phase
    phase = current_phase(ACC, CLUS)
    if phase == "CLUSTER_PHASE_SUSPENDED":
        logger.info(
            json.dumps(
                {"action": "stop", "phase": phase, "message": "already_suspended"}
            )
        )
        return {"status": "ok", "phase": phase}

    # Create backup
    backup_result = do_backup(ACC, CLUS)
    if isinstance(backup_result, dict) and "error" in backup_result:
        return backup_result

    backup_id = backup_result

    # Suspend cluster
    suspend_resp = call_mgmt("POST", f"accounts/{ACC}/clusters/{CLUS}/suspend")
    if not suspend_resp:
        logger.error(json.dumps({"error": "suspend_failed"}))
        return {"error": "suspend_failed"}

    # Poll for SUSPENDED phase (10 min timeout)
    suspend_start = time.time()
    while time.time() - suspend_start < 600:  # 10 minutes
        phase = current_phase(ACC, CLUS)
        if phase == "CLUSTER_PHASE_SUSPENDED":
            break
        time.sleep(15)

    elapsed_ms = int((time.time() - start_time) * 1000)

    logger.info(
        json.dumps(
            {"action": "stop", "backup_id": backup_id, "phase": phase, "ms": elapsed_ms}
        )
    )

    return {"status": "ok", "phase": phase, "backup_id": backup_id}


def status():
    """Get cluster status and endpoint."""
    phase = current_phase(ACC, CLUS)
    if not phase:
        return {"error": "failed_to_get_phase"}

    # Get endpoint info
    resp = call_mgmt("GET", f"accounts/{ACC}/clusters/{CLUS}")
    endpoint = ""
    if resp:
        data = resp.json()
        endpoint_info = data.get("cluster", {}).get("state", {}).get("endpoint", {})
        endpoint = endpoint_info.get("url", "")

    return {"status": "ok", "phase": phase, "endpoint": endpoint}


def touch():
    """Update last hit timestamp in secret manager only."""
    current_time = str(int(time.time()))
    success = update_secret_manager("qdrant_idle_marker", current_time)

    logger.info(
        json.dumps(
            {
                "action": "touch",
                "last_hit": current_time,
                "secret_updated": success,
            }
        )
    )

    return {
        "status": "ok",
        "action": "touch",
        "last_hit": current_time,
        "secret_updated": success,
    }


def handle(request):
    """Cloud Function entry point."""

    # Debug environment variables (without exposing secrets)
    mgmt_key = _ensure_mgmt_key()
    logger.info(
        json.dumps(
            {
                "debug": "env_check",
                "acc_set": bool(ACC),
                "clus_set": bool(CLUS),
                "mgmt_key_set": bool(mgmt_key),
                "mgmt_key_len": len(mgmt_key) if mgmt_key else 0,
            }
        )
    )

    # Validate required environment variables
    if not all([ACC, CLUS, mgmt_key]):
        error_msg = "Missing required environment variables"
        logger.error(json.dumps({"error": error_msg}))
        return {"error": error_msg}, 500

    # Get action from query parameters
    action = request.args.get("action", "status")

    if action == "stop":
        return stop()
    elif action == "status":
        return status()
    elif action == "touch":
        return touch()
    else:
        return {"error": f"unknown_action: {action}"}, 400
