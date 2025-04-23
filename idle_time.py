# import json
# import time
# import os
# import ctypes
# from datetime import datetime

# class LASTINPUTINFO(ctypes.Structure):
#     _fields_ = [
#         ('cbSize', ctypes.c_uint),
#         ('dwTime', ctypes.c_uint),
#     ]

# def get_idle_time():
#     """Get the number of seconds the system has been idle"""
#     last_input_info = LASTINPUTINFO()
#     last_input_info.cbSize = ctypes.sizeof(last_input_info)
#     ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info))
#     millis = ctypes.windll.kernel32.GetTickCount() - last_input_info.dwTime
#     return millis / 1000.0  # Convert to seconds

# def load_idle_data():
#     """Load existing idle data from JSON file"""
#     if os.path.exists('idle_data.json'):
#         try:
#             with open('idle_data.json', 'r') as file:
#                 return json.load(file)
#         except json.JSONDecodeError:
#             print("Error reading idle_data.json, creating new data")
#     return []  # Return an empty list instead of a dictionary

# def save_idle_data(data):
#     """Save idle data to JSON file"""
#     with open('idle_data.json', 'w') as file:
#         json.dump(data, file, indent=4)

# def main():
#     # Define idle threshold (in seconds)
#     IDLE_THRESHOLD = 10  # Consider user idle after 60 seconds
#     CHECK_INTERVAL = 1  # Check every 2 minutes (120 seconds)
    
#     idle_data = load_idle_data()
#     current_session = None
    
#     print("Idle time monitoring started. Press Ctrl+C to exit.")
    
#     try:
#         while True:
#             idle_time = get_idle_time()
#             current_time = datetime.now().isoformat()
            
#             if idle_time >= IDLE_THRESHOLD:
#                 if current_session is None:
#                     # Start of a new idle session
#                     print(f"User went idle at {current_time}")
#                     current_session = {
#                         "start_time": current_time,
#                         "end_time": None
#                     }
#             elif current_session is not None:
#                 # User is active again, end the idle session
#                 current_session["end_time"] = current_time
#                 idle_data.append(current_session)  # Add directly to the list
#                 print(f"User returned at {current_time}. Idle session recorded.")
#                 save_idle_data(idle_data)
#                 current_session = None
            
#             time.sleep(CHECK_INTERVAL)
    
#     except KeyboardInterrupt:
#         # Handle case where script is terminated during an idle session
#         if current_session is not None:
#             current_session["end_time"] = datetime.now().isoformat()
#             current_session["end_time_note"] = "Script terminated during idle session"
#             idle_data.append(current_session)
        
#         save_idle_data(idle_data)
#         print("\nIdle time monitoring stopped. Data saved to idle_data.json")

# if __name__ == "__main__":
#     main()

# # time_in_seconds = 30000
# # minutes = time_in_seconds / 60
# # hr = minutes / 60
# # minutes = minutes % 60
# # print(f"{int(hr)} hours {int(minutes)} minutes")
from datetime import datetime,timedelta
timebreak = [
    {
        "start_time": "2025-04-23T13:19:38.749421",
        "end_time": "2025-04-23T13:19:45.755339"
    },
    {
        "start_time": "2025-04-23T13:30:54.277253",
        "end_time": "2025-04-23T13:31:03.282100"
    },
    {
        "start_time": "2025-04-23T13:31:22.293148",
        "end_time": "2025-04-23T14:31:26.295817"
    }
]
# if timebreak[-1]['end_time'] - timebreak[0]['start_time'] > 60:
if datetime.fromisoformat(timebreak[-1]['end_time']) - datetime.fromisoformat(timebreak[0]['start_time']) > timedelta(minutes=60):
    print("True")
else:
    print("False")