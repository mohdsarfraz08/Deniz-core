"""
Linux integration: core intents (apps, metrics, file managers).

Terminal disambiguation, risky-close confirmation, and session-registry terminal
tracking are Windows-only in v1. This adapter does not expose pending resolvers.
"""

from __future__ import annotations

import datetime
import shutil
import subprocess

import psutil

from .base_adapter import BaseAdapter
from core.action_results import CloseFileExplorerWindowsResult
from core.security.process_kill_policy import is_global_mass_kill_blocked, normalize_exe_name
from core.session.app_registry import SessionRegistry

# Process names (lowercase) that must not be closed by generic name iteration.
CRITICAL_PROCESSES: frozenset[str] = frozenset(
    {
        "systemd",
        "init",
        "kernel",
        "kthreadd",
        "sshd",
    }
)

# File-manager processes closed by ``close_file_explorer_windows`` (process-level, not per-window).
FILE_MANAGER_PROCESSES: frozenset[str] = frozenset(
    {
        "nautilus",
        "nautilus-desktop",
        "dolphin",
        "dolphin-bin",
        "thunar",
        "nemo",
        "pcmanfm",
    }
)


class LinuxAdapter(BaseAdapter):
    """Minimal Linux ``BaseAdapter`` for core CLI intents."""

    def __init__(self, session_registry: SessionRegistry | None = None) -> None:
        self._session_registry = session_registry  # reserved for future parity

    def execute_command(self, command: str) -> str:
        return f"Executing {command} on Linux"

    def get_status(self) -> str:
        return "Linux System Active"

    def open_app(self, app_name: str) -> str:
        name = app_name.strip()
        if not name:
            return "Error opening : empty name"

        executable = shutil.which(name)
        if executable:
            try:
                subprocess.Popen(
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"{name} opened."
            except OSError as e:
                return f"Error opening {name}: {e}"

        xdg = shutil.which("xdg-open")
        if xdg:
            try:
                subprocess.Popen(
                    [xdg, name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"{name} opened."
            except OSError as e:
                return f"Error opening {name}: {e}"

        return f"Error opening {name}: application not found in PATH"

    def close_app(self, app_name: str) -> str:
        target = app_name.strip().lower()
        if target.endswith(".exe"):
            target = target[: -len(".exe")]

        if target in CRITICAL_PROCESSES:
            return f"Blocked: {target} is a critical system process."

        exe_norm = normalize_exe_name(target)
        if is_global_mass_kill_blocked(exe_norm):
            return (
                "Can't close every running instance of that program by name. "
                "Focus the window you mean to close."
            )

        found = False
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                base = pname.removesuffix(".exe")
                if base == target or pname == target:
                    proc.terminate()
                    found = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if found:
            return f"{target} closed successfully."
        return f"{target} is not running."

    def close_file_explorer_windows(self) -> CloseFileExplorerWindowsResult:
        """
        Terminate file-manager processes (Nautilus, Dolphin, etc.).

        Unlike Windows, this does not close individual folder windows via Shell COM.
        """
        closed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                base = pname.removesuffix(".exe")
                if base in FILE_MANAGER_PROCESSES or pname in FILE_MANAGER_PROCESSES:
                    proc.terminate()
                    closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return {
            "status": "success",
            "action": "close_file_explorer_windows",
            "count": closed,
        }

    def get_time(self) -> str:
        return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}."

    def get_cpu_usage(self) -> str:
        usage = psutil.cpu_percent(interval=1)
        return f"Current CPU usage: {usage}%"

    def get_memory_usage(self) -> str:
        usage = psutil.virtual_memory().percent
        return f"Current Memory usage: {usage}%"
