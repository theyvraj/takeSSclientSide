import pyautogui
import base64
import io
from datetime import datetime
import time
import requests
import socket
import os
import json


OFFLINE_QUEUE_DIR = "offline_queue"
def check_internet(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False 

def save_offline_screenshot(screenshot, timestamp):
    if not os.path.exists(OFFLINE_QUEUE_DIR):
        os.makedirs(OFFLINE_QUEUE_DIR)
    filename = f"{OFFLINE_QUEUE_DIR}/screenshot_{timestamp}.png"
    screenshot.save(filename)
    print(f"💾 Offline screenshot saved: {filename}")

def upload_offline_screenshots(api_url, token):
    if not os.path.exists(OFFLINE_QUEUE_DIR):
        return

    headers = {"Authorization": f"Token {token}"}
    files = os.listdir(OFFLINE_QUEUE_DIR)
    png_files = [f for f in files if f.endswith(".png")]

    for file in png_files:
        filepath = os.path.join(OFFLINE_QUEUE_DIR, file)
        try:
            with open(filepath, 'rb') as img_file:
                img_bytes = img_file.read()
                base64_encoded = base64.b64encode(img_bytes).decode('utf-8')
                timestamp = file.replace("screenshot_", "").replace(".png", "")
                payload = {
                    "screenshot_json": {
                        timestamp: base64_encoded
                    }
                }
                response = requests.post(api_url, json=payload, headers=headers)

                if response.status_code == 200:
                    print(f"☁️ Uploaded offline screenshot: {file}")
                    os.remove(filepath)
                else:
                    print(f"⚠️ Failed to upload {file}: {response.status_code} {response.text}")
        except Exception as e:
            print(f"❌ Error uploading offline screenshot {file}: {e}")


def encode_screenshot(screenshot):
    img_byte_arr = io.BytesIO()
    screenshot.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    base64_encoded = base64.b64encode(img_bytes)
    utf8_string = base64_encoded.decode('utf-8')
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    return {timestamp: utf8_string}

def get_token(username, password, login_url):
    try:
        response = requests.post(login_url, data={'username': username, 'password': password})
        if response.status_code == 200:
            return response.json().get('token')
        else:
            print("Login failed:", response.status_code, response.text)
            return None
    except Exception as e:
        print("Error logging in:", e)
        return None

def take_single_screenshot_and_send_to_api(api_url, token):
    screenshot = pyautogui.screenshot()

    # Save locally
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    filename = f"screenshot_{timestamp}.png"
    screenshot.save(filename)
    print(f"📸 Saved locally as: {filename}")

    # Encode and send to API
    json_data = encode_screenshot(screenshot)
    full_payload = {"screenshot_json": json_data}
    headers = {"Authorization": f"Token {token}"}

    try:
        response = requests.post(api_url, json=full_payload, headers=headers)
        if response.status_code == 200:
            print("\u2705 Screenshot sent:", response.json().get("saved_files"))
        else:
            print("\u274C Error:", response.status_code, response.text)
    except Exception as e:
        print("Error sending screenshot:", e)

def run_screenshot_loop(api_url, login_url, username, password, interval_minutes):
    token = get_token(username, password, login_url)
    if not token:
        print("\u274C Could not authenticate. Exiting.")
        return

    while True:
        istatus = check_internet()
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        screenshot = pyautogui.screenshot()

        if istatus:
            print("🌐 Internet available. Taking and uploading screenshot.")
            take_single_screenshot_and_send_to_api(api_url, token)
            upload_offline_screenshots(api_url, token)  # Try uploading any offline ones
        else:
            print("📴 Offline. Saving screenshot locally.")
            save_offline_screenshot(screenshot, timestamp)
            time.sleep(5)

        time.sleep(interval_minutes * 10)


if __name__ == "__main__":
    API_URL = "http://192.168.211.28:8000/api/screenshots/"
    LOGIN_URL = "http://192.168.211.28:8000/api/login/"
    USERNAME = input("Enter your username: ")
    PASSWORD = input("Enter your password: ")
    print("\U0001F552 You have 5 seconds to minimize this window...")
    time.sleep(5)
    run_screenshot_loop(API_URL, LOGIN_URL, USERNAME, PASSWORD, interval_minutes=1)

ex = input("Press Enter to exit...")