"""
Process termination policy: block unsafe global (by-image-name) mass kills.

Terminal shells and host processes must be closed via focused-window / scoped
logic in ``adapters.terminal_windows``, not by iterating every matching PID.
"""

from __future__ import annotations

# Globally killing by executable name is forbidden for these — too many user sessions.
GLOBAL_PROCESS_KILL_BLOCKLIST: frozenset[str] = frozenset(
    {
        "powershell.exe",
        "pwsh.exe",
        "cmd.exe",
        "explorer.exe",
        "conhost.exe",
    }
)


def normalize_exe_name(name: str) -> str:
    n = name.strip().lower()
    if not n.endswith(".exe"):
        n += ".exe"
    return n


def is_global_mass_kill_blocked(exe_name: str) -> bool:
    return normalize_exe_name(exe_name) in GLOBAL_PROCESS_KILL_BLOCKLIST
