"""
Focused-window terminal handling on Windows.

Never performs taskkill / global PID enumeration by shell image name.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable

import psutil

from core.security.scoped_terminate import terminate_pid_scoped
from core.security.terminal_trust import append_workload_hint_if_any

from .terminal_constants import (
    CONHOST,
    SHELL_EXECUTABLES,
    WINDOWS_TERMINAL_HOSTS,
    exe_matches_close_request,
)

logger = logging.getLogger(__name__)


@dataclass
class TerminalLaunchResult:
    """Outcome of spawning a terminal via ``launch_terminal_app``."""

    message: str
    pid: int | None = None
    process_name: str | None = None
    launch_method: str = ""
    window_title: str | None = None

try:
    import win32gui
    import win32process
except ImportError:  # pragma: no cover - exercised when pywin32 missing
    win32gui = None
    win32process = None

TERMINAL_LAUNCH_COOLDOWN_SEC = 2.0


def try_focus_window_for_pid(pid: int) -> bool:
    """Bring a visible top-level window for ``pid`` to the foreground (best effort)."""
    if win32gui is None or win32process is None:
        return False
    found: list[int] = []

    def _enum(hwnd: int, _: object) -> bool:
        try:
            _, wpid = win32process.GetWindowThreadProcessId(hwnd)
            if int(wpid) == pid and win32gui.IsWindowVisible(hwnd):
                found.append(hwnd)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(_enum, None)
    except Exception:
        return False
    if not found:
        return False
    try:
        win32gui.SetForegroundWindow(found[0])
        return True
    except Exception:
        return False


def try_window_title_for_pid(pid: int) -> str | None:
    """Best-effort main window title for a process (first visible window)."""
    if win32gui is None or win32process is None:
        return None
    found: list[str] = []

    def _enum(hwnd: int, _: object) -> bool:
        try:
            _, wpid = win32process.GetWindowThreadProcessId(hwnd)
            if int(wpid) == pid and win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    found.append(t)
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(_enum, None)
    except Exception:
        return None
    return found[0] if found else None


def _get_foreground_pid() -> tuple[int | None, str | None]:
    if win32gui is None or win32process is None:
        return None, (
            "Terminal close requires pywin32 (win32gui). Install pywin32 on Windows."
        )
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None, "No foreground window — focus a terminal or use an assistant-opened session first."
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return int(pid), None


def try_get_foreground_pid() -> int | None:
    """
    Foreground process PID for UX only (e.g. ordering disambiguation lists).

    Returns ``None`` when pywin32 is missing or there is no foreground window —
    callers treat that as \"unknown focus\".
    """
    pid, err = _get_foreground_pid()
    if err is not None or pid is None:
        return None
    return pid


def _shell_children_recursive(host_pid: int) -> list[psutil.Process]:
    found: list[psutil.Process] = []
    try:
        root = psutil.Process(host_pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return found
    try:
        for ch in root.children(recursive=True):
            try:
                n = ch.name().lower()
                if n in SHELL_EXECUTABLES:
                    found.append(ch)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return found


def _maybe_risk_gate(
    risk_gate: Callable[[int], str | None] | None, target_pid: int
) -> str | None:
    if risk_gate is None:
        return None
    return risk_gate(target_pid)


def _filter_shells_for_request(
    request_key: str, shells: list[psutil.Process]
) -> list[psutil.Process]:
    out: list[psutil.Process] = []
    for p in shells:
        try:
            n = p.name().lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        if exe_matches_close_request(request_key, n):
            out.append(p)
    return out


def close_focused_terminal_session(
    request_key: str,
    *,
    risk_gate: Callable[[int], str | None] | None = None,
) -> str:
    """
    Close exactly one terminal-related process: the focused shell, or a single
    matching descendant when the foreground window is Windows Terminal / ConHost.

    ``request_key``: ``powershell`` | ``pwsh`` | ``cmd`` | ``terminal``

    ``risk_gate``: if set, called with the PID about to be terminated; returning a
    non-empty string cancels the kill and shows that message (e.g. yes/no confirmation).
    """
    pid, err = _get_foreground_pid()
    if err:
        return err
    assert pid is not None

    try:
        proc = psutil.Process(pid)
        foreground_name = proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return f"Could not inspect foreground process: {e}"

    # Case A: foreground is already an interactive shell — verify label matches user intent.
    if foreground_name in SHELL_EXECUTABLES:
        if not exe_matches_close_request(request_key, foreground_name):
            return (
                f"The focused window is {foreground_name}. It does not match "
                f'"{request_key}". Click the terminal you want to close, then try again.'
            )
        gated = _maybe_risk_gate(risk_gate, pid)
        if gated is not None:
            return gated
        err = terminate_pid_scoped(pid)
        if err is not None:
            return err
        return append_workload_hint_if_any(
            pid,
            f"Closed focused session ({foreground_name}, PID {pid}).",
        )

    # Case B: Windows Terminal — never kill the host PID; target shell children only.
    if foreground_name in WINDOWS_TERMINAL_HOSTS:
        shells = _shell_children_recursive(pid)
        if request_key == "terminal":
            return _terminate_single_or_ambiguous(shells, "shell tab", risk_gate)
        matching = _filter_shells_for_request(request_key, shells)
        return _terminate_one_or_explain(matching, request_key, risk_gate)

    # Case C: Console host — shell often appears as a descendant.
    if foreground_name == CONHOST:
        shells = _shell_children_recursive(pid)
        matching = (
            _filter_shells_for_request(request_key, shells)
            if request_key != "terminal"
            else shells
        )
        if request_key == "terminal":
            return _terminate_single_or_ambiguous(shells, "console session", risk_gate)
        return _terminate_one_or_explain(matching, request_key, risk_gate)

    return (
        f"The focused window isn't a terminal ({foreground_name}). "
        f"Click a terminal window, or close one the assistant opened."
    )


def _terminate_single_or_ambiguous(
    shells: list[psutil.Process],
    kind_label: str,
    risk_gate: Callable[[int], str | None] | None = None,
) -> str:
    if len(shells) == 0:
        return f"No shell process found for this {kind_label}."
    if len(shells) > 1:
        return (
            f"Several shell sessions are open in this {kind_label}. "
            "Click inside the tab you want to close, then try again."
        )
    p = shells[0]
    try:
        name = p.name()
        spid = p.pid
        gated = _maybe_risk_gate(risk_gate, spid)
        if gated is not None:
            return gated
        err = terminate_pid_scoped(spid)
        if err is not None:
            return err
        return append_workload_hint_if_any(
            spid,
            f"Closed focused shell session ({name}, PID {spid}).",
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return f"Could not terminate shell: {e}"


def _terminate_one_or_explain(
    matches: list[psutil.Process],
    request_key: str,
    risk_gate: Callable[[int], str | None] | None = None,
) -> str:
    if len(matches) == 0:
        return (
            f"No matching {request_key} session found inside the focused terminal window."
        )
    if len(matches) > 1:
        return (
            f"Multiple {request_key} sessions found — click inside the tab you want to close, "
            "then try again."
        )
    p = matches[0]
    try:
        name = p.name()
        spid = p.pid
        gated = _maybe_risk_gate(risk_gate, spid)
        if gated is not None:
            return gated
        err = terminate_pid_scoped(spid)
        if err is not None:
            return err
        return append_workload_hint_if_any(spid, f"Closed {name} (PID {spid}).")
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return f"Could not terminate process: {e}"


# --- Opening terminals (debounce enforced by caller) ---


def normalize_terminal_open_target(app_name: str) -> str | None:
    """Map user target string to a canonical launch key, or None for generic open."""
    raw = app_name.strip().lower()
    raw = raw.removesuffix(".exe")
    compact = raw.replace(" ", "")
    if compact in ("powershell", "powershell_ise"):
        return "powershell"
    if compact in ("pwsh", "powershellcore"):
        return "pwsh"
    if compact in ("windowsterminal", "wt", "terminal"):
        return "terminal"
    if raw in ("windows terminal",):
        return "terminal"
    return None


def launch_terminal_app(
    canonical: str,
    *,
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
    which: Callable[[str], str | None] = shutil.which,
    monotonic: Callable[[], float] = time.monotonic,
) -> TerminalLaunchResult:
    """
    Launch one new terminal session (Windows Terminal preferred when available).

    Returns PID of the spawned top-level process for session tracking. Caller debounces.
    """
    _ = monotonic
    creationflags = subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0

    wt = which("wt.exe")
    if canonical == "powershell":
        if wt:
            proc = popen([wt, "-p", "Windows PowerShell"], creationflags=creationflags)
            time.sleep(0.08)
            pid = proc.pid
            pname = _safe_process_name(pid)
            try_focus_window_for_pid(pid)
            title = try_window_title_for_pid(pid)
            return TerminalLaunchResult(
                message="Opened Windows Terminal.",
                pid=pid,
                process_name=pname,
                launch_method='wt.exe -p "Windows PowerShell"',
                window_title=title,
            )
        ps = which("powershell.exe")
        exe = ps or "powershell.exe"
        proc = popen([exe], creationflags=creationflags)
        time.sleep(0.08)
        pid = proc.pid
        pname = _safe_process_name(pid)
        try_focus_window_for_pid(pid)
        return TerminalLaunchResult(
            message="Opened PowerShell.",
            pid=pid,
            process_name=pname,
            launch_method="powershell.exe",
        )

    if canonical == "pwsh":
        pw = which("pwsh.exe")
        if pw:
            proc = popen([pw], creationflags=creationflags)
            time.sleep(0.08)
            pid = proc.pid
            pname = _safe_process_name(pid)
            try_focus_window_for_pid(pid)
            return TerminalLaunchResult(
                message="Opened PowerShell (pwsh).",
                pid=pid,
                process_name=pname,
                launch_method="pwsh.exe",
            )
        return TerminalLaunchResult(message="pwsh.exe not found on PATH.")

    if canonical == "terminal":
        if wt:
            proc = popen([wt], creationflags=creationflags)
            time.sleep(0.08)
            pid = proc.pid
            pname = _safe_process_name(pid)
            try_focus_window_for_pid(pid)
            return TerminalLaunchResult(
                message="Opened Windows Terminal.",
                pid=pid,
                process_name=pname,
                launch_method="wt.exe",
            )
        return TerminalLaunchResult(
            message="Windows Terminal (wt.exe) not found. Try 'open powershell' instead."
        )

    logger.warning("launch_terminal_app: unknown canonical %r", canonical)
    return TerminalLaunchResult(message="Internal error: unknown terminal launch type.")


def _safe_process_name(pid: int) -> str | None:
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
