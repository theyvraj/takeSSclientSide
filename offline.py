import pyautogui
import base64
import io
from datetime import datetime
import time
import requests
import socket
import os

OFFLINE_QUEUE_DIR = "offline_queue"

def current_timestamp():
    return datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

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
    print(f"💾 Offline screenshot saved: {filepath}")

def encode_screenshot(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    base64_encoded = base64.b64encode(img_bytes).decode('utf-8')
    return base64_encoded

def send_screenshot_to_api(api_url, token, encoded_data, timestamp):
    headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
    payload = {"screenshot_json": {timestamp: encoded_data}}
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Screenshot sent:", response.json().get("saved_files"))
            return True
        else:
            print("❌ API Error:", response.status_code, response.text)
            return False
    except requests.exceptions.Timeout:
        print("⏳ Timeout! Could not send screenshot.")
    except Exception as e:
        print("❌ Error sending screenshot:", e)
    return False

def upload_offline_screenshots(api_url, token):
    if not os.path.exists(OFFLINE_QUEUE_DIR):
        return

    for file in os.listdir(OFFLINE_QUEUE_DIR):
        if not file.endswith(".png"):
            continue
        filepath = os.path.join(OFFLINE_QUEUE_DIR, file)
        try:
            with open(filepath, 'rb') as f:
                img_bytes = f.read()
            base64_encoded = base64.b64encode(img_bytes).decode('utf-8')
            raw_name = file.replace("screenshot_", "").replace(".png", "")
            try:
                datetime.strptime(raw_name, "%d-%m-%Y_%H-%M-%S")
            except ValueError:
                print(f"⚠️ Skipping file with invalid timestamp format: {file}")
                continue
            if send_screenshot_to_api(api_url, token, base64_encoded, raw_name):
                print(f"☁️ Uploaded offline screenshot: {file}")
                os.remove(filepath)
        except Exception as e:
            print(f"❌ Error uploading offline screenshot {file}: {e}")

def get_token(username, password, login_url):
    try:
        response = requests.post(login_url, data={'username': username, 'password': password}, timeout=10)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            print("🔐 Login failed:", response.status_code, response.text)
    except Exception as e:
        print("❌ Error logging in:", e)
    return None

def take_and_process_screenshot(api_url, token, save_local=True):
    screenshot = pyautogui.screenshot()
    timestamp = current_timestamp()

    if save_local:
        local_filename = f"screenshot_{timestamp}.png"
        screenshot.save(local_filename)
        print(f"📸 Saved locally as: {local_filename}")

    encoded_data = encode_screenshot(screenshot)
    success = send_screenshot_to_api(api_url, token, encoded_data, timestamp)

    if not success:
        save_offline_screenshot(screenshot, timestamp)

    return screenshot

def run_screenshot_loop(api_url, login_url, username, password, interval_minutes):
    token = get_token(username, password, login_url)
    if not token:
        print("❌ Could not authenticate. Exiting.")
        return

    print("🟢 Screenshot loop started. Press Ctrl+C to exit.")
    while True:
        try:
            istatus = check_internet()
            if istatus:
                print("🌐 Internet available. Uploading screenshot.")
                screenshot = take_and_process_screenshot(api_url, token, save_local=False)
                try:
                    upload_offline_screenshots(api_url, token)
                except Exception as e:
                    print(f"⚠️ Error uploading offline screenshots: {e}")
            else:
                print("📴 No internet. Screenshot saved.")
                screenshot = pyautogui.screenshot()
                save_offline_screenshot(screenshot, current_timestamp())
        except Exception as main_loop_error:
            print(f"🔥 Fatal error in main loop: {main_loop_error}")

        print(f"⏱ Waiting {interval_minutes} minute(s) before next screenshot...\n")
        time.sleep(interval_minutes * 60)

# ----------------------
if __name__ == "__main__":
    API_URL = "http://192.168.211.28:8000/api/screenshots/"
    LOGIN_URL = "http://192.168.211.28:8000/api/login/"
    USERNAME = input("Enter your username: ")
    PASSWORD = input("Enter your password: ")
    print("⏳ You have 5 seconds to minimize this window...")
    time.sleep(5)
    run_screenshot_loop(API_URL, LOGIN_URL, USERNAME, PASSWORD, interval_minutes=1)

input("Press Enter to exit...")
