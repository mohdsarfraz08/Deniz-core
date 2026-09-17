"""
core/action_results.py — Structured result types for Phase 8 (Execution Hardening).

ActionResult
    The canonical return contract for all SystemExecutor methods.
    Provides machine-readable success/failure, a human-readable message,
    optional structured data, and a recoverability flag the future AI Planner
    (Phase 12) will use to decide whether to retry or escalate.

AuditRecord
    Immutable telemetry snapshot written to logs/audit.log after every intent
    execution.  Sensitive fields (file paths, app targets) are sanitised before
    persistence to prevent PII reaching future LLM planner context.

AI Ethics / Data Privacy note
    The sanitise_for_audit() function redacts home-directory prefixes and
    Windows/Linux username path segments so that personal directory names are
    never stored in structured logs.  This is the single chokepoint — all
    audit writes must go through write_audit_record() in audit_log.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, NotRequired, TypedDict, overload


# ---------------------------------------------------------------------------
# Primary Phase 8 contract
# ---------------------------------------------------------------------------

@dataclass
class ActionResult:
    """
    Structured result returned by every SystemExecutor method.

    Attributes
    ----------
    success:
        True when the underlying OS action completed without error.
    message:
        Human-readable response forwarded to the user via IntentEngine.
        Must never be None; use an empty string if there is nothing to say.
    data:
        Optional machine-readable payload (e.g. process PID, window count).
        Consumed by the AI Planner layer — must not contain raw PII.
    recoverable:
        True when the failure is transient and a retry may succeed.
        False for permanent failures (process not found, permission denied).
        The Phase 12 AI Planner uses this flag to decide retry vs escalation.
    """

    success: bool
    message: str
    data: dict | None = None
    recoverable: bool = True


# ---------------------------------------------------------------------------
# Audit telemetry
# ---------------------------------------------------------------------------

# Patterns whose matched groups are replaced with <REDACTED> in audit output.
_PII_PATTERNS: list[re.Pattern[str]] = [
    # Windows: C:\Users\<username>\...
    re.compile(r"(C:\\[Uu]sers\\)[^\\]+", re.IGNORECASE),
    # Linux/macOS: /home/<username>/...  or  /Users/<username>/...
    re.compile(r"(/(?:home|Users)/)[^/]+", re.IGNORECASE),
]


@overload
def sanitise_for_audit(value: str) -> str: ...
@overload
def sanitise_for_audit(value: None) -> None: ...
def sanitise_for_audit(value: str | None) -> str | None:
    """
    Redact username-bearing path segments before writing to audit logs.

    This is the single authoritative PII chokepoint for Phase 8 telemetry.
    All audit writes must pass user-supplied strings through this function.

    Examples
    --------
    >>> sanitise_for_audit(r"C:\\Users\\alice\\Documents\\report.docx")
    'C:\\\\Users\\\\<REDACTED>\\\\Documents\\\\report.docx'
    >>> sanitise_for_audit("/home/bob/projects/deniz")
    '/home/<REDACTED>/projects/deniz'
    >>> sanitise_for_audit("chrome")
    'chrome'
    """
    if value is None:
        return None
    for pattern in _PII_PATTERNS:
        value = pattern.sub(r"\g<1><REDACTED>", value)
    return value


@dataclass
class AuditRecord:
    """
    Immutable telemetry snapshot for a single intent execution.

    Written to logs/audit.log by audit_log.write_audit_record().
    All string fields that may contain user-supplied paths are sanitised
    via sanitise_for_audit() before the record is constructed.

    Attributes
    ----------
    intent:
        The resolved intent name (e.g. ``open_app``).
    target:
        The sanitised app name or file path, if applicable.
    success:
        Mirrors ActionResult.success.
    message:
        The sanitised user-facing message from ActionResult.message.
    recoverable:
        Mirrors ActionResult.recoverable.
    execution_time_s:
        Wall-clock seconds the adapter call took.
    timestamp:
        ISO-8601 UTC timestamp string.
    """

    intent: str
    target: str | None
    success: bool
    message: str
    recoverable: bool
    execution_time_s: float
    timestamp: str


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# ---------------------------------------------------------------------------

class CloseFileExplorerWindowsResult(TypedDict):
    """
    Deprecated — retained only so existing import sites resolve without change.

    All new code should use ActionResult.  This TypedDict will be removed
    when close_file_explorer_windows() is fully migrated in Phase 8.
    """

    status: Literal["success", "error"]
    action: Literal["close_file_explorer_windows"]
    count: int
    detail: NotRequired[str]
