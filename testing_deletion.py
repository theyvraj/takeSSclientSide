from datetime import datetime, timedelta
import os
import json

# Load timebreak data from idle_time.json
with open("idle_data.json", "r") as f:
    timebreak = json.load(f)

# Parse start and end times
start = datetime.fromisoformat(timebreak[0]['start_time'])
end = datetime.fromisoformat(timebreak[-1]['end_time'])

# Check if the duration is over 60 minutes
if end - start > timedelta(minutes=60):
    try:
        os.remove("idle_data.json")
        print("File 'idle_data.json' deleted.")
    except FileNotFoundError:
        print("File 'idle_data.json' does not exist.")
else:
    print("File was not deleted (duration under 60 minutes).")
