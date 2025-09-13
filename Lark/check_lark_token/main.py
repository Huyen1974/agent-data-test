import requests
import json
import time
import logging
from google.cloud import secretmanager
from flask import jsonify
import functions_framework

# Thiết lập logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cấu hình
PROJECT_ID = "github-chatgpt-ggcloud"
SECRET_NAME = "lark-access-token-sg"
LARK_API_URL = "https://open.larksuite.com/open-apis/im/v1/messages?receive_id_type=chat_id"
LARK_GENERATE_TOKEN_URL = "https://asia-southeast1-github-chatgpt-ggcloud.cloudfunctions.net/generate_lark_token"
TEST_CHAT_ID = "oc_028305c6332e7eca363c9b707d07b3e5"
MAX_RETRIES = 6

# Khởi tạo client Secret Manager
client = secretmanager.SecretManagerServiceClient()

def get_lark_token():
    secret_version_name = client.secret_version_path(PROJECT_ID, SECRET_NAME, "latest")
    try:
        response = client.access_secret_version(request={"name": secret_version_name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error retrieving token from Secret Manager: {str(e)}")
        return None

def validate_lark_token(token):
    if not token:
        logger.warning("No token provided for validation")
        return False
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {
        "receive_id": TEST_CHAT_ID,
        "msg_type": "text",
        "content": json.dumps({"text": "Token validation test"})
    }
    try:
        response = requests.post(LARK_API_URL, headers=headers, json=body, timeout=10)
        logger.info(f"Validate response status: {response.status_code}, body: {response.text}")
        try:
            data = response.json()
            if data.get("code") == 0:
                logger.info("Token validation successful")
                return True
            else:
                logger.error(f"Lark API error: code={data.get('code')}, msg={data.get('msg')}")
                return False
        except json.JSONDecodeError:
            logger.error(f"Lark API returned invalid JSON: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending validation message: {str(e)}")
        return False

def call_generate_lark_token():
    try:
        response = requests.get(LARK_GENERATE_TOKEN_URL, timeout=10)
        logger.info(f"Generate-lark-token response status: {response.status_code}, body: {response.text}")
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Error calling generate-lark-token: {str(e)}")
        return False

@functions_framework.http
def check_lark_token(request):
    log = ""
    logger.info("Start check_lark_token")

    for attempt in range(MAX_RETRIES):
        token = get_lark_token()
        if token is None:
            log += f"Attempt {attempt + 1}: Failed to retrieve token from Secret Manager.\n"
            logger.warning(f"Attempt {attempt + 1}: Failed to retrieve token from Secret Manager")
            if attempt < MAX_RETRIES - 1:
                time.sleep(3)
            continue
        if validate_lark_token(token):
            logger.info("Token is valid")
            return jsonify({"status": "OK", "message": "Token is valid", "token": token})

        log += f"Attempt {attempt + 1}: Token invalid. Calling generate-lark-token...\n"
        logger.info(f"Attempt {attempt + 1}: Token invalid. Calling generate-lark-token...")
        if not call_generate_lark_token():
            log += "  Failed to call generate-lark-token.\n"
            logger.warning("Failed to call generate-lark-token")
        if attempt < MAX_RETRIES - 1:
            time.sleep(3)

    log += "ERROR: Token still invalid after multiple attempts and regeneration.\n"
    logger.error("Token still invalid after multiple attempts and regeneration")
    return jsonify({"status": "ERROR", "message": f"Token invalid after {MAX_RETRIES} attempts."}), 500
