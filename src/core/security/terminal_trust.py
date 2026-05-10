"""
Confidence hierarchy for closing terminals without global executable kills.

Level 1 — Assistant-launched session (PID tracked at launch).
Level 2 — User-focused interactive terminal (foreground window + verified shell/host).
Level 3 — Multiple candidates (numbered list + ephemeral follow-up selection within that snapshot).

Never enumerates processes for termination by image name across the machine.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import NamedTuple

import psutil

from adapters.terminal_constants import OBSERVABLE_TERMINAL_EXES, TERMINAL_DISPLAY_LABELS

logger = logging.getLogger(__name__)


class RiskLevel(IntEnum):
    """Workload risk before closing a terminal session (scoped PID only)."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TrustLevel(IntEnum):
    ASSISTANT_LAUNCHED = 1
    FOCUSED_INTERACTIVE = 2
    USER_DISAMBIGUATION = 3


class ObservableTerminal(NamedTuple):
    pid: int
    exe_name: str
    display_label: str


# Reasonable upper bound for interactive listing (full snapshot is sorted for stable numbering).
OBSERVABLE_TERMINAL_LIST_MAX = 512


def is_assistant_owned_session(source: str) -> bool:
    """Highest confidence: we spawned this process and recorded its PID."""
    return source == "assistant_launch"


def list_observable_terminal_sessions(max_items: int = OBSERVABLE_TERMINAL_LIST_MAX) -> list[ObservableTerminal]:
    """
    Read-only snapshot for UX when disambiguation is needed.

    Collects all matching processes, sorts for stable numbering, then truncates to
    ``max_items``. Does not terminate anything (observation / counting only).
    """
    out: list[ObservableTerminal] = []
    seen: set[int] = set()
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = proc.info.get("pid")
                raw_name = proc.info.get("name") or ""
                name = raw_name.lower()
                if pid is None or int(pid) in seen:
                    continue
                if name not in OBSERVABLE_TERMINAL_EXES:
                    continue
                seen.add(int(pid))
                label = TERMINAL_DISPLAY_LABELS.get(name, raw_name)
                out.append(ObservableTerminal(int(pid), name, label))
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
                continue
    except Exception as e:
        logger.debug("list_observable_terminal_sessions: %s", e)
    out.sort(key=lambda s: (s.display_label.lower(), s.pid))
    return out[:max_items]


def format_multi_terminal_disambiguation(sessions: list[ObservableTerminal]) -> str:
    """UX copy aligned with conversational follow-up (shared with pending-disambiguation flow)."""
    from core.security.terminal_session_analysis import analyze_sessions_for_disambiguation
    from core.session.pending_terminal_disambiguation import (
        format_disambiguation_prompt,
        options_from_session_infos,
    )

    infos = analyze_sessions_for_disambiguation(
        sessions,
        assistant_entries=[],
        foreground_pid=None,
    )
    return format_disambiguation_prompt(options_from_session_infos(infos))


def format_single_terminal_need_focus() -> str:
    return (
        "A terminal is running, but I can't safely guess which window you mean without focus. "
        'Click the terminal you want to close, then say "close terminal" again.'
    )


RISKY_CHILD_NAMES = frozenset(
    {
        "node.exe",
        "python.exe",
        "pythonw.exe",
        "docker.exe",
        "kubectl.exe",
    }
)


def collect_risky_child_hints(host_pid: int, max_names: int = 5) -> list[str]:
    """Notable child workloads under ``host_pid`` (recursive) — hints only, not blocking."""
    hints: list[str] = []
    try:
        root = psutil.Process(host_pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return hints
    try:
        for child in root.children(recursive=True):
            try:
                n = child.name().lower()
                if n in RISKY_CHILD_NAMES:
                    if n not in hints:
                        hints.append(n)
                elif any(
                    x in n for x in ("ssh", "plink", "npm", "uvicorn", "pytest", "dotnet")
                ):
                    if n not in hints:
                        hints.append(n)
                if len(hints) >= max_names:
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return hints


def append_workload_hint_if_any(host_pid: int, base_message: str) -> str:
    """Suffix informational workload hints after a successful scoped close."""
    hints = collect_risky_child_hints(host_pid)
    if not hints:
        return base_message
    shown = ", ".join(hints[:4])
    return f"{base_message} Heads-up: related workloads were active ({shown})."


def workload_requires_close_confirmation(level: RiskLevel) -> bool:
    """Idle / unknown-low workloads close immediately; scripts and servers need yes/no."""
    return level != RiskLevel.LOW


def _safe_cmdline(proc: psutil.Process, max_parts: int = 8) -> str:
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


def _classify_child_risk(proc: psutil.Process) -> tuple[RiskLevel, str | None]:
    """
    Map a child process to a risk tier and an optional human-readable workload line.

    Heuristic only — prefers slight inconvenience over destructive certainty.
    """
    try:
        name = proc.name().lower()
        cmd_l = _safe_cmdline(proc).lower()
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        return RiskLevel.LOW, None

    display = _safe_cmdline(proc)

    # --- HIGH: servers, containers, remote sessions ---
    if name == "node.exe" or name.startswith("node"):
        return RiskLevel.HIGH, f"node — {display}"
    if "docker" in name or "docker" in cmd_l or "docker-compose" in cmd_l:
        return RiskLevel.HIGH, f"docker — {display}"
    if name in ("ssh.exe", "plink.exe") or "ssh " in cmd_l:
        return RiskLevel.HIGH, f"ssh — {display}"
    if "kubectl" in name or "kubectl" in cmd_l:
        return RiskLevel.HIGH, f"kubectl — {display}"
    if any(x in cmd_l for x in ("uvicorn", "gunicorn", "vite", "webpack", "npm start")):
        return RiskLevel.HIGH, f"server/tooling — {display}"

    # --- MEDIUM: interpreted workloads ---
    if name in ("python.exe", "pythonw.exe", "python3.exe"):
        if any(x in cmd_l for x in ("uvicorn", "gunicorn", "flask run")):
            return RiskLevel.HIGH, f"python server — {display}"
        return RiskLevel.MEDIUM, f"python — {display}"
    if "pytest" in cmd_l or name == "pytest.exe":
        return RiskLevel.MEDIUM, f"pytest — {display}"
    if name in ("npm.cmd", "npx.exe") or name.startswith("npm"):
        return RiskLevel.HIGH, f"npm — {display}"

    return RiskLevel.LOW, None


def analyze_terminal_workload(host_pid: int, max_lines: int = 8) -> tuple[RiskLevel, list[str]]:
    """
    Inspect descendant processes for risky workloads.

    Returns the highest risk tier seen and bullet lines for the confirmation prompt.
    """
    max_level = RiskLevel.LOW
    lines: list[str] = []
    seen: set[str] = set()

    try:
        root = psutil.Process(host_pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return RiskLevel.LOW, []

    try:
        for child in root.children(recursive=True):
            try:
                lvl, line = _classify_child_risk(child)
                if line and line not in seen:
                    seen.add(line)
                    lines.append(line)
                    if lvl > max_level:
                        max_level = lvl
                elif lvl > max_level:
                    max_level = lvl
                if len(lines) >= max_lines:
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return max_level, lines


def format_close_confirmation_prompt(workload_lines: list[str]) -> str:
    """Shown before terminating when MEDIUM/HIGH risk — user must answer yes/no next turn."""
    body: list[str] = ["This terminal appears to be running:"]
    if workload_lines:
        for w in workload_lines:
            body.append(f"  - {w}")
    else:
        body.append("  - (active subprocess workloads detected)")
    body.extend(["", "Close anyway? (yes/no)"])
    return "\n".join(body)


def describe_close_confidence(trust: TrustLevel) -> str:
    """Debug / logging helper."""
    return {TrustLevel.ASSISTANT_LAUNCHED: "assistant_owned", TrustLevel.FOCUSED_INTERACTIVE: "focused", TrustLevel.USER_DISAMBIGUATION: "user_pick"}.get(
        trust, "unknown"
    )
