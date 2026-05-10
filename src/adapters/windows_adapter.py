from __future__ import annotations

import datetime
import os
import time
from dataclasses import dataclass

import psutil

from .base_adapter import BaseAdapter
from .terminal_windows import (
    TERMINAL_LAUNCH_COOLDOWN_SEC,
    TerminalLaunchResult,
    close_focused_terminal_session,
    launch_terminal_app,
    normalize_terminal_open_target,
    try_get_foreground_pid,
    try_window_title_for_pid,
)
from core.executor.window_executor import close_file_explorer_windows_impl
from core.intent_resolution import terminal_close_request_key
from core.security.process_kill_policy import is_global_mass_kill_blocked, normalize_exe_name
from core.security.terminal_trust import (
    RiskLevel,
    analyze_terminal_workload,
    append_workload_hint_if_any,
    format_close_confirmation_prompt,
    format_single_terminal_need_focus,
    is_assistant_owned_session,
    list_observable_terminal_sessions,
    workload_requires_close_confirmation,
)
from core.security.scoped_terminate import terminate_pid_scoped
from core.security.terminal_session_analysis import analyze_sessions_for_disambiguation
from core.session.app_registry import SessionRegistry
from core.session.pending_terminal_disambiguation import (
    DisambiguationResolveKind,
    PendingTerminalDisambiguation,
    TerminalDisambiguationOption,
    format_disambiguation_prompt,
    options_from_session_infos,
    resolve_terminal_disambiguation_followup,
)

CRITICAL_PROCESSES = [
    "explorer.exe",
    "winlogon.exe",
    "csrss.exe",
]


@dataclass
class PendingRiskyClose:
    """User must answer yes/no on the next turn before we terminate ``pid``."""

    pid: int
    risk_level: RiskLevel
    workload_lines: list[str]


class WindowsAdapter(BaseAdapter):
    """
    Windows integration: apps, metrics, and session-aware terminal management.

    Pass a shared :class:`SessionRegistry` from :class:`AssistantEngine` so opens/closes
    are tracked across commands.
    """

    def __init__(self, session_registry: SessionRegistry | None = None) -> None:
        self._session_registry = (
            session_registry if session_registry is not None else SessionRegistry()
        )
        self._last_terminal_launch_mono: float = 0.0
        self._last_terminal_launch_key: str | None = None
        self._pending_risky_close: PendingRiskyClose | None = None
        self._pending_disambiguation: PendingTerminalDisambiguation | None = None

    def try_resolve_pending_risky_close(self, text: str) -> str | None:
        """
        If awaiting yes/no after a MEDIUM/HIGH workload prompt, resolve it.

        Returns a user-visible string to short-circuit the intent pipeline, or
        ``None`` when there is nothing pending (caller continues normally).
        """
        if self._pending_risky_close is None:
            return None
        t = text.strip().lower()
        if t not in ("yes", "no", "y", "n"):
            return 'Please answer "yes" or "no".'
        if t in ("no", "n"):
            self._pending_risky_close = None
            return "Cancelled. The terminal was left running."
        pending = self._pending_risky_close
        self._pending_risky_close = None
        err = terminate_pid_scoped(pending.pid)
        if err is not None:
            return err
        return "Closed as requested."

    def try_resolve_pending_terminal_disambiguation(self, text: str) -> str | None:
        """
        Resolve follow-up replies (number, listed PID, name) after a multi-terminal list.

        Returns a user-visible string to short-circuit the intent pipeline, or ``None``
        when there is no pending disambiguation or the input should be parsed normally.
        """
        if self._pending_disambiguation is None:
            return None
        now = time.monotonic()
        if now > self._pending_disambiguation.expires_at:
            self._pending_disambiguation = None
            return "That selection expired. Please try again."

        result = resolve_terminal_disambiguation_followup(text, self._pending_disambiguation)

        if result.kind == DisambiguationResolveKind.FALLTHROUGH:
            return None

        if result.kind == DisambiguationResolveKind.CANCELLED:
            self._pending_disambiguation = None
            return result.message or "Cancelled."

        if result.kind == DisambiguationResolveKind.ERROR_KEEP:
            return result.message

        if result.kind == DisambiguationResolveKind.NARROW:
            self._pending_disambiguation = result.new_pending
            return result.message

        if result.kind == DisambiguationResolveKind.CLOSE_OPTION:
            assert result.option is not None
            return self._execute_disambiguated_close(result.option)

        return None

    def _execute_disambiguated_close(self, option: TerminalDisambiguationOption) -> str:
        """Scoped PID close after explicit pick from the pending option list only."""
        self._pending_disambiguation = None
        gate = self._risk_gate_before_terminate(option.pid)
        if gate is not None:
            return gate
        err = terminate_pid_scoped(option.pid)
        if err is not None:
            return err
        return append_workload_hint_if_any(
            option.pid,
            f"Closed {option.display_name} (PID {option.pid}).",
        )

    def _risk_gate_before_terminate(self, pid: int) -> str | None:
        """
        MEDIUM/HIGH workloads → store pending confirmation and return prompt.

        LOW → ``None`` (caller may terminate immediately).
        """
        level, lines = analyze_terminal_workload(pid)
        if not workload_requires_close_confirmation(level):
            return None
        self._pending_risky_close = PendingRiskyClose(
            pid=pid,
            risk_level=level,
            workload_lines=list(lines),
        )
        return format_close_confirmation_prompt(lines)

    def execute_command(self, command: str):
        return f"Executing {command} on Windows"

    def get_status(self):
        return "Windows System Active"

    def open_app(self, app_name: str):
        canonical = normalize_terminal_open_target(app_name)
        if canonical is not None:
            self._pending_risky_close = None
            self._pending_disambiguation = None
            if not self._terminal_launch_debounce_allow(canonical):
                return (
                    f"Ignored duplicate terminal launch "
                    f"(wait ~{TERMINAL_LAUNCH_COOLDOWN_SEC:.0f}s between tries)."
                )
            result = launch_terminal_app(canonical)
            self._register_terminal_launch(canonical, result)
            return result.message

        try:
            os.startfile(app_name)
            return f"{app_name} opened."
        except OSError as e:
            return f"Error opening {app_name}: {e}"

    def _register_terminal_launch(self, canonical: str, result: TerminalLaunchResult) -> None:
        if result.pid is None:
            return
        title = result.window_title
        if title is None:
            title = try_window_title_for_pid(result.pid)
        self._session_registry.register_app(
            category="terminal",
            pid=result.pid,
            process_name=result.process_name or "unknown",
            launch_method=result.launch_method or canonical,
            launch_canonical=canonical,
            window_title=title,
            source="assistant_launch",
        )

    def _terminal_launch_debounce_allow(self, canonical: str) -> bool:
        now = time.monotonic()
        if (
            self._last_terminal_launch_key == canonical
            and (now - self._last_terminal_launch_mono) < TERMINAL_LAUNCH_COOLDOWN_SEC
        ):
            return False
        self._last_terminal_launch_mono = now
        self._last_terminal_launch_key = canonical
        return True

    def close_file_explorer_windows(self):
        return close_file_explorer_windows_impl()

    def close_app(self, app_name: str):
        term_key = terminal_close_request_key(app_name)
        if term_key is not None:
            return self._close_terminal_smart(term_key)

        target_app = app_name.lower()
        if not target_app.endswith(".exe"):
            target_app += ".exe"

        if target_app in CRITICAL_PROCESSES:
            if target_app == "explorer.exe":
                return "Use window-level close for File Explorer."
            return f"Blocked: {target_app} is a critical system process."

        exe_norm = normalize_exe_name(target_app)
        if is_global_mass_kill_blocked(exe_norm):
            return (
                "Can't close every running instance of that program by name. "
                "Focus the window you mean, or close a terminal the assistant opened."
            )

        found = False

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == target_app:
                    proc.terminate()
                    found = True

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if found:
            return f"{target_app} closed successfully."
        else:
            return f"{target_app} is not running."

    def _close_terminal_smart(self, request_key: str) -> str:
        """
        Trust hierarchy (never global executable kill):

        1. Assistant-launched PID (SessionRegistry, ``source=assistant_launch``).
        2. Focused interactive terminal (scoped close + workload hints).
        3. Multiple observable terminals → list + ask user to focus target.
        4. Single orphan terminal → ask for focus.
        5. Else safe refusal.
        """
        self._session_registry.cleanup_dead_processes("terminal")
        entry = self._session_registry.pop_close_candidate(request_key)
        if entry is not None:
            if not is_assistant_owned_session(entry.source):
                return (
                    "I can't confidently close that session by PID alone. "
                    'Focus the terminal window and say "close terminal".'
                )
            gate_msg = self._risk_gate_before_terminate(entry.pid)
            if gate_msg is not None:
                return gate_msg
            err = terminate_pid_scoped(entry.pid)
            if err is not None:
                return f"{err} Try focus-based close instead."
            return append_workload_hint_if_any(
                entry.pid,
                "Closed the terminal session I started for you.",
            )

        focused = close_focused_terminal_session(
            request_key,
            risk_gate=self._risk_gate_before_terminate,
        )
        if focused.startswith("Closed "):
            return focused

        if focused.startswith("Terminal close requires"):
            return focused

        low = focused.lower()
        if "several shell sessions" in low:
            return focused
        if "multiple" in low and "sessions" in low and "click" in low:
            return focused

        observed = list_observable_terminal_sessions()
        if len(observed) >= 2:
            infos = analyze_sessions_for_disambiguation(
                observed,
                assistant_entries=self._session_registry.list_alive_terminal_entries(),
                foreground_pid=try_get_foreground_pid(),
            )
            opts = options_from_session_infos(infos)
            self._pending_disambiguation = PendingTerminalDisambiguation(
                options=opts,
                request_key=request_key,
                action="close_terminal",
            )
            return format_disambiguation_prompt(opts)
        if len(observed) == 1:
            return format_single_terminal_need_focus()

        return "I couldn't find a safe terminal session to close."

    def get_time(self):
        return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}."

    def get_cpu_usage(self):
        usage = psutil.cpu_percent(interval=1)
        return f"Current CPU usage: {usage}%"

    def get_memory_usage(self):
        usage = psutil.virtual_memory().percent
        return f"Current Memory usage: {usage}%"
