import tkinter as tk
from tkinter import messagebox
def ask_yes_no(new_version):
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    message = f"New version {new_version} is available.\nDo you want to download it?"
    response = messagebox.askyesno("Update Available", message)
    return response
ask_yes_no("1.0.1")
