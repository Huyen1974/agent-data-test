"""Cloud Function để tạo và lưu trữ token truy cập ứng dụng Lark trong Secret Manager."""

import logging
import os

import functions_framework
import requests
from flask import jsonify
from google.cloud import secretmanager
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

# --- Cấu hình ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "github-chatgpt-ggcloud")
APP_SECRET_ID = os.environ.get("APP_SECRET_ID", "lark-app-secret-sg")
APP_ID = os.environ.get("LARK_APP_ID", "cli_a785d634437a502f")
NEW_TOKEN_SECRET_ID = os.environ.get("NEW_TOKEN_SECRET_ID", "lark-access-token-sg")
LARK_TOKEN_URL = os.environ.get(
    "LARK_TOKEN_URL",
    "https://open.larksuite.com/open-apis/auth/v3/app_access_token/internal/",
)
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "10"))

# --- Thiết lập logging ---
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

# --- Khởi tạo client ---
client = secretmanager.SecretManagerServiceClient()


def get_latest_secret_version(secret_id, project_id):
    """Lấy phiên bản mới nhất của secret từ Secret Manager."""
    secret_version_name = client.secret_version_path(project_id, secret_id, "latest")
    try:
        response = client.access_secret_version(request={"name": secret_version_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error("Lỗi khi lấy secret %s: %s", secret_id, str(e))
        return None


def save_secret(secret_id, project_id, new_token):
    """Lưu token mới vào Secret Manager."""
    parent = client.secret_path(project_id, secret_id)
    try:
        response = client.add_secret_version(
            request={"parent": parent, "payload": {"data": new_token.encode("UTF-8")}}
        )
        logger.info("Đã lưu phiên bản mới: %s", response.name)
        return True
    except Exception as e:
        logger.error("Lỗi khi lưu secret %s: %s", secret_id, str(e))
        return False


def delete_old_secret_versions(secret_id, project_id):
    """Xóa các phiên bản cũ của secret, giữ lại phiên bản mới nhất."""
    parent = client.secret_path(project_id, secret_id)
    try:
        versions = list(client.list_secret_versions(request={"parent": parent}))
        versions.sort(key=lambda v: v.create_time, reverse=True)
        if len(versions) > 1:
            for version in versions[1:]:
                if version.state == secretmanager.SecretVersion.State.ENABLED:
                    client.disable_secret_version(request={"name": version.name})
                    client.destroy_secret_version(request={"name": version.name})
                    logger.info("Đã xóa phiên bản cũ: %s", version.name)
    except Exception as e:
        logger.error("Lỗi khi xóa phiên bản cũ của secret %s: %s", secret_id, str(e))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    reraise=True,
)
def call_lark_api(url, payload, headers):
    """Gọi API Lark để tạo token với logic retry."""
    logger.info("Gọi API Lark: %s", url)
    response = requests.post(
        url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response


@functions_framework.http
def generate_lark_token(request):
    """Tạo token truy cập ứng dụng Lark mới và lưu vào Secret Manager."""
    logger.info("Bắt đầu xử lý request tạo token mới")

    # Lấy app_secret
    app_secret = get_latest_secret_version(APP_SECRET_ID, PROJECT_ID)
    if not app_secret:
        logger.error("Không tìm thấy app_secret")
        return jsonify({"status": "ERROR", "message": "Không tìm thấy app_secret"}), 400

    # Gọi API Lark
    headers = {"Content-Type": "application/json"}
    payload = {"app_id": APP_ID, "app_secret": app_secret}
    try:
        response = call_lark_api(LARK_TOKEN_URL, payload, headers)
        data = response.json()
        if data.get("code") != 0 or not data.get("app_access_token"):
            logger.error(
                "Response không hợp lệ từ API Lark: %s",
                data.get("msg", "Unknown error"),
            )
            return (
                jsonify(
                    {
                        "status": "ERROR",
                        "message": data.get("msg", "Response không hợp lệ từ API Lark"),
                    }
                ),
                500,
            )

        app_access_token = data["app_access_token"]

        # Lưu token mới
        if not save_secret(NEW_TOKEN_SECRET_ID, PROJECT_ID, app_access_token):
            logger.error("Không thể lưu token mới")
            return (
                jsonify({"status": "ERROR", "message": "Không thể lưu token mới"}),
                500,
            )

        # Xóa phiên bản cũ
        delete_old_secret_versions(NEW_TOKEN_SECRET_ID, PROJECT_ID)

        logger.info("Tạo và lưu token mới thành công")
        return (
            jsonify({"status": "OK", "message": "Tạo và lưu token mới thành công"}),
            200,
        )

    except requests.RequestException as e:
        logger.error("Lỗi khi gọi API Lark: %s", str(e))
        return (
            jsonify({"status": "ERROR", "message": f"Lỗi khi gọi API Lark: {str(e)}"}),
            500,
        )
    except Exception as e:
        logger.error("Lỗi không xác định: %s", str(e))
        return (
            jsonify({"status": "ERROR", "message": f"Lỗi không xác định: {str(e)}"}),
            500,
        )


# FORCE DEPLOY
# trigger redeploy after delete
