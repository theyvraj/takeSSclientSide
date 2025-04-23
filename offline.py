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
from threading import Thread
from PIL import Image
import pystray
import uuid
import getpass

# --- Configuration ---
OFFLINE_QUEUE_DIR = "offline_queue"
LOG_FILE = "screenshot_logger.log"
MAX_LOG_SIZE = 1_000_000
BACKUP_COUNT = 5

API_URL = "http://192.168.211.28:8000/api/screenshots/"
LOGIN_URL = "http://192.168.211.28:8000/api/login/"
LOG_URL = "http://192.168.211.28:8000/api/logs/"

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
    username = get_computer_username()
    return f"{username}_{system_uuid}"

def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False

def ensure_offline_dir():
    os.makedirs(OFFLINE_QUEUE_DIR, exist_ok=True)

def save_offline_screenshot(screenshot, timestamp):
    ensure_offline_dir()
    filepath = os.path.join(OFFLINE_QUEUE_DIR, f"screenshot_{timestamp}.png")
    screenshot.save(filepath)
    log(f"💾 Offline screenshot saved: {filepath}")

def encode_screenshot(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

def get_recent_logs():
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
    ensure_offline_dir()
    for filename in os.listdir(OFFLINE_QUEUE_DIR):
        if filename.endswith(".png"):
            filepath = os.path.join(OFFLINE_QUEUE_DIR, filename)
            try:
                with Image.open(filepath) as img:
                    timestamp = filename.replace("screenshot_", "").replace(".png", "")
                    encoded = encode_screenshot(img)
                    log_text = get_recent_logs()
                    if send_screenshot_to_api(api_url, token, encoded, timestamp, log_text):
                        os.remove(filepath)
                        log(f"✅ Offline screenshot sent and deleted: {filename}")
                    else:
                        log(f"⚠️ Failed to send offline screenshot: {filename}")
            except Exception as e:
                log(f"❌ Error processing offline screenshot {filename}: {e}")

def run_loop(api_url, login_url, interval_minutes=1):
    system_user_uuid = get_system_username_uuid()
    token = get_token(system_user_uuid, login_url)
    if not token:
        log("❌ Authentication failed. Exiting.")
        return

    log("🟢 Screenshot loop started.")
    while True:
        try:
            if check_internet():
                log("🌐 Internet available.")
                send_offline_screenshots(api_url, token)  # 🔁 Process any offline screenshots

                screenshot = pyautogui.screenshot()
                timestamp = current_timestamp()
                encoded = encode_screenshot(screenshot)
                log_text = get_recent_logs()
                if send_screenshot_to_api(api_url, token, encoded, timestamp, log_text):
                    log("☁️ Screenshot sent to API successfully.")
                else:
                    save_offline_screenshot(screenshot, timestamp)
            else:
                log("📴 No internet. Screenshot will be saved offline.")
                screenshot = pyautogui.screenshot()
                timestamp = current_timestamp()
                save_offline_screenshot(screenshot, timestamp)
        except Exception as e:
            log(f"🔥 Fatal loop error: {e}")
        time.sleep(interval_minutes * 60)

def start_from_tray():
    def loop_thread():
        run_loop(API_URL, LOGIN_URL)

    def on_quit(icon, item):
        log("👋 Quitting...")
        icon.stop()

    icon_image = Image.new("RGB", (64, 64), color=(0, 128, 255))
    icon = pystray.Icon("ScreenshotLogger", icon_image, "Screenshot Logger", menu=pystray.Menu(
        pystray.MenuItem("Start", lambda icon, item: Thread(target=loop_thread, daemon=True).start()),
        pystray.MenuItem("Quit", on_quit)
    ))
    icon.run()

if __name__ == "__main__":
    start_from_tray()
