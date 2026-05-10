"""
Shared identifiers for terminal/shell processes (safe close & enumeration).

Used by ``terminal_windows``, ``terminal_trust``, and related adapters — not for mass kills.
"""

from __future__ import annotations

# Interactive shells (foreground-close Case A).
SHELL_EXECUTABLES: frozenset[str] = frozenset(
    {
        "powershell.exe",
        "pwsh.exe",
        "cmd.exe",
    }
)

WINDOWS_TERMINAL_HOSTS: frozenset[str] = frozenset({"windowsterminal.exe"})
CONHOST = "conhost.exe"

# Processes counted when listing terminal-like activity (observation only; never used to mass-kill).
OBSERVABLE_TERMINAL_EXES: frozenset[str] = (
    SHELL_EXECUTABLES | WINDOWS_TERMINAL_HOSTS | frozenset({"conhost.exe"})
)

TERMINAL_DISPLAY_LABELS: dict[str, str] = {
    "windowsterminal.exe": "Windows Terminal",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell (pwsh)",
    "cmd.exe": "Command Prompt",
    "conhost.exe": "Console host",
}


def exe_matches_close_request(request_key: str, exe_lower: str) -> bool:
    """Whether ``exe_lower`` satisfies a close phrase (``powershell``, ``terminal``, …)."""
    if request_key == "powershell":
        return exe_lower in ("powershell.exe", "pwsh.exe")
    if request_key == "pwsh":
        return exe_lower == "pwsh.exe"
    if request_key == "cmd":
        return exe_lower == "cmd.exe"
    if request_key == "terminal":
        return exe_lower in SHELL_EXECUTABLES or exe_lower in WINDOWS_TERMINAL_HOSTS
    return False
