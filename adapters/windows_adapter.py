from .base_adapter import BaseAdapter
import subprocess
import os
import datetime
import psutil

CRITICAL_PROCESSES = [
    "explorer.exe",
    "winlogon.exe",
    "csrss.exe"
]
class WindowsAdapter(BaseAdapter):
    def execute_command(self, command: str):
        # Implementation for Windows Shell execution
        return f"Executing {command} on Windows"

    def get_status(self):
        return "Windows System Active"

    def open_app(self, app_name: str):
        try:
            os.startfile(app_name)
            return f"{app_name} opened."
        except OSError as e:
            return f"Error opening {app_name}: {e}"

    

    def close_app(self, app_name: str):
        target_app = app_name.lower()

        if not target_app.endswith('.exe'):
            target_app += '.exe'

        if target_app in CRITICAL_PROCESSES:
            return f"Blocked: {target_app} is a critical system process."

        found = False

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == target_app:
                    proc.terminate()  # graceful first
                    found = True

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if found:
            return f"{target_app} closed successfully."
        else:
            return f"{target_app} is not running."

    def get_time(self):
        return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}."

    def get_cpu_usage(self):
        usage = psutil.cpu_percent(interval=1)
        return f"Current CPU usage: {usage}%"

    def get_memory_usage(self):
        usage = psutil.virtual_memory().percent
        return f"Current Memory usage: {usage}%"