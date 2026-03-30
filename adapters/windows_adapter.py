from .base_adapter import BaseAdapter
import subprocess
import os
import datetime

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
        # Adding .exe is a simple heuristic. A more robust solution
        # might involve checking running processes.
        os.system(f"taskkill /f /im {app_name}.exe")
        return f"{app_name} closed."

    def get_time(self):
        return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}."