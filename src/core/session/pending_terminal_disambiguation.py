"""
Ephemeral pending state when multiple terminal candidates require user choice.

Selections are ONLY validated against the stored option list — never machine-wide
PID or process-name scans for termination.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum

from core.security.terminal_session_analysis import (
    TerminalRiskLevel,
    TerminalSessionInfo,
    risk_label_public,
)
from core.security.terminal_trust import ObservableTerminal

TERMINAL_DISAMBIGUATION_TTL_SEC = 45.0


class DisambiguationResolveKind(Enum):
    """Outcome of interpreting follow-up text against a pending disambiguation."""

    FALLTHROUGH = "fallthrough"
    CANCELLED = "cancelled"
    ERROR_KEEP = "error_keep"
    NARROW = "narrow"
    CLOSE_OPTION = "close_option"


@dataclass
class TerminalDisambiguationOption:
    """One numbered choice; PID must appear in the safe candidate snapshot."""

    index: int
    pid: int
    display_name: str
    process_name: str
    risk_level: TerminalRiskLevel = TerminalRiskLevel.LOW


@dataclass
class PendingTerminalDisambiguation:
    """
    Short-lived follow-up after listing terminals.

    ``expires_at`` uses ``time.monotonic()`` for stable comparisons.
    Maps to the conceptual ``PendingAction`` model (type + payload + timestamps).
    """

    type: str = field(default="terminal_disambiguation")
    action: str = field(default="close_terminal")
    request_key: str = "terminal"
    options: list[TerminalDisambiguationOption] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    expires_at: float = field(
        default_factory=lambda: time.monotonic() + TERMINAL_DISAMBIGUATION_TTL_SEC
    )

    def as_payload_dict(self) -> dict:
        """Serializable view of option metadata (for logging/tests only)."""
        return {
            "action": self.action,
            "options": [
                {
                    "index": o.index,
                    "pid": o.pid,
                    "display_name": o.display_name,
                    "process_name": o.process_name,
                    "risk_level": o.risk_level.name,
                }
                for o in self.options
            ],
        }


@dataclass
class TerminalDisambiguationResolveResult:
    kind: DisambiguationResolveKind
    message: str | None = None
    option: TerminalDisambiguationOption | None = None
    new_pending: PendingTerminalDisambiguation | None = None


def options_from_observable(sessions: list[ObservableTerminal]) -> list[TerminalDisambiguationOption]:
    """Legacy path: minimal labels (prefer :func:`options_from_session_infos`)."""
    out: list[TerminalDisambiguationOption] = []
    for i, s in enumerate(sessions, start=1):
        out.append(
            TerminalDisambiguationOption(
                index=i,
                pid=s.pid,
                display_name=s.display_label,
                process_name=s.exe_name,
                risk_level=TerminalRiskLevel.LOW,
            )
        )
    return out


def options_from_session_infos(infos: list[TerminalSessionInfo]) -> list[TerminalDisambiguationOption]:
    out: list[TerminalDisambiguationOption] = []
    for i, s in enumerate(infos, start=1):
        out.append(
            TerminalDisambiguationOption(
                index=i,
                pid=s.pid,
                display_name=s.display_name,
                process_name=s.process_name,
                risk_level=s.risk_level,
            )
        )
    return out


def format_disambiguation_prompt(options: list[TerminalDisambiguationOption]) -> str:
    lines = ["I found multiple terminal sessions:"]
    for o in options:
        lines.append(
            f"  {o.index}. {o.display_name} — PID {o.pid} — {risk_label_public(o.risk_level)}"
        )
    lines.extend(
        [
            "",
            "Reply with:",
            "  • a number (e.g. 2 or \"close 2\")",
            "  • a PID from this list",
            "  • a name or workload phrase (e.g. powershell, SSH Session)",
            "",
            "Risk labels are advisory (interruption cost), not guarantees.",
            "",
            f"This choice expires in about {int(TERMINAL_DISAMBIGUATION_TTL_SEC)} seconds.",
        ]
    )
    return "\n".join(lines)


def format_narrow_prompt(options: list[TerminalDisambiguationOption], theme: str) -> str:
    lines = [f"Which {theme} session should I close?"]
    for o in options:
        lines.append(
            f"  {o.index}. {o.display_name} — PID {o.pid} — {risk_label_public(o.risk_level)}"
        )
    lines.extend(["", "Reply with a number or PID from this list."])
    return "\n".join(lines)


def _reindex(options: list[TerminalDisambiguationOption]) -> list[TerminalDisambiguationOption]:
    return [
        TerminalDisambiguationOption(
            index=i,
            pid=o.pid,
            display_name=o.display_name,
            process_name=o.process_name,
            risk_level=o.risk_level,
        )
        for i, o in enumerate(options, start=1)
    ]


def _norm_name_query(text: str) -> str:
    t = text.strip().lower()
    for prefix in (
        "close terminal ",
        "close ",
        "terminal ",
    ):
        if t.startswith(prefix):
            t = t[len(prefix) :].strip()
    t = t.removesuffix(".exe").strip()
    return t


def _find_by_pid(pid: int, options: list[TerminalDisambiguationOption]) -> TerminalDisambiguationOption | None:
    for o in options:
        if o.pid == pid:
            return o
    return None


def _find_by_index(idx: int, options: list[TerminalDisambiguationOption]) -> TerminalDisambiguationOption | None:
    for o in options:
        if o.index == idx:
            return o
    return None


def _pick_index_or_pid(n: int, opts: list[TerminalDisambiguationOption]) -> TerminalDisambiguationOption | None:
    if 1 <= n <= len(opts):
        by_idx = _find_by_index(n, opts)
        if by_idx:
            return by_idx
    return _find_by_pid(n, opts)


def resolve_terminal_disambiguation_followup(
    text: str,
    pending: PendingTerminalDisambiguation,
) -> TerminalDisambiguationResolveResult:
    """
    Interpret ``text`` as a selection against ``pending.options`` only.

    Caller must ensure ``pending`` has not expired (``expires_at`` vs ``time.monotonic()``).
    """
    raw = text.strip()
    if not raw:
        return TerminalDisambiguationResolveResult(DisambiguationResolveKind.FALLTHROUGH)

    low = raw.lower()
    if low in ("cancel", "nevermind", "never mind", "stop", "abort"):
        return TerminalDisambiguationResolveResult(DisambiguationResolveKind.CANCELLED, message="Cancelled.")

    opts = pending.options

    # Explicit PID phrase — only if present in options
    m = re.search(r"\bpid\s*(\d+)\b", raw, re.I)
    if m:
        pid = int(m.group(1))
        hit = _find_by_pid(pid, opts)
        if hit:
            return TerminalDisambiguationResolveResult(
                DisambiguationResolveKind.CLOSE_OPTION,
                option=hit,
            )
        return TerminalDisambiguationResolveResult(
            DisambiguationResolveKind.ERROR_KEEP,
            message=f"PID {pid} isn't in the current list. Pick a PID shown above.",
        )

    # close <n>, terminal <n>, close number <n>
    m = re.match(r"^(?:close|terminal)\s+(?:number\s+)?(\d+)\s*$", raw, re.I)
    if m:
        n = int(m.group(1))
        hit = _pick_index_or_pid(n, opts)
        if hit:
            return TerminalDisambiguationResolveResult(DisambiguationResolveKind.CLOSE_OPTION, option=hit)
        return TerminalDisambiguationResolveResult(
            DisambiguationResolveKind.ERROR_KEEP,
            message=f'"{n}" doesn\'t match a listed number or PID.',
        )

    # Bare digits: index first when in range, else PID match in list
    if re.fullmatch(r"\d+", raw.strip()):
        n = int(raw.strip())
        hit = _pick_index_or_pid(n, opts)
        if hit:
            return TerminalDisambiguationResolveResult(DisambiguationResolveKind.CLOSE_OPTION, option=hit)
        return TerminalDisambiguationResolveResult(
            DisambiguationResolveKind.ERROR_KEEP,
            message=f'"{n}" isn\'t a listed index or PID.',
        )

    # Name / fragment
    q = _norm_name_query(raw)
    if q:
        matches = [
            o
            for o in opts
            if q in o.process_name.lower()
            or q in o.display_name.lower()
            or q.replace(" ", "") in o.display_name.lower().replace(" ", "")
        ]
        if len(matches) == 1:
            return TerminalDisambiguationResolveResult(
                DisambiguationResolveKind.CLOSE_OPTION,
                option=matches[0],
            )
        if len(matches) > 1:
            narrow = _reindex(matches)
            theme = "matching"
            if all("powershell" in o.process_name.lower() for o in matches):
                theme = "PowerShell"
            elif len({o.process_name.lower() for o in matches}) == 1:
                pn = matches[0].process_name.lower()
                if pn in ("powershell.exe", "pwsh.exe"):
                    theme = "PowerShell"
                elif pn == "cmd.exe":
                    theme = "Command Prompt"
                else:
                    theme = matches[0].display_name.split()[0]
            new_pending = PendingTerminalDisambiguation(
                type=pending.type,
                action=pending.action,
                request_key=pending.request_key,
                options=narrow,
                created_at=pending.created_at,
                expires_at=min(
                    pending.expires_at,
                    time.monotonic() + TERMINAL_DISAMBIGUATION_TTL_SEC,
                ),
            )
            return TerminalDisambiguationResolveResult(
                DisambiguationResolveKind.NARROW,
                message=format_narrow_prompt(narrow, theme),
                new_pending=new_pending,
            )
        return TerminalDisambiguationResolveResult(DisambiguationResolveKind.FALLTHROUGH)

    return TerminalDisambiguationResolveResult(DisambiguationResolveKind.FALLTHROUGH)
