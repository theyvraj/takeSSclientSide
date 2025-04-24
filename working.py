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
import uuid
import getpass
import json
import shutil

# --- Configuration ---
SCREENSHOTS_DIR = "screenshots"
OFFLINE_QUEUE_DIR = "offline_queue"
IDLE_DATA_DIR = "idle_data"
LOG_FILE = "screenshot_logger.log"
MAX_LOG_SIZE = 1_000_000
BACKUP_COUNT = 5

API_URL = "http://192.168.211.28:8000/api/screenshots/"
LOGIN_URL = "http://192.168.211.28:8000/api/login/"
LOG_URL = "http://192.168.211.28:8000/api/logs/"
IDLE_DATA_URL = "http://192.168.211.28:8000/api/idle_data/"  # New endpoint for idle data

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

def ensure_dirs():
    """Ensure all required directories exist"""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    os.makedirs(OFFLINE_QUEUE_DIR, exist_ok=True)
    
    # Create user-specific idle data directory
    user_idle_dir = os.path.join(IDLE_DATA_DIR, get_system_username_uuid())
    os.makedirs(user_idle_dir, exist_ok=True)
    return user_idle_dir

def save_offline_screenshot(screenshot, timestamp):
    """Save screenshot to offline queue"""
    ensure_dirs()
    filepath = os.path.join(OFFLINE_QUEUE_DIR, f"screenshot_{timestamp}.png")
    screenshot.save(filepath)
    log(f"💾 Offline copy saved: {filepath}")
    return filepath

def save_screenshot(screenshot, timestamp):
    """Save screenshot to screenshots directory"""
    ensure_dirs()
    filepath = os.path.join(SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
    screenshot.save(filepath)
    log(f"🖼️ Screenshot saved to: {filepath}")
    return filepath

def encode_screenshot(screenshot):
    """Encode screenshot to base64"""
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

def get_recent_logs():
    """Get recent logs from log file"""
    if not os.path.exists(LOG_FILE):
        return ""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[LogError] Could not read logs: {str(e)}"

def save_idle_data(idle_data):
    """Save idle data to user-specific file"""
    user_idle_dir = ensure_dirs()
    idle_file_path = os.path.join(user_idle_dir, "idle_data.json")
    
    # Create a temporary file first to avoid file access issues
    temp_file_path = os.path.join(user_idle_dir, "idle_data_temp.json")
    
    try:
        with open(temp_file_path, 'w') as f:
            json.dump(idle_data, f)
        
        # Replace the original file with the temp file
        shutil.move(temp_file_path, idle_file_path)
        log(f"💾 Idle data saved to {idle_file_path}")
        return idle_file_path
    except Exception as e:
        log(f"⚠️ Error saving idle data: {str(e)}")
        return None

def send_idle_data_to_api(api_url, token, idle_data_path):
    """Send idle data to API"""
    if not os.path.exists(idle_data_path):
        log(f"⚠️ Idle data file not found: {idle_data_path}")
        return False
    
    try:
        with open(idle_data_path, 'r') as f:
            idle_data = json.load(f)
        
        headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
        payload = {
            "user_id": get_system_username_uuid(),
            "idle_data": idle_data
        }
        
        response = requests.post(IDLE_DATA_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            log("📤 Idle data uploaded successfully.")
            return True
        else:
            log(f"⚠️ Idle data upload error: {response.status_code} {response.text}")
            return False
    except Exception as e:
        log(f"⚠️ Idle data upload error: {str(e)}")
        return False

def send_screenshot_to_api(api_url, token, encoded_data, timestamp, log_text):
    """Send screenshot and logs to API"""
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    payload = {
        "screenshot_json": {timestamp: encoded_data},
        "log_text": log_text,
        "user_id": get_system_username_uuid()
    }
    
    log("⏳ Sending screenshot and logs to API.")
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            log("✅ Screenshot + logs sent.")
            log("☁️ Screenshot and logs sent successfully.")
            return True
        else:
            log(f"❌ API Error: {response.status_code} {response.text}")
            return False
    except Exception as e:
        log(f"❌ Error sending screenshot: {e}")
        return False

def get_token(username, login_url):
    """Get authentication token from API"""
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
    """Send all offline screenshots to API"""
    ensure_dirs()
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
                        log(f"✅ Offline screenshot sent and deleted from queue: {filename}")
                    else:
                        log(f"⚠️ Failed to send offline screenshot: {filename}")
            except Exception as e:
                log(f"❌ Error processing offline screenshot {filename}: {e}")

def track_idle_time():
    """Track user idle time"""
    from ctypes import Structure, windll, c_uint, sizeof, byref
    
    class LASTINPUTINFO(Structure):
        _fields_ = [
            ('cbSize', c_uint),
            ('dwTime', c_uint),
        ]
    
    def get_idle_duration():
        lastInputInfo = LASTINPUTINFO()
        lastInputInfo.cbSize = sizeof(lastInputInfo)
        windll.user32.GetLastInputInfo(byref(lastInputInfo))
        millis = windll.kernel32.GetTickCount() - lastInputInfo.dwTime
        return millis / 1000.0  # Convert to seconds
    
    idle_threshold = 60  # seconds
    is_idle = False
    idle_start_time = None
    idle_data = {"idle_periods": []}
    
    while True:
        try:
            idle_duration = get_idle_duration()
            
            if not is_idle and idle_duration > idle_threshold:
                # User just went idle
                idle_start_time = datetime.now()
                is_idle = True
                log(f"⏸️ User went idle at {idle_start_time}")
            
            elif is_idle and idle_duration < idle_threshold:
                # User returned from idle
                idle_end_time = datetime.now()
                idle_period_seconds = (idle_end_time - idle_start_time).total_seconds()
                
                # Record the idle period
                idle_data["idle_periods"].append({
                    "start": idle_start_time.isoformat(),
                    "end": idle_end_time.isoformat(),
                    "duration_seconds": idle_period_seconds
                })
                
                log(f"▶️ User returned from idle at {idle_end_time}. Idle duration: {idle_period_seconds:.2f} seconds")
                is_idle = False
                
                # Save idle data to file
                idle_file_path = save_idle_data(idle_data)
        
        except Exception as e:
            log(f"⚠️ Error tracking idle time: {str(e)}")
        
        time.sleep(5)  # Check every 5 seconds

def authenticate_with_retries(max_retries=5, retry_delay=30):
    """Authenticate with API with retries"""
    system_user_uuid = get_system_username_uuid()
    
    for attempt in range(max_retries):
        log("🔄 Attempting to authenticate with API...")
        
        if not check_internet():
            log(f"📴 No internet connection. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue
        
        token = get_token(system_user_uuid, LOGIN_URL)
        if token:
            return token
        
        time.sleep(retry_delay)
    
    # If we get here, authentication failed after all retries
    log("❌ Authentication failed after multiple attempts.")
    return None

def run_loop(api_url, login_url, interval_seconds=30):
    """Main screenshot loop"""
    token = authenticate_with_retries()
    if not token:
        log("❌ Authentication failed. Exiting.")
        return

    # Start idle time tracking in a separate thread
    idle_thread = Thread(target=track_idle_time, daemon=True)
    idle_thread.start()

    log("🟢 Screenshot loop started.")
    while True:
        try:
            screenshot = pyautogui.screenshot()
            timestamp = current_timestamp()
            
            # Always save locally
            save_screenshot(screenshot, timestamp)
            
            if check_internet():
                log("🌐 Internet available.")
                
                # Try to send any offline screenshots first
                send_offline_screenshots(api_url, token)
                
                # Send current screenshot
                encoded = encode_screenshot(screenshot)
                log_text = get_recent_logs()
                
                if not send_screenshot_to_api(api_url, token, encoded, timestamp, log_text):
                    # If sending fails, save offline
                    log("📴 No internet. Saving offline.")
                    save_offline_screenshot(screenshot, timestamp)
            else:
                log("📴 No internet. Saving offline.")
                save_offline_screenshot(screenshot, timestamp)
                
        except Exception as e:
            log(f"🔥 Fatal loop error: {e}")
        
        time.sleep(interval_seconds)

if __name__ == "__main__":
    run_loop(API_URL, LOGIN_URL)