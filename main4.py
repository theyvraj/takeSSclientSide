import pyautogui
from PIL import Image
import logging
from logging.handlers import RotatingFileHandler
import ctypes
import base64
import io
from datetime import datetime
import time
import requests
import socket
import os
import uuid
import getpass
import json

# --- Configuration ---
SCREENSHOT_JSON = "screenshot_data.json"
ERROR_LOG_FILE = "error_log.json"
IDLE_DATA_FILE = "idle_data.json"
LOG_DIR = "logs"
IDLE_THRESHOLD = 60  # seconds

API_URL = "http://192.168.211.28:8000/api/screenshots/"
LOGIN_URL = "http://192.168.211.28:8000/api/login/"
ERROR_API_URL = "http://192.168.211.28:8000/api/errors/"

# --- Ensure Directories Exist ---
os.makedirs(LOG_DIR, exist_ok=True)

# --- Logger Setup ---
def setup_logger():
    today = datetime.now().strftime('%Y-%m-%d')
    log_path = os.path.join(LOG_DIR, f"{get_system_username_uuid()}_{today}.log")
    logger = logging.getLogger("ClientLogger")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger, log_path

def log(msg):
    logger.info(msg)

def log_error_to_file(error_message):
    error_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "error": error_message
    }
    try:
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, "r+", encoding="utf-8") as f:
                existing = json.load(f)
                existing.append(error_entry)
                f.seek(0)
                json.dump(existing, f, indent=2)
        else:
            with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([error_entry], f, indent=2)
    except Exception as e:
        log(f"[ERROR] Could not write to error_log.json: {e}")

# --- Helper Functions ---
def get_computer_username():
    return getpass.getuser()

def get_system_username_uuid():
    system_uuid = str(uuid.getnode())
    username = get_computer_username().lower()
    return f"{username}_{system_uuid}"

def current_timestamp():
    return datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False

def encode_screenshot(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

def get_complete_logs():
    if not os.path.exists(DAILY_LOG_FILE):
        return ""
    try:
        with open(DAILY_LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[LogError] Could not read logs: {str(e)}"

def get_idle_duration_windows():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0

def get_token(username, login_url):
    headers = {'Content-Type': 'application/json'}
    payload = {'uuid': username}
    try:
        response = requests.post(login_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('token')
        log(f"[AuthError] Login failed: {response.status_code} - {response.text}")
        log_error_to_file(f"Token fetch failed: {response.status_code} - {response.text}")
    except Exception as e:
        log(f"[ERROR] Token fetch failed: {e}")
        log_error_to_file(str(e))
    return None

def send_screenshot_to_api(api_url, token, screenshot_data, log_text, idle_sessions):
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    payload = {
        "screenshot_json": screenshot_data,
        "log_text": log_text,
        "idle_time_json": {
            "idle_sessions": idle_sessions,
            "total_idle_time": sum(session["duration_seconds"] for session in idle_sessions)
        }
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        return response.status_code == 200
    except Exception as e:
        log(f"[ERROR] Failed to send screenshot data: {e}")
        log_error_to_file(str(e))
        return False

def send_error_logs_to_api(error_api_url, token):
    if not os.path.exists(ERROR_LOG_FILE):
        return

    try:
        with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
            errors = json.load(f)

        if not errors:
            return

        headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
        payload = {"errors": errors}

        response = requests.post(error_api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            os.remove(ERROR_LOG_FILE)
            log("🧹 Cleared error_log.json after successful transmission.")
        else:
            log(f"[ErrorLog] Failed to send errors: {response.status_code} - {response.text}")
    except Exception as e:
        log(f"[ERROR] Failed to send error logs: {e}")

# --- Main Loop ---
def run_loop(api_url, login_url, error_api_url, screenshot_interval=3, send_interval=5):
    user_uuid = get_system_username_uuid()
    token = None

    # Load persisted idle sessions
    idle_sessions = []
    if os.path.exists(IDLE_DATA_FILE):
        try:
            with open(IDLE_DATA_FILE, "r", encoding="utf-8") as f:
                idle_sessions = json.load(f)
        except Exception as e:
            log_error_to_file(f"Could not read idle_data.json: {e}")

    while token is None:
        log("🔐 Authenticating...")
        if check_internet():
            token = get_token(user_uuid, login_url)
        if token is None:
            time.sleep(30)

    log("🟢 Screenshot loop started.")
    last_screenshot_time = 0
    last_send_time = 0
    idle_start = None

    while True:
        now = time.time()

        # Idle detection
        idle_time = get_idle_duration_windows()
        if idle_time >= IDLE_THRESHOLD:
            if idle_start is None:
                idle_start = datetime.now()
        elif idle_start:
            end = datetime.now()
            duration = (end - idle_start).total_seconds()
            new_session = {
                "start_time": idle_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": duration
            }
            idle_sessions.append(new_session)
            try:
                with open(IDLE_DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(idle_sessions, f, indent=2)
            except Exception as e:
                log_error_to_file(f"Failed to update idle_data.json: {e}")
            idle_start = None

        # Take screenshot every interval
        if now - last_screenshot_time >= screenshot_interval * 60:
            screenshot = pyautogui.screenshot()
            timestamp = current_timestamp()
            encoded = encode_screenshot(screenshot)

            new_entry = {timestamp: encoded}
            existing_data = []
            if os.path.exists(SCREENSHOT_JSON):
                with open(SCREENSHOT_JSON, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            existing_data.append(new_entry)
            with open(SCREENSHOT_JSON, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2)
            log(f"🖼️ Screenshot captured and added to JSON queue: {timestamp}")
            last_screenshot_time = now

        # Send all screenshots every interval
        if now - last_send_time >= send_interval * 60:
            log("📤 Preparing to send queued screenshot data...")
            try:
                if os.path.exists(SCREENSHOT_JSON):
                    with open(SCREENSHOT_JSON, "r", encoding="utf-8") as f:
                        data_list = json.load(f)
                    screenshot_data = {k: v for d in data_list for k, v in d.items()}

                    # Load idle sessions before sending
                    persistent_idle_sessions = []
                    if os.path.exists(IDLE_DATA_FILE):
                        with open(IDLE_DATA_FILE, "r", encoding="utf-8") as f:
                            persistent_idle_sessions = json.load(f)

                    success = send_screenshot_to_api(
                        api_url, token, screenshot_data,
                        get_complete_logs(), persistent_idle_sessions
                    )

                    if success:
                        os.remove(SCREENSHOT_JSON)
                        log("✅ All screenshot data sent successfully and cleared.")
                        if os.path.exists(IDLE_DATA_FILE):
                            os.remove(IDLE_DATA_FILE)
                            log("🧹 Cleared idle_data.json after successful transmission.")
                        idle_sessions.clear()
                    else:
                        log("❌ Failed to send screenshot data, retaining JSON for retry.")
            except Exception as e:
                log_error_to_file(str(e))

            send_error_logs_to_api(error_api_url, token)
            last_send_time = now

        time.sleep(30)

# --- Entry Point ---
logger, DAILY_LOG_FILE = setup_logger()

if __name__ == "__main__":
    run_loop(API_URL, LOGIN_URL, ERROR_API_URL)
