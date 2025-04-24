import pyautogui
import base64
import io
from datetime import datetime
import time
import requests
import socket
import os
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image
import uuid
import getpass

# --- Configuration ---
SCREENSHOTS_DIR = "screenshots"
OFFLINE_QUEUE_DIR = "offline_queue"
LOG_FILE = "screenshot_logger.log"
MAX_LOG_SIZE = 1_000_000
BACKUP_COUNT = 5
MAX_LOG_ENTRIES = 5

API_URL = "http://192.168.211.28:8000/api/screenshots/"
LOGIN_URL = "http://192.168.211.28:8000/api/login/"

# --- Logging Setup ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding='utf-8')
formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%d-%m-%Y_%H-%M-%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log(msg):
    print(msg)
    logger.info(msg)

def current_timestamp():
    return datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

def get_computer_username():
    return getpass.getuser()

def get_system_username_uuid():
    system_uuid = str(uuid.getnode())
    username = get_computer_username().lower()
    return f"{username}_{system_uuid}"

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def save_screenshot(screenshot, timestamp):
    ensure_dir(SCREENSHOTS_DIR)
    filepath = os.path.join(SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
    screenshot.save(filepath)
    log(f"🖼️ Screenshot saved to: {filepath}")
    return filepath

def save_offline_copy(screenshot, timestamp):
    ensure_dir(OFFLINE_QUEUE_DIR)
    filepath = os.path.join(OFFLINE_QUEUE_DIR, f"screenshot_{timestamp}.png")
    screenshot.save(filepath)
    log(f"💾 Offline copy saved: {filepath}")
    return filepath

def encode_screenshot(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

def get_complete_logs():
    if not os.path.exists(LOG_FILE):
        return ""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[LogError] Could not read logs: {str(e)}"

def send_screenshot_to_api(api_url, token, encoded_data, timestamp, log_text):
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    payload = {
        "screenshot_json": {timestamp: encoded_data},
        "log_text": log_text
    }
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            log("✅ Screenshot + logs sent.")
            return True
        else:
            log(f"❌ API Error: {response.status_code} {response.text}")
            return False
    except Exception as e:
        log(f"❌ Error sending screenshot: {e}")
        return False

def get_token(username, login_url):
    headers = {'Content-Type': 'application/json'}
    payload = {'uuid': username}
    try:
        response = requests.post(login_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            log(f"🔐 Login failed: {response.status_code} {response.text}")
    except Exception as e:
        log(f"❌ Login error: {e}")
    return None

def send_offline_screenshots(api_url, token):
    ensure_dir(OFFLINE_QUEUE_DIR)
    for filename in os.listdir(OFFLINE_QUEUE_DIR):
        if filename.endswith(".png"):
            filepath = os.path.join(OFFLINE_QUEUE_DIR, filename)
            try:
                img = Image.open(filepath)
                img.load()
                img_copy = img.copy()
                img.close()

                timestamp = filename.replace("screenshot_", "").replace(".png", "")
                encoded = encode_screenshot(img_copy)
                log_text = get_complete_logs()

                if send_screenshot_to_api(api_url, token, encoded, timestamp, log_text):
                    os.remove(filepath)
                    log(f"✅ Offline screenshot sent and deleted from queue: {filename}")
                else:
                    log(f"⚠️ Failed to send offline screenshot: {filename}")
            except Exception as e:
                log(f"❌ Error processing offline screenshot {filename}: {e}")

def run_loop(api_url, login_url, screenshot_interval=3, log_interval=2, send_interval=5):
    system_user_uuid = get_system_username_uuid()

    # Retry token acquisition until successful
    token = None
    while token is None:
        log("🔄 Attempting to authenticate with API...")
        if check_internet():
            token = get_token(system_user_uuid, login_url)
        else:
            log("📴 No internet connection. Retrying in 30 seconds...")
        if token is None:
            time.sleep(30)

    log("🟢 Screenshot loop started.")
    last_screenshot_time = 0
    last_log_time = 0
    last_send_time = 0
    screenshot = None
    logs = []

    while True:
        current_time = time.time()

        if current_time - last_screenshot_time >= screenshot_interval * 60:
            screenshot = pyautogui.screenshot()
            timestamp = current_timestamp()
            if check_internet():
                log("🌐 Internet available.")
                save_screenshot(screenshot, timestamp)
            else:
                log("📴 No internet. Saving offline.")
                save_screenshot(screenshot, timestamp)
                save_offline_copy(screenshot, timestamp)
            last_screenshot_time = current_time

        if current_time - last_log_time >= log_interval * 60:
            log_text = get_complete_logs()
            logs.append(log_text)
            if len(logs) > MAX_LOG_ENTRIES:
                logs = logs[-MAX_LOG_ENTRIES:]
            last_log_time = current_time

        if current_time - last_send_time >= send_interval * 60:
            if screenshot and logs:
                log("⏳ Sending screenshot and logs to API.")
                timestamp = current_timestamp()
                combined_logs = "\n\n".join(logs[-2:])
                if send_screenshot_to_api(api_url, token, encode_screenshot(screenshot), timestamp, combined_logs):
                    log("☁️ Screenshot and logs sent successfully.")
                else:
                    save_offline_copy(screenshot, timestamp)
            send_offline_screenshots(api_url, token)
            last_send_time = current_time
            logs.clear()

        time.sleep(30)

if __name__ == "__main__":
    run_loop(API_URL, LOGIN_URL)
