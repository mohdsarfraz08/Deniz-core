"""
Workload-aware descriptions for terminal disambiguation (advisory risk only).

Risk labels describe approximate interruption cost — not security guarantees.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
import psutil

from adapters.terminal_constants import CONHOST, WINDOWS_TERMINAL_HOSTS
from core.security.terminal_trust import ObservableTerminal
from core.session.app_registry import AppSessionEntry

logger = logging.getLogger(__name__)


class TerminalRiskLevel(IntEnum):
    """Advisory interruption risk for closing a session (not security severity)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


def risk_label_public(r: TerminalRiskLevel) -> str:
    """User-visible suffix, e.g. LOW RISK — never implies guaranteed safety."""
    return f"{r.name} RISK"


@dataclass
class TerminalSessionInfo:
    pid: int
    process_name: str
    display_name: str
    workload_hint: str | None
    risk_level: TerminalRiskLevel
    source: str | None
    is_assistant_owned: bool
    is_focused: bool = False


@dataclass
class _WorkloadSignals:
    ssh: bool = False
    docker: bool = False
    npm_dev: bool = False
    api_server: bool = False
    python_heavy: bool = False
    python_light: bool = False
    jupyter: bool = False
    streamlit: bool = False
    git_op: bool = False
    pytest: bool = False
    kubectl: bool = False
    hints: list[str] = field(default_factory=list)


def _safe_cmdline(proc: psutil.Process, max_parts: int = 10) -> str:
    try:
        parts = proc.cmdline()
        if not parts:
            return proc.name()
        return " ".join(parts[:max_parts])
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        try:
            return proc.name()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return "?"


def _scan_process_tree(host_pid: int) -> tuple[_WorkloadSignals, TerminalRiskLevel]:
    signals = _WorkloadSignals()
    max_risk = TerminalRiskLevel.LOW

    try:
        root = psutil.Process(host_pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return signals, max_risk

    try:
        for child in root.children(recursive=True):
            try:
                name = child.name().lower()
                cmd_l = _safe_cmdline(child).lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

            # --- HIGH-tier signals ---
            if name in ("ssh.exe", "plink.exe") or "ssh " in cmd_l or cmd_l.startswith("ssh"):
                signals.ssh = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "SSH")
            if "docker-compose" in cmd_l or "docker compose" in cmd_l:
                signals.docker = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "docker-compose")
            elif "docker" in name or "docker" in cmd_l:
                signals.docker = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "docker")
            if "kubectl" in name or "kubectl" in cmd_l:
                signals.kubectl = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "kubectl")
            if name == "node.exe" or name.startswith("node"):
                signals.npm_dev = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "node")
            if (
                any(pkg in cmd_l for pkg in ("npm", "yarn", "pnpm"))
                and any(x in cmd_l for x in ("dev", "start", "vite", "webpack", "serve", "watch"))
            ):
                signals.npm_dev = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "package manager")
            if any(x in cmd_l for x in ("uvicorn", "gunicorn", "flask run", "fastapi")):
                signals.api_server = True
                max_risk = TerminalRiskLevel.HIGH
                _add_hint(signals, "API server")
            if any(x in cmd_l for x in ("vite", "webpack", "npm start", "npm run")) and signals.npm_dev:
                pass
            # --- MEDIUM / conditional ---
            if "pytest" in cmd_l or name == "pytest.exe":
                signals.pytest = True
                if max_risk < TerminalRiskLevel.MEDIUM:
                    max_risk = TerminalRiskLevel.MEDIUM
                _add_hint(signals, "pytest")
            if name == "git.exe" or cmd_l.strip().startswith("git ") or " git " in cmd_l:
                signals.git_op = True
                if max_risk < TerminalRiskLevel.MEDIUM:
                    max_risk = TerminalRiskLevel.MEDIUM
                _add_hint(signals, "git")
            if "jupyter" in cmd_l or "jupyter" in name:
                signals.jupyter = True
                if max_risk < TerminalRiskLevel.MEDIUM:
                    max_risk = TerminalRiskLevel.MEDIUM
                _add_hint(signals, "jupyter")
            if "streamlit" in cmd_l:
                signals.streamlit = True
                if max_risk < TerminalRiskLevel.MEDIUM:
                    max_risk = TerminalRiskLevel.MEDIUM
                _add_hint(signals, "streamlit")
            if name in ("python.exe", "pythonw.exe", "python3.exe"):
                if any(x in cmd_l for x in ("uvicorn", "gunicorn", "flask run", "fastapi")):
                    signals.api_server = True
                    signals.python_heavy = True
                    max_risk = TerminalRiskLevel.HIGH
                elif any(x in cmd_l for x in ("pytest", "tox")):
                    signals.pytest = True
                    if max_risk < TerminalRiskLevel.MEDIUM:
                        max_risk = TerminalRiskLevel.MEDIUM
                else:
                    signals.python_light = True
                    if max_risk < TerminalRiskLevel.MEDIUM:
                        max_risk = TerminalRiskLevel.MEDIUM
                _add_hint(signals, "python")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return signals, max_risk


def _add_hint(signals: _WorkloadSignals, text: str) -> None:
    if text not in signals.hints:
        signals.hints.append(text)
        if len(signals.hints) > 6:
            signals.hints.pop(0)


def _pick_workload_label(signals: _WorkloadSignals, max_risk: TerminalRiskLevel) -> tuple[str, TerminalRiskLevel]:
    """Choose a single human-facing label; risk may be bumped for primary workload type."""
    risk = max_risk
    if signals.ssh:
        return "SSH Session", TerminalRiskLevel.HIGH
    if signals.docker:
        return "Docker Container", TerminalRiskLevel.HIGH
    if signals.kubectl:
        return "Kubernetes client", TerminalRiskLevel.HIGH
    if signals.npm_dev or (signals.api_server and any("node" in h for h in signals.hints)):
        return "npm dev server", TerminalRiskLevel.HIGH
    if signals.api_server:
        return "API Server", TerminalRiskLevel.HIGH
    if signals.streamlit:
        return "Python app (Streamlit)", TerminalRiskLevel.MEDIUM
    if signals.jupyter:
        return "Python (Jupyter)", TerminalRiskLevel.MEDIUM
    if signals.pytest:
        return "Tests (pytest)", TerminalRiskLevel.MEDIUM
    if signals.git_op:
        return "Git Operation", TerminalRiskLevel.MEDIUM
    if signals.python_heavy or signals.python_light:
        return "Python Script", max(risk, TerminalRiskLevel.MEDIUM)

    return "Active workload", risk


def _idle_shell_label(exe_lower: str) -> str:
    if exe_lower == "powershell.exe":
        return "Idle PowerShell"
    if exe_lower == "pwsh.exe":
        return "Idle PowerShell (pwsh)"
    if exe_lower == "cmd.exe":
        return "Idle Command Prompt"
    if exe_lower in WINDOWS_TERMINAL_HOSTS:
        return "Windows Terminal session"
    if exe_lower == CONHOST:
        return "Console session"
    return "Terminal session"


def _conhost_friendly_idle_label(root: psutil.Process) -> str:
    try:
        for ch in root.children(recursive=False):
            try:
                n = ch.name().lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if n == "powershell.exe":
                return "Idle PowerShell"
            if n == "pwsh.exe":
                return "Idle PowerShell (pwsh)"
            if n == "cmd.exe":
                return "Idle Command Prompt"
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return "Console session"


def _compose_display_name(
    *,
    host_exe: str,
    root: psutil.Process | None,
    signals: _WorkloadSignals,
    tree_risk: TerminalRiskLevel,
    assistant: bool,
) -> tuple[str, TerminalRiskLevel, str | None]:
    """
    Returns display_name, effective_risk, workload_hint.
    Suppresses raw exe names like conhost.exe in favor of idle/workload phrases.
    """
    exe_l = host_exe.lower()
    workload_hint: str | None = ", ".join(signals.hints[:3]) if signals.hints else None

    has_workload = any(
        (
            signals.ssh,
            signals.docker,
            signals.npm_dev,
            signals.api_server,
            signals.python_heavy,
            signals.python_light,
            signals.jupyter,
            signals.streamlit,
            signals.git_op,
            signals.pytest,
            signals.kubectl,
        )
    )

    if not has_workload:
        idle = (
            _conhost_friendly_idle_label(root)
            if exe_l == CONHOST and root is not None
            else _idle_shell_label(exe_l)
        )
        risk = TerminalRiskLevel.LOW
        if assistant:
            return "Assistant Terminal", risk, workload_hint
        return idle, risk, workload_hint

    label, lrisk = _pick_workload_label(signals, tree_risk)
    effective = max(lrisk, tree_risk)
    if assistant:
        return f"Assistant · {label}", effective, workload_hint
    return label, effective, workload_hint


def resolve_focused_listed_pid(foreground_pid: int | None, listed_pids: list[int]) -> int | None:
    """Map foreground PID to one of the listed session roots (direct or ancestor)."""
    if foreground_pid is None or not listed_pids:
        return None
    cand = set(listed_pids)
    if foreground_pid in cand:
        return foreground_pid
    try:
        p = psutil.Process(foreground_pid)
        seen: set[int] = set()
        while p.pid not in seen:
            seen.add(p.pid)
            if p.pid in cand:
                return p.pid
            try:
                parent = p.parent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
            if parent is None:
                break
            p = parent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return None


def analyze_terminal_session(
    obs: ObservableTerminal,
    *,
    assistant_entry: AppSessionEntry | None,
    is_focused: bool,
) -> TerminalSessionInfo:
    """Build advisory session info for one enumerated PID (never kills)."""
    pid = obs.pid
    exe = obs.exe_name
    source = assistant_entry.source if assistant_entry else None
    assistant = assistant_entry is not None

    root: psutil.Process | None
    try:
        root = psutil.Process(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        root = None

    signals, tree_risk = _scan_process_tree(pid)
    display_name, risk_level, workload_hint = _compose_display_name(
        host_exe=exe,
        root=root,
        signals=signals,
        tree_risk=tree_risk,
        assistant=assistant,
    )

    return TerminalSessionInfo(
        pid=pid,
        process_name=exe,
        display_name=display_name,
        workload_hint=workload_hint,
        risk_level=risk_level,
        source=source,
        is_assistant_owned=assistant,
        is_focused=is_focused,
    )


def analyze_sessions_for_disambiguation(
    observed: list[ObservableTerminal],
    *,
    assistant_entries: list[AppSessionEntry],
    foreground_pid: int | None,
) -> list[TerminalSessionInfo]:
    """
    Enrich observable terminals with workload labels, advisory risk, and sort order:

    1. Assistant-owned
    2. Focused (foreground or ancestor match)
    3. LOW → MEDIUM → HIGH risk
    """
    by_pid: dict[int, AppSessionEntry] = {}
    for e in assistant_entries:
        try:
            if psutil.pid_exists(e.pid):
                by_pid[e.pid] = e
        except Exception:
            continue

    listed_pids = [o.pid for o in observed]
    focused_target = resolve_focused_listed_pid(foreground_pid, listed_pids)

    sessions: list[TerminalSessionInfo] = []
    for obs in observed:
        entry = by_pid.get(obs.pid)
        is_focused = focused_target is not None and obs.pid == focused_target
        sessions.append(
            analyze_terminal_session(obs, assistant_entry=entry, is_focused=is_focused)
        )

    def sort_key(s: TerminalSessionInfo) -> tuple[int, int, int, int]:
        return (
            0 if s.is_assistant_owned else 1,
            0 if s.is_focused else 1,
            s.risk_level.value,
            s.pid,
        )

    sessions.sort(key=sort_key)
    return sessions
