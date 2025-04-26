"""

import os
import time
import json
import base64
import requests
import pyautogui
import datetime
import ctypes
import psutil
from pathlib import Path

# Configurations
SERVER_URL = "https://rankfiller.com/seotools/api"
SCREENSHOT_ENDPOINT = f"{SERVER_URL}/timetrackerscreen/"
ERROR_LOG_ENDPOINT = f"{SERVER_URL}/timeerrorlog/"
UPDATE_CHECK_ENDPOINT = f"{SERVER_URL}/autoupdate/"
APP_NAME = "ssTaker"
VERSION = "2.3"

# Local storage paths
LOCAL_DATA_DIR = Path(__file__).parent / "local_cache"
SCREENSHOTS_FILE = LOCAL_DATA_DIR / "pending_screenshots.json"
ERRORS_FILE = LOCAL_DATA_DIR / "error_log.json"

# Ensure local cache directory exists
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Setup user (e.g., UUID or username)
def get_username():
    return os.getenv("COMPUTERNAME") or "UnknownUser"

USERNAME = get_username()

# ---------------- Utility Functions ----------------

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

def log_error(message):
    timestamp = datetime.datetime.now().isoformat()
    entry = {"timestamp": timestamp, "user": USERNAME, "error": message}
    with open(ERRORS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def capture_screenshot():
    timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    screenshot = pyautogui.screenshot()
    screenshot_bytes = screenshot.tobytes()
    buffered = screenshot.tobytes()
    encoded = base64.b64encode(screenshot.tobytes()).decode("utf-8")
    return {timestamp: encoded}

def get_idle_time():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis // 1000

def get_activity_log():
    now = datetime.datetime.now()
    start = (now - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    end = now.strftime("%Y-%m-%d %H:%M:%S")
    return [{"start_time": start, "end_time": end}]

# ---------------- Data Handling ----------------

def queue_data(screenshot_dict, activity_log):
    payload = {
        "user": USERNAME,
        "datetime": datetime.datetime.now().isoformat(),
        "screenshots": [{k: v} for k, v in screenshot_dict.items()],
        "activity_log": activity_log
    }

    data = []
    if SCREENSHOTS_FILE.exists():
        with open(SCREENSHOTS_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []

    data.append(payload)
    with open(SCREENSHOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def flush_data():
    if not SCREENSHOTS_FILE.exists():
        return

    with open(SCREENSHOTS_FILE, "r", encoding="utf-8") as f:
        try:
            payloads = json.load(f)
        except json.JSONDecodeError:
            log_error("Failed to decode pending_screenshots.json")
            return

    remaining = []
    for payload in payloads:
        try:
            response = requests.post(SCREENSHOT_ENDPOINT, json=payload, timeout=15)
            if response.status_code != 200:
                remaining.append(payload)
        except Exception as e:
            log_error(str(e))
            remaining.append(payload)

    with open(SCREENSHOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(remaining, f, indent=2)

def flush_errors():
    if not ERRORS_FILE.exists():
        return

    with open(ERRORS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        try:
            error_entry = json.loads(line)
            payload = {
                "user": error_entry.get("user", USERNAME),
                "errorlog": error_entry.get("error", "")
            }
            requests.post(ERROR_LOG_ENDPOINT, json=payload)
        except Exception as e:
            log_error(f"Failed to send error log: {str(e)}")

    # Clear after successful send
    ERRORS_FILE.unlink(missing_ok=True)

def check_for_update():
    try:
        response = requests.post(UPDATE_CHECK_ENDPOINT, data={"appname": APP_NAME})
        if response.status_code == 200:
            data = response.json().get("data", {})
            new_version = data.get("version")
            url = data.get("url")
            if new_version and new_version != VERSION:
                print(f"New version available: {new_version}. Downloading from {url}...")
                response = requests.get(url)
                if response.status_code == 200:
                    with open("updated_app.exe", "wb") as f:
                        f.write(response.content)
                    print("Update downloaded.")
        else:
            log_error("Update check failed.")
    except Exception as e:
        log_error(f"Update check error: {str(e)}")

# ---------------- Main Loop ----------------

def main():
    print(f"Time Tracker started for user: {USERNAME}")
    screenshot_interval = 60  # seconds
    last_check = time.time()

    while True:
        try:
            screenshot = capture_screenshot()
            activity_log = get_activity_log()
            idle_time = get_idle_time()

            print(f"Idle Time: {idle_time}s | Saving screenshot and activity log...")

            queue_data(screenshot, activity_log)

            if is_connected():
                flush_data()
                flush_errors()
                if time.time() - last_check > 300:
                    check_for_update()
                    last_check = time.time()

        except Exception as e:
            log_error(f"Main loop error: {str(e)}")

        time.sleep(screenshot_interval)

if __name__ == "__main__":
    main()
"""


"""
import os
import json
import base64
from datetime import datetime
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import timetrack_User, timetracker, timetracking_log, timetrack_error, timetracker_setting, AutoUpdateExe


@csrf_exempt
def doctortimescreens(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('user', '')
            activity_datetime = data.get('datetime', '')
            screenshots = data.get('screenshots', [])
            activity_logs = data.get('activity_log', [])

            # Get or create user
            user_obj, _ = timetrack_User.objects.get_or_create(
                user_name=username,
                defaults={'created_at': datetime.now()}
            )

            # Check if tracking is enabled
            if user_obj.trackstatus:
                date_folder = datetime.now().strftime('%Y-%m-%d')
                user_dir = os.path.join(settings.MEDIA_ROOT, 'screens', username, date_folder)
                os.makedirs(user_dir, exist_ok=True)

                # Save activity logs
                for log in activity_logs:
                    start = log.get("start_time")
                    if not timetracking_log.objects.filter(user_id=user_obj, activity_start=start).exists():
                        timetracking_log.objects.create(
                            user_id=user_obj,
                            activity_start=start,
                            activity_end=log.get("end_time")
                        )

                # Save screenshots
                for entry in screenshots:
                    for timestamp, encoded_img in entry.items():
                        filename = f"screenshot_{timestamp}.png"
                        filepath = os.path.join(user_dir, filename)

                        with open(filepath, 'wb') as img_file:
                            img_file.write(base64.b64decode(encoded_img))

                        timetracker.objects.create(
                            user_id=user_obj,
                            activity_date=timestamp,
                            screenshot_data=filename
                        )

            # Send current settings back to client
            settings_obj = timetracker_setting.objects.first()
            data = {
                "status": user_obj.trackstatus,
                "screen_shot_time": settings_obj.screenshot_time,
                "log_time": settings_obj.log_time,
                "update_time": settings_obj.update_time,
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
def doctortimeerrorlog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))
            username = data.get('user', '')
            errorlog = data.get('errorlog', '')

            user_obj, _ = timetrack_User.objects.get_or_create(
                user_name=username,
                defaults={'created_at': datetime.now()}
            )

            if 'Permission denied' not in errorlog:
                timetrack_error.objects.create(
                    user_id=user_obj,
                    error_log=errorlog,
                    created_at=datetime.now()
                )

            return JsonResponse({"status": "logged"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)


@csrf_exempt
def check_autoupdate(request):
    if request.method == "POST":
        try:
            app_name = request.POST.get("appname")
            latest_version = AutoUpdateExe.objects.filter(
                select_app=app_name
            ).order_by('-app_version').first()

            if latest_version and latest_version.exe_file:
                download_url = request.build_absolute_uri(latest_version.exe_file.url)
                return JsonResponse({
                    "data": {
                        "url": download_url,
                        "version": latest_version.app_version
                    }
                })
            else:
                return JsonResponse({"data": {"url": None, "version": None}})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid method"}, status=405)




"""


"""

from django.urls import path
from . import views

urlpatterns = [
    path('api/timetrackerscreen/', views.doctortimescreens),
    path('api/timeerrorlog/', views.doctortimeerrorlog),
    path('api/autoupdate/', views.check_autoupdate),
]


"""




"""

from django.contrib import admin
from .models import timetrack_User, timetracking_log, timetracker_setting, timetrack_error

@admin.register(timetrack_User)
class TimeTrackUserAdmin(admin.ModelAdmin):
    list_display = ("user_name", "shortname", "department", "location", "status", "trackstatus", "created_at")
    search_fields = ("user_name", "shortname", "location")
    list_filter = ("status", "trackstatus", "department")


@admin.register(timetracking_log)
class TimeTrackingLogAdmin(admin.ModelAdmin):
    list_display = ("user_id", "activity_start", "activity_end")
    search_fields = ("user_id__user_name",)
    list_filter = ("activity_start",)


@admin.register(timetracker_setting)
class TimeTrackerSettingAdmin(admin.ModelAdmin):
    list_display = ("screenshot_time", "log_time", "update_time")
    readonly_fields = ("id",)


@admin.register(timetrack_error)
class TimeTrackErrorAdmin(admin.ModelAdmin):
    list_display = ("user_id", "error_log", "created_at")
    search_fields = ("user_id__user_name", "error_log")
    list_filter = ("created_at",)


"""




"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('yourappname.urls')),  # 👈 Connect your app urls
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


"""





"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'your-super-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # Change in production

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'yourappname',  # 👈 Add your app name here
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'yourprojectname.urls'  # 👈 your project folder name

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'yourprojectname.wsgi.application'

# Database
# Using SQLite for now
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'  # Change if needed
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'

# Media files (screenshots, logs)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



"""