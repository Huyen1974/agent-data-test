import functions_framework
import requests
import json
import os
import logging
from datetime import datetime
import random
import string
from typing import Dict, Any, Tuple, Optional

from google.cloud import firestore
from google.cloud import secretmanager
from google.cloud.firestore_v1.base_query import FieldFilter

# --- Constants ---
# Infrastructure details (Consider moving to environment variables for flexibility)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT", "chatgpt-db-project") # Use env var if set
GCP_REGION = os.environ.get("FUNCTION_REGION", "asia-southeast1") # Use env var if set
FIRESTORE_PROJECT_ID = GCP_PROJECT_ID
FIRESTORE_DATABASE = "test-default"
FIRESTORE_COLLECTION = "conversations"
SECRET_MANAGER_PROJECT_ID = "github-chatgpt-ggcloud"
# LARK_TOKEN_SECRET_ID = "lark-access-token-sg" # Removed as token is now fetched from URL
OPENAI_API_KEY_SECRET_ID = "openai-api-key-sg"
TARGET_LARK_CHAT_ID = "oc_028305c6332e7eca363c9b707d07b3e5"

# Lark API Endpoint
LARK_SEND_MESSAGE_URL = "https://open.larksuite.com/open-apis/im/v1/messages?receive_id_type=chat_id"
CHECK_LARK_TOKEN_URL = "https://asia-southeast1-chatgpt-db-project.cloudfunctions.net/check_lark_token" # Added URL constant

# OpenAI API Details
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4" # Or specify a more detailed model like gpt-4-turbo-preview
OPENAI_SYSTEM_PROMPT = "Bạn là trợ lý thông minh xử lý các yêu cầu bảng, cột, công thức. Hãy hỏi lại nếu thiếu thông tin. Tối đa 3 lần hỏi."
MAX_CLARIFICATION_ATTEMPTS = 3

# Confirmation Keywords (Vietnamese)
CONFIRMATION_KEYWORDS = ["ok", "oke", "okee", "đồng ý", "dong y", "yes", "y", "ukm", "uh", "ừ"]

# --- Initialize Clients ---
try:
    db = firestore.Client(project=FIRESTORE_PROJECT_ID, database=FIRESTORE_DATABASE)
    secret_manager_client = secretmanager.SecretManagerServiceClient()
    logging.info(f"Firestore and Secret Manager clients initialized successfully for project {FIRESTORE_PROJECT_ID}.")
except Exception as e:
    logging.error(f"Failed to initialize Google Cloud clients: {e}", exc_info=True)
    # Critical error, function might not work
    db = None
    secret_manager_client = None

# --- Logging Setup ---
# Configure logging level (e.g., INFO, DEBUG)
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def get_secret(project_id, secret_id, version_id="latest") -> Optional[str]:
    """Fetches a secret from Google Secret Manager."""
    if not secret_manager_client:
        logging.error("Secret Manager client not initialized.")
        return None
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    try:
        response = secret_manager_client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        logging.info(f"Successfully retrieved secret: {secret_id}")
        return secret_value
    except Exception as e:
        logging.error(f"Failed to access secret {name}: {e}", exc_info=True)
        return None

def get_lark_token_from_url(url: str) -> Optional[str]:
    """Fetches Lark token from the check_lark_token Cloud Function URL."""
    # Unit Test Idea: Mock requests.get, return mock response (success/failure/invalid JSON)
    #               Assert correct URL and handling of different responses.
    logging.info(f"Attempting to fetch Lark token from URL: {url}")
    try:
        response = requests.get(url, timeout=30) # Increased timeout to 30 seconds
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        token_data = response.json()
        token = token_data.get("token") # Assuming the key is 'token'
        
        if token:
            logging.info(f"Successfully fetched Lark token from URL.")
            return token
        else:
            logging.error(f"'token' key not found in response JSON from {url}. Response: {response.text}")
            return None
    except requests.exceptions.Timeout:
         logging.error(f"Timeout error fetching Lark token from {url}.", exc_info=True)
         return None
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error fetching Lark token from {url}: {e}", exc_info=True)
        if e.response is not None:
             logging.error(f"Check Lark Token URL Response Status: {e.response.status_code}, Body: {e.response.text}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON response from {url}: {e}. Response: {response.text}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"Unexpected error fetching Lark token from {url}: {e}", exc_info=True)
        return None

def send_lark_message(chat_id: str, content: str, token: str) -> bool:
    """Sends a message to the specified Lark chat."""
    # Unit Test Idea: Mock requests.post, assert correct URL, headers, payload,
    #               and return True/False based on mocked response.
    if not token:
        logging.error("Lark token is missing, cannot send message.")
        return False
    if not chat_id:
         logging.error("Chat ID is missing, cannot send message.")
         return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8", # Ensure UTF-8
    }
    # Content must be a JSON string containing a 'text' field for text messages
    payload = json.dumps({
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    })

    logging.debug(f"Sending Lark message to {chat_id}: {content[:100]}...")
    try:
        response = requests.post(LARK_SEND_MESSAGE_URL, headers=headers, data=payload, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()
        if response_data.get("code") == 0:
            logging.info(f"Message sent successfully to chat {chat_id}.")
            return True
        else:
            # Log Lark's specific error
            lark_code = response_data.get('code')
            lark_msg = response_data.get('msg')
            logging.error(f"Failed to send Lark message. Lark Code: {lark_code}, Msg: {lark_msg}")
            return False
    except requests.exceptions.Timeout:
         logging.error(f"Timeout error sending Lark message to {chat_id}.", exc_info=True)
         return False
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP error sending Lark message: {e}", exc_info=True)
        if e.response is not None:
             logging.error(f"Lark send API Response Status: {e.response.status_code}, Body: {e.response.text}")
        return False
    except json.JSONDecodeError as e:
         logging.error(f"Error decoding JSON response from Lark send API: {e}. Response: {response.text}", exc_info=True)
         return False

def generate_conversation_id() -> str:
    """Generates a unique conversation ID."""
    # Unit Test Idea: Assert format is conv_YYYYMMDD_HHMMSS_random(6).
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"conv_{timestamp_str}_{random_str}"

def call_openai_api(api_key: str, system_prompt: str, messages: list) -> Tuple[Optional[str], Optional[str]]:
    """Calls the OpenAI Chat Completion API. Returns (response_text, error_message)."""
    # Unit Test Idea: Mock requests.post, assert correct URL, headers, payload.
    #               Return predefined responses or exceptions.
    if not api_key:
        logging.error("OpenAI API key is missing.")
        return None, "OpenAI API key not configured."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "temperature": 0.7, # Adjust as needed
    }

    logging.debug(f"Calling OpenAI API with model {OPENAI_MODEL}. Messages: {messages}")
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60) # Increased timeout
        response.raise_for_status()
        result = response.json()

        # Check for valid response structure
        if "choices" in result and len(result["choices"]) > 0 and \
           "message" in result["choices"][0] and "content" in result["choices"][0]["message"]:
            bot_response = result["choices"][0]["message"]["content"].strip()
            logging.info(f"OpenAI response received successfully.")
            logging.debug(f"OpenAI response content: {bot_response[:100]}...")
            return bot_response, None
        else:
            logging.error(f"Unexpected OpenAI response format: {result}")
            return None, "Invalid response format from OpenAI."
    except requests.exceptions.Timeout:
        logging.error("OpenAI API request timed out.")
        return None, "OpenAI request timed out."
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling OpenAI API: {e}", exc_info=True)
        error_details = f"Failed to communicate with OpenAI: {e}"
        if e.response is not None:
             logging.error(f"OpenAI API Response Status: {e.response.status_code}")
             logging.error(f"OpenAI API Response Body: {e.response.text}")
             error_details += f" (Status: {e.response.status_code})"
        return None, error_details
    except json.JSONDecodeError as e:
         logging.error(f"Error decoding JSON response from OpenAI API: {e}. Response: {response.text}", exc_info=True)
         return None, "Error decoding OpenAI response."

def function_comment(parsed_command: str):
    """Placeholder function to log the final parsed command."""
    # Unit Test Idea: Assert logging.info was called with the correct message.
    # logging.info(f"--- function_comment --- Received command for processing: {parsed_command}")
    print(f"function_comment processed command: {parsed_command}") # Replaced logging.info
    # In the future, this could trigger a Workflow or another service.

def handle_command(parsed_command: str):
    """Handles the confirmed command by calling function_comment."""
    # Unit Test Idea: Assert function_comment was called with parsed_command.
    # logging.info(f"--- handle_command --- Triggering action for: {parsed_command}")
    print(f"Calling handle_command with command: {parsed_command}") # Replaced logging.info
    function_comment(parsed_command)
    # Add any other post-processing logic here if needed.

def update_conversation(conversation_id: str, updates: Dict[str, Any]) -> bool:
    """Updates a conversation document in Firestore."""
    # Unit Test Idea: Mock db.collection().document().update().
    #               Assert correct doc_id and updates (including timestamp).
    if not db:
        logging.error("Firestore client not initialized. Cannot update conversation.")
        return False
    if not conversation_id:
        logging.error("Conversation ID is missing. Cannot update conversation.")
        return False

    try:
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(conversation_id)
        # Ensure timestamp is updated on every modification
        updates['timestamp'] = firestore.SERVER_TIMESTAMP
        doc_ref.update(updates)
        logging.info(f"Conversation {conversation_id} updated successfully in Firestore.")
        logging.debug(f"Firestore update data for {conversation_id}: {updates}")
        return True
    except Exception as e:
        logging.error(f"Error updating Firestore document {conversation_id}: {e}", exc_info=True)
        return False

def create_conversation(data: Dict[str, Any]) -> Optional[str]:
    """Creates a new conversation document in Firestore."""
    # Unit Test Idea: Mock db.collection().document().set(). Assert generated ID format
    #               and data (including timestamp) passed to set().
    if not db:
        logging.error("Firestore client not initialized. Cannot create conversation.")
        return None
    try:
        conversation_id = generate_conversation_id()
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(conversation_id)
        data['timestamp'] = firestore.SERVER_TIMESTAMP # Set initial timestamp
        doc_ref.set(data)
        logging.info(f"Conversation {conversation_id} created successfully in Firestore.")
        logging.debug(f"Firestore create data for {conversation_id}: {data}")
        return conversation_id
    except Exception as e:
        logging.error(f"Error creating Firestore document: {e}", exc_info=True)
        return None

def get_pending_conversation(chat_id: str) -> Optional[firestore.DocumentSnapshot]:
    """Retrieves the latest pending conversation for a given chat ID."""
    # Unit Test Idea: Mock db.collection().where()...stream(). Assert query parameters.
    #               Return a mock DocumentSnapshot or empty list.
    if not db:
        logging.error("Firestore client not initialized. Cannot get pending conversation.")
        return None
    if not chat_id:
         logging.error("Chat ID is missing. Cannot query pending conversation.")
         return None

    try:
        logging.debug(f"Querying Firestore for pending conversation for chat_id: {chat_id}")
        query = db.collection(FIRESTORE_COLLECTION) \
                  .where(filter=FieldFilter('chat_id', '==', chat_id)) \
                  .where(filter=FieldFilter('labels.Status', '==', 'Pending')) \
                  .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                  .limit(1)
        docs = list(query.stream()) # Use list() to execute and get results
        if docs:
            logging.info(f"Found pending conversation for chat {chat_id}: {docs[0].id}")
            return docs[0] # Return the DocumentSnapshot object
        else:
            logging.info(f"No pending conversation found for chat {chat_id}.")
            return None
    except Exception as e:
        logging.error(f"Error querying Firestore for pending conversation: {e}", exc_info=True)
        return None

# --- Refactored Logic Handlers ---

def handle_challenge(request_json: Dict[str, Any]) -> Any:
    """Handles Lark's webhook challenge request."""
    # Unit Test Idea: Provide sample challenge JSON, assert correct response format.
    challenge_code = request_json.get('challenge')
    if not challenge_code:
         logging.error("Challenge request received, but 'challenge' key is missing.")
         # Return error response consistent with other errors
         # Use standard tuple return format
         return (
             json.dumps({'status': 'ERROR', 'message': 'Missing challenge code in request'}),
             400,
             {'Content-Type': 'application/json'}
         )

    logging.info(f"Received Lark challenge request. Responding with challenge code.")
    # Standardized JSON response for challenge using tuple format
    return (
        json.dumps({'challenge': challenge_code}),
        200,
        {'Content-Type': 'application/json'}
    )

def parse_lark_event(request_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parses V1 or V2 Lark event JSON and extracts message details.

    Returns:
        A dictionary containing extracted fields ('chat_id', 'message_id', 
        'user_message', 'sender_id', 'message_type') or None if parsing fails 
        or message type is unsupported/irrelevant.
    """
    # Unit Test Idea: Provide sample V1/V2 JSON payloads (text, image, missing keys).
    #               Assert correct extraction or None return.
    extracted_data = {
        'chat_id': None,
        'message_id': None,
        'user_message': None, # Will store extracted text content
        'sender_id': None,
        'message_type': None
    }

    try:
        header = request_json.get('header', {}) # V2 Event structure
        schema = request_json.get('schema') # V1 Event structure or header in V2
        event = request_json.get('event', {}) # Present in both V1 and V2 (usually)

        if not event:
             logging.error("Event data missing in request JSON.")
             return None

        message = event.get('message')
        if not message:
            logging.error("Message data missing in event.")
            return None

        # --- Event Structure Handling (V2 Preferred) ---
        is_v2 = schema == "2.0" or (header and header.get("event_type") == "im.message.receive_v1")

        if is_v2:
            logging.debug("Parsing as Lark Event Schema V2")
            extracted_data['chat_id'] = message.get('chat_id')
            extracted_data['message_id'] = message.get('message_id')
            extracted_data['message_type'] = message.get("message_type")
            sender = event.get('sender', {}).get('sender_id', {})
            extracted_data['sender_id'] = sender.get('open_id')

            if extracted_data['message_type'] == "text":
                content_str = message.get('content', '{}')
                try:
                    content = json.loads(content_str)
                    extracted_data['user_message'] = content.get('text', '').strip()
                    # Log message content potentially containing special chars/emojis
                    logging.debug(f"V2 Text content extracted: {extracted_data['user_message'][:100]}...")
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode V2 message content JSON: {content_str}")
            elif extracted_data['message_type']:
                 # Log unsupported types but continue parsing other fields
                 logging.info(f"Received unsupported message_type (V2): {extracted_data['message_type']} from chat {extracted_data['chat_id']}")
            else:
                logging.warning("Message type missing in V2 event.")

        # --- Fallback/Assume V1 Structure ---
        elif 'event' in request_json: # Check if it looks like a V1 structure
            logging.debug("Parsing as Lark Event Schema V1 (or fallback)")
            extracted_data['chat_id'] = event.get('chat_id') # V1 might have chat_id directly in event
            if not extracted_data['chat_id']:
                 extracted_data['chat_id'] = message.get('chat_id') # Or in message

            extracted_data['message_id'] = message.get('message_id')
            extracted_data['message_type'] = message.get('type') # V1 uses 'type'

            sender_info = event.get('sender', {}) # Path might differ
            sender_user_info = sender_info.get('sender_id') # V1 structure might differ
            if isinstance(sender_user_info, dict):
                 extracted_data['sender_id'] = sender_user_info.get('open_id')
            # Add more specific V1 sender parsing if needed

            if extracted_data['message_type'] == "text":
                 content_str = message.get('content', '{}')
                 try:
                     # V1 text content is often JSON like {'text':'...'}
                     content = json.loads(content_str)
                     extracted_data['user_message'] = content.get('text', '').strip()
                     logging.debug(f"V1 Text content extracted (from JSON): {extracted_data['user_message'][:100]}...")
                 except json.JSONDecodeError:
                     # If content is just a plain string in V1
                     if isinstance(content_str, str):
                         extracted_data['user_message'] = content_str.strip()
                         logging.debug(f"V1 message content treated as raw string: {extracted_data['user_message'][:100]}...")
                     else:
                         logging.warning(f"Could not decode V1 message content: {content_str}")
                 except TypeError: # Handle cases where content might not be string/bytes
                      logging.warning(f"Invalid type for V1 message content: {type(content_str)}")

            elif extracted_data['message_type']:
                 logging.info(f"Received unsupported message_type (V1): {extracted_data['message_type']} from chat {extracted_data['chat_id']}")
            else:
                 logging.warning("Message type missing in V1 event.")

        else:
            logging.error(f"Could not determine event schema (V1/V2). Keys: {list(request_json.keys())}")
            return None

        # --- Final Validation and Filtering ---
        if not extracted_data['chat_id']:
            logging.error("Failed to extract chat_id from event after parsing.")
            return None # Critical failure

        if not extracted_data['message_id']:
             logging.warning(f"Failed to extract message_id from event for chat {extracted_data['chat_id']}. Proceeding without it.")

        # Filter by Target Chat ID
        if extracted_data['chat_id'] != TARGET_LARK_CHAT_ID:
            logging.info(f"Ignoring message from non-target chat ID: {extracted_data['chat_id']}")
            return None

        # Filter by Message Type (currently only support text)
        if extracted_data['message_type'] != "text":
             logging.info(f"Ignoring non-text message. Type: {extracted_data['message_type']}")
             return None

        # Filter by Empty Content
        if not extracted_data['user_message']:
             logging.info(f"Ignoring text message with empty content.")
             return None

        logging.info(f"Successfully parsed relevant Lark text event: chat_id={extracted_data['chat_id']}, msg_id={extracted_data['message_id']}")
        return extracted_data

    except Exception as e:
         logging.error(f"Exception during event parsing: {e}", exc_info=True)
         return None

def handle_message_event(parsed_event: Dict[str, Any]) -> Tuple[Any, int]:
    """Handles the logic for a parsed message event.

    Retrieves secrets, interacts with Firestore and OpenAI, sends replies.

    Returns:
        A tuple (response_body, status_code) for the Cloud Function response.
        Response body can be str ("OK") or dict for JSON errors.
    """
    chat_id = parsed_event.get('chat_id')
    message_id = parsed_event.get('message_id') # ID of the current incoming message
    user_message = parsed_event.get('user_message')
    sender_id = parsed_event.get('sender_id')

    # Added Logging for Start
    print(f"Starting handle_message_event for message_id: {message_id}")

    # Double check critical info
    if not chat_id or not user_message:
        logging.error("handle_message_event called with missing chat_id or user_message.")
        return {"status": "ERROR", "message": "Internal parsing error"}, 500

    # --- Get Credentials ---
    # UPDATED: Get Lark token from URL instead of Secret Manager
    lark_token = get_lark_token_from_url(CHECK_LARK_TOKEN_URL)
    # Added Logging for Lark Token Fetch
    if lark_token:
        print(f"Successfully retrieved Lark token ending with ...{lark_token[-6:]}")
        print(f"Debug: Successfully retrieved Lark token: {lark_token[:5]}...{lark_token[-5:]}")
    else:
        print("Failed to retrieve Lark token from check_lark_token URL.")
        print("Debug: Failed to retrieve Lark token from check_lark_token URL.")
        # Specific error message if fetching token from URL failed
        logging.error("Failed to retrieve Lark token from check_lark_token URL. Aborting message handling.")
        # Cannot notify user without token
        return {"status": "ERROR", "message": "Server configuration error (Could not get Lark Token from URL)"}, 500

    openai_api_key = get_secret(SECRET_MANAGER_PROJECT_ID, OPENAI_API_KEY_SECRET_ID)
    if not openai_api_key:
        logging.error("Failed to retrieve OpenAI API key. Aborting message handling.")
        # Notify user about the issue
        send_lark_message_success = send_lark_message(chat_id, "Lỗi: Không thể truy cập khóa API OpenAI. Vui lòng liên hệ quản trị viên.", lark_token)
        print(f"Debug: Lark message sent (reporting OpenAI key error): {send_lark_message_success}")
        return {"status": "ERROR", "message": "Server configuration error (OpenAI Key)"}, 500

    # --- Check for Pending Conversation ---
    # Suggestion: For more robust retry prevention, consider checking if this specific
    # message_id has already been processed for this conversation before proceeding.
    # This would require adding message_id/last_processed_message_id to the Firestore record and checking it.
    pending_conv_snapshot = get_pending_conversation(chat_id)
    conv_id = None # Initialize conv_id

    if pending_conv_snapshot:
        # --- Handle Response to a Pending Question ---
        conv_id = pending_conv_snapshot.id # Assign conv_id here
        print(f"Handling response for pending conversation: {conv_id}")
        conv_data = pending_conv_snapshot.to_dict()
        if not conv_data:
             logging.error(f"Failed to read data for pending conversation {conv_id}. Aborting.")
             send_lark_message_success = send_lark_message(chat_id, "Lỗi: Không thể đọc dữ liệu cuộc hội thoại đang chờ.", lark_token)
             print(f"Lark message sent (reporting Firestore read error): {send_lark_message_success} for conversation {conv_id}")
             print(f"Debug: Lark message sent (reporting Firestore read error): {send_lark_message_success} for conversation {conv_id}")
             update_success = update_conversation(conv_id, {'labels.Status': 'Failed', 'bot_response': 'Error reading conversation data'})
             print(f"Firestore document updated (marking read error): {update_success} for conversation {conv_id}")
             print(f"Debug: Firestore document updated (marking read error): {update_success} for conversation {conv_id}")
             return {"status": "ERROR", "message": "Failed to read Firestore data"}, 500

        request_count = conv_data.get('requestCount', 0)
        history = conv_data.get('history', [])

        # Prevent adding duplicate consecutive user messages if function reruns (simple check)
        if not history or history[-1].get("role") != "user" or history[-1].get("content") != user_message:
            history.append({"role": "user", "content": user_message})
        else:
            # NOTE: This duplicate check assumes the function runs quickly and consecutively.
            # A more robust check using message_id in Firestore might be needed for true idempotency.
            logging.warning(f"Duplicate user message detected for {conv_id}. History[-1]: {history[-1]}. Current message: {user_message}. Ignoring duplicate and acknowledging request.")
            return "OK", 200 # Acknowledge receipt, state hasn't changed meaningfully

        # Check if the user is confirming
        is_confirming = any(keyword in user_message.lower() for keyword in CONFIRMATION_KEYWORDS)

        if is_confirming:
            print(f"User confirmed the previous bot response for {conv_id}.")
            confirmed_command = ""
            for i in range(len(history) - 2, -1, -1):
                 if history[i].get("role") == "assistant":
                      confirmed_command = history[i].get("content", "")
                      break
            if not confirmed_command:
                 logging.error(f"Confirmation received for {conv_id}, but couldn't find last assistant message in history: {history}")
                 send_lark_message_success = send_lark_message(chat_id, "Lỗi: Không tìm thấy phản hồi trước đó để xác nhận.", lark_token)
                 print(f"Lark message sent (reporting confirmation error): {send_lark_message_success} for conversation {conv_id}")
                 print(f"Debug: Lark message sent (reporting confirmation error): {send_lark_message_success} for conversation {conv_id}")
                 update_success = update_conversation(conv_id, {
                     'labels.Status': 'Failed',
                     'bot_response': 'Error finding previous response on confirmation',
                     'user_message': user_message # Store the problematic confirmation message
                     })
                 print(f"Firestore document updated (marking confirmation error): {update_success} for conversation {conv_id}")
                 print(f"Debug: Firestore document updated (marking confirmation error): {update_success} for conversation {conv_id}")
                 return {"status": "ERROR", "message": "Logic error: Could not find previous response"}, 500

            print(f"Confirmed command for {conv_id}: {confirmed_command[:100]}...")
            # Firestore Update: Add top-level user_message for latest user input clarity
            update_successful = update_conversation(conv_id, {
                'labels.Status': 'Completed',
                'responseCount': firestore.Increment(1),
                'history': history,
                'user_message': user_message # Latest user message (confirmation)
            })
            print(f"Firestore document updated (status Completed): {update_successful} for conversation {conv_id}")
            print(f"Debug: Firestore document updated (status Completed): {update_successful} for conversation {conv_id}")

            if update_successful:
                 handle_command(confirmed_command)
                 send_lark_message_success = send_lark_message(chat_id, "Đã xác nhận. Đang xử lý yêu cầu của bạn...", lark_token)
                 print(f"Lark message sent (confirmation success): {send_lark_message_success} for conversation {conv_id}")
                 print(f"Debug: Lark message sent (confirmation success): {send_lark_message_success} for conversation {conv_id}")
            else:
                 send_lark_message_success = send_lark_message(chat_id, "Lỗi: Không thể cập nhật trạng thái cuộc hội thoại sau khi xác nhận.", lark_token)
                 print(f"Lark message sent (reporting update failure): {send_lark_message_success} for conversation {conv_id}")
                 print(f"Debug: Lark message sent (reporting update failure): {send_lark_message_success} for conversation {conv_id}")
                 return {"status": "ERROR", "message": "Firestore update failed after confirmation"}, 500
        else:
            # --- User provided more info, ask GPT again ---
            print(f"User provided additional information for {conv_id}. Request count: {request_count}")
            if request_count >= MAX_CLARIFICATION_ATTEMPTS:
                logging.warning(f"Max clarification attempts ({MAX_CLARIFICATION_ATTEMPTS}) reached for {conv_id}.")
                fail_message = "Đã vượt quá số lần hỏi lại tối đa. Không thể xử lý yêu cầu."
                # Firestore Update: Add top-level user_message
                update_success = update_conversation(conv_id, {
                    'labels.Status': 'Completed',
                    'bot_response': fail_message,
                    'responseCount': firestore.Increment(1),
                    'history': history,
                    'user_message': user_message # Store the last user message
                })
                print(f"Firestore document updated (max attempts): {update_success} for conversation {conv_id}")
                print(f"Debug: Firestore document updated (max attempts): {update_success} for conversation {conv_id}")
                send_lark_message_success = send_lark_message(chat_id, fail_message, lark_token)
                print(f"Lark message sent (max attempts): {send_lark_message_success} for conversation {conv_id}")
                print(f"Debug: Lark message sent (max attempts): {send_lark_message_success} for conversation {conv_id}")
            else:
                bot_response, error = call_openai_api(openai_api_key, OPENAI_SYSTEM_PROMPT, history)
                # Added Logging for OpenAI API Call
                if error:
                    print(f"OpenAI API call failed for conversation {conv_id}: {error}")
                    print(f"Debug: OpenAI API call failed for conversation {conv_id}: {error}")
                    send_lark_message_success = send_lark_message(chat_id, f"Lỗi khi xử lý thông tin bổ sung: {error}", lark_token)
                    print(f"Lark message sent (reporting OpenAI error): {send_lark_message_success} for conversation {conv_id}")
                    print(f"Debug: Lark message sent (reporting OpenAI error): {send_lark_message_success} for conversation {conv_id}")
                    # Firestore Update: Update history and user_message even if AI call fails
                    update_success = update_conversation(conv_id, {
                        'history': history,
                        'user_message': user_message
                        })
                    print(f"Firestore document updated (after OpenAI failure): {update_success} for conversation {conv_id}")
                    print(f"Debug: Firestore document updated (after OpenAI failure): {update_success} for conversation {conv_id}")
                elif bot_response:
                    print(f"OpenAI API called successfully for conversation {conv_id}.")
                    print(f"Debug: OpenAI API called successfully for conversation {conv_id}.")
                    history.append({"role": "assistant", "content": bot_response})
                    message_sent = send_lark_message(chat_id, bot_response, lark_token)
                    # Added Logging for Lark Message Send
                    print(f"Lark message sent (clarification response): {message_sent} for conversation {conv_id}")
                    print(f"Debug: Lark message sent (clarification response): {message_sent} for conversation {conv_id}")
                    if message_sent:
                         # Firestore Update: Add top-level user_message
                        update_success = update_conversation(conv_id, {
                            'bot_response': bot_response,
                            'requestCount': firestore.Increment(1),
                            'labels.Status': 'Pending',
                            'history': history,
                            'user_message': user_message # Store latest user message that triggered this bot response
                        })
                        print(f"Firestore document updated (clarification pending): {update_success} for conversation {conv_id}")
                        print(f"Debug: Firestore document updated (clarification pending): {update_success} for conversation {conv_id}")
                    else:
                        logging.error(f"Failed to send Lark message for {conv_id}, Firestore update skipped for this turn.")
                        # Firestore Update: Still save history up to user msg and user_message
                        update_success = update_conversation(conv_id, {
                            'history': history[:-1],
                            'user_message': user_message
                            })
                        print(f"Firestore document updated (after Lark send failure): {update_success} for conversation {conv_id}")
                        print(f"Debug: Firestore document updated (after Lark send failure): {update_success} for conversation {conv_id}")
    else:
        # --- Handle New Request ---
        print("Handling new conversation request.")
        initial_history = [{"role": "user", "content": user_message}]
        bot_response, error = call_openai_api(openai_api_key, OPENAI_SYSTEM_PROMPT, initial_history)
        # Added Logging for OpenAI API Call
        if error:
            print(f"OpenAI API call failed for new request: {error}")
            print(f"Debug: OpenAI API call failed for new request: {error}")
            send_lark_message_success = send_lark_message(chat_id, f"Lỗi khi xử lý yêu cầu ban đầu: {error}", lark_token)
            print(f"Lark message sent (reporting initial OpenAI error): {send_lark_message_success}")
            print(f"Debug: Lark message sent (reporting initial OpenAI error): {send_lark_message_success}")
            return {"status": "ERROR", "message": f"OpenAI API failed: {error}"}, 500
        elif bot_response:
             print("OpenAI API called successfully for new request.")
             print("Debug: OpenAI API called successfully for new request.")
             current_history = initial_history + [{"role": "assistant", "content": bot_response}]
             # Firestore: Includes top-level user_message for initial message clarity
             initial_data = {
                'chat_id': chat_id,
                'initial_message_id': message_id,
                'user_message': user_message,
                'sender_id': sender_id,
                'bot_response': bot_response,
                'requestCount': 1,
                'responseCount': 0,
                'labels': {
                    'DataSource': 'LarkRequest',
                    'Purpose': 'Processing',
                    'Status': 'Pending',
                },
                'vectorStatus': 'pending',
                'vectorId': None,
                'history': current_history
            }
             conv_id = create_conversation(initial_data)
             # Added Logging for Firestore Create
             if conv_id:
                 print(f"Firestore document created: {conv_id}")
                 print(f"Debug: Firestore document created: {conv_id}")
                 message_sent = send_lark_message(chat_id, bot_response, lark_token)
                 # Added Logging for Lark Message Send
                 print(f"Lark message sent (initial response): {message_sent} for conversation {conv_id}")
                 print(f"Debug: Lark message sent (initial response): {message_sent} for conversation {conv_id}")
                 if not message_sent:
                      logging.error(f"Created conversation {conv_id} but failed to send initial Lark message.")
                      # Update status to Failed if send fails (verified existing)
                      update_success = update_conversation(conv_id, {
                          'labels.Status': 'Failed',
                          'bot_response': 'Failed to send initial message'
                      })
                      # Added Logging for Firestore Update
                      print(f"Firestore document updated (marking initial send failed): {update_success} for conversation {conv_id}")
                      print(f"Debug: Firestore document updated (marking initial send failed): {update_success} for conversation {conv_id}")
                      # Optional: Consider returning 500 if initial send fails, as state is inconsistent
                      # return {"status": "ERROR", "message": "Failed to send initial Lark message"}, 500
             else:
                 print(f"Firestore document creation failed.")
                 print("Debug: Firestore document creation failed.")
                 send_lark_message_success = send_lark_message(chat_id, "Lỗi: Không thể lưu trữ cuộc hội thoại ban đầu.", lark_token)
                 print(f"Lark message sent (reporting create failure): {send_lark_message_success}")
                 print(f"Debug: Lark message sent (reporting create failure): {send_lark_message_success}")
                 return {"status": "ERROR", "message": "Firestore create failed"}, 500

    # If all went well or handled internally (e.g., duplicate message)
    return "OK", 200

# --- Main Cloud Function --- 

@functions_framework.http
def lark_webhook(request):
    """HTTP Cloud Function to handle Lark webhook events (Challenge and Messages)."""
    # Unit Test Idea: Mock request object (method, is_json, get_json). 
    #               Call lark_webhook, assert calls to handlers and final response.
    logging.info(f"lark_webhook invoked. Method: {request.method}, Content-Type: {request.content_type}, Path: {request.path}")

    # Check if clients initialized (critical)
    if not db or not secret_manager_client:
         logging.critical("Firestore or Secret Manager client not available. Function cannot proceed.")
         # Use standard tuple return format
         return (
             json.dumps({'status': 'ERROR', 'message': 'Internal Server Error: Service dependencies not initialized.'}),
             500,
             {'Content-Type': 'application/json'}
         )

    # --- Request Validation ---
    if request.method != 'POST':
        logging.warning(f"Received non-POST request: {request.method}")
        # Handle GET for health checks or simple info
        if request.method == 'GET':
             # Use standard tuple return format
             return (
                json.dumps({'status': 'OK', 'message': 'Service is running. Use POST for webhook.'}),
                200,
                {'Content-Type': 'application/json'}
             )
        else:
             # Method Not Allowed for others
             # Use standard tuple return format
             return (
                json.dumps({'status': 'ERROR', 'message': 'Method Not Allowed'}),
                405,
                {'Content-Type': 'application/json'}
             )

    if not request.is_json:
         logging.warning(f"Received POST request but Content-Type is not JSON: {request.content_type}")
         # Use standard tuple return format
         return (
            json.dumps({'status': 'ERROR', 'message': 'Invalid Content-Type, must be application/json'}),
            415, # Unsupported Media Type
            {'Content-Type': 'application/json'}
         )

    # --- JSON Parsing and Handling ---
    request_json = request.get_json(silent=True)
    if request_json is None:
        # Log raw data for debugging
        raw_data = request.get_data(as_text=True)
        logging.error(f"Failed to parse JSON data. Raw request body: {raw_data}")
        # Use standard tuple return format
        return (
            json.dumps({'status': 'ERROR', 'message': 'Invalid JSON payload'}),
            400,
            {'Content-Type': 'application/json'}
        )

    # --- Dispatch based on Payload Type (Challenge or Event) ---
    try:
        if 'challenge' in request_json:
            # Handle Lark's challenge request (already returns tuple)
            return handle_challenge(request_json)
        else:
            # Assume it's a message event, parse it
            parsed_event = parse_lark_event(request_json)

            if parsed_event:
                 # Handle the valid text message event (returns tuple: body, status)
                 response_body, status_code = handle_message_event(parsed_event)
                 # Determine headers based on body type
                 if isinstance(response_body, dict):
                     headers = {'Content-Type': 'application/json'}
                     response_body = json.dumps(response_body) # Serialize dict to JSON string
                 else: # Assume plain text ("OK")
                     headers = {'Content-Type': 'text/plain'}
                 return response_body, status_code, headers
            else:
                 # Parsing failed or irrelevant event
                 # Logged within parse_lark_event
                 logging.info("Request parsed but determined irrelevant or failed parsing, acknowledging request.")
                 # Acknowledge receipt even if not processed (HTTP 200)
                 # Use standard tuple return format
                 return (
                     json.dumps({'status': 'OK', 'message': 'Event received but not processed (e.g., wrong chat, non-text, or parse error)'}),
                     200,
                     {'Content-Type': 'application/json'}
                 )

    except Exception as e:
        # Catch-all for unexpected errors during dispatch or handling
        logging.error(f"Unhandled exception in main webhook handler: {e}", exc_info=True)
        # Attempt to notify Lark if possible (best effort)
        try:
            # Try to get Lark token again *specifically* for error notification
            lark_token_notify = get_lark_token_from_url(CHECK_LARK_TOKEN_URL) 
            # Try to extract chat_id again from raw JSON if possible for notification
            chat_id_notify = request_json.get('event', {}).get('message', {}).get('chat_id')
            
            if chat_id_notify and lark_token_notify:
                 logging.info(f"Attempting to send final error notification to chat {chat_id_notify}")
                 send_lark_message(chat_id_notify, "Đã xảy ra lỗi máy chủ nội bộ không mong muốn khi xử lý yêu cầu của bạn.", lark_token_notify)
            elif chat_id_notify:
                 logging.error("Could not get Lark token to send final error notification.")
            else:
                 logging.error("Cannot send final error notification to Lark (missing chat_id or token).")
        except Exception as notify_e:
             logging.error(f"Exception occurred while trying to send final error notification to Lark: {notify_e}", exc_info=True)

        # Return standardized JSON error using tuple format
        return (
            json.dumps({'status': 'ERROR', 'message': 'Internal Server Error'}),
            500,
            {'Content-Type': 'application/json'}
         )
