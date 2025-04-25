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

# --- Configuration ---
SCREENSHOTS_DIR = "screenshots"
OFFLINE_QUEUE_DIR = "offline_queue"
LOG_DIR = "logs"
IDLE_THRESHOLD = 60  # seconds

API_URL = "http://192.168.211.28:8000/api/screenshots/"
LOGIN_URL = "http://192.168.211.28:8000/api/login/"

# --- Ensure Directories Exist ---
for d in [SCREENSHOTS_DIR, OFFLINE_QUEUE_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

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

def save_screenshot(screenshot, timestamp, folder):
    filepath = os.path.join(folder, f"screenshot_{timestamp}.png")
    screenshot.save(filepath)
    log(f"🖼️ Screenshot saved to: {filepath}")
    return filepath

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
    except Exception as e:
        log(f"[ERROR] Token fetch failed: {e}")
    return None

def send_screenshot_to_api(api_url, token, encoded_data, timestamp, log_text, idle_sessions):
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    payload = {
        "screenshot_json": {timestamp: encoded_data},
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
        log(f"[ERROR] Failed to send screenshot: {e}")
        return False

def send_offline_screenshots(api_url, token):
    for filename in os.listdir(OFFLINE_QUEUE_DIR):
        if filename.endswith(".png"):
            filepath = os.path.join(OFFLINE_QUEUE_DIR, filename)
            try:
                with Image.open(filepath) as img:
                    encoded = encode_screenshot(img)
                timestamp = filename.replace("screenshot_", "").replace(".png", "")
                if send_screenshot_to_api(api_url, token, encoded, timestamp, get_complete_logs(), []):
                    os.remove(filepath)
                    log(f"✅ Sent offline screenshot: {filename}")
            except Exception as e:
                log(f"[ERROR] Could not send offline screenshot: {e}")

# --- Main Loop ---
def run_loop(api_url, login_url, screenshot_interval=3, send_interval=5):
    user_uuid = get_system_username_uuid()
    token = None

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
    idle_sessions = []
    screenshot_queue = []

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
            idle_sessions.append({
                "start_time": idle_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": end.strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": duration
            })
            idle_start = None

        # Take screenshot every interval
        if now - last_screenshot_time >= screenshot_interval * 60:
            screenshot = pyautogui.screenshot()
            timestamp = current_timestamp()
            save_screenshot(screenshot, timestamp, SCREENSHOTS_DIR)
            if not check_internet():
                save_screenshot(screenshot, timestamp, OFFLINE_QUEUE_DIR)

            # Store screenshot and timestamp in queue
            screenshot_queue.append((screenshot, timestamp))
            last_screenshot_time = now

        # Send all screenshots in queue
        if now - last_send_time >= send_interval * 60:
            log("📤 Preparing to send queued screenshots...")
            for screenshot, timestamp in screenshot_queue:
                encoded = encode_screenshot(screenshot)
                success = send_screenshot_to_api(
                    api_url, token, encoded, timestamp,
                    get_complete_logs(), idle_sessions
                )
                if success:
                    log(f"✅ Screenshot sent: {timestamp}")
                else:
                    save_screenshot(screenshot, timestamp, OFFLINE_QUEUE_DIR)
                    log(f"❌ Failed to send screenshot: {timestamp}, saved offline.")

            screenshot_queue.clear()
            send_offline_screenshots(api_url, token)
            idle_sessions.clear()
            last_send_time = now

        time.sleep(30)

# --- Entry Point ---
logger, DAILY_LOG_FILE = setup_logger()

if __name__ == "__main__":
    run_loop(API_URL, LOGIN_URL)
