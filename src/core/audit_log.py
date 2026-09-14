"""
core/audit_log.py — Phase 8 execution audit writer.

write_audit_record() is the single entry-point for persisting AuditRecord
objects to logs/audit.log.  It enforces PII sanitisation via
sanitise_for_audit() before any field touches disk.

AI Ethics contract
------------------
* Intent names are logged as-is (they are code symbols, not user data).
* `target` and `message` fields are sanitised before write.
* Raw user input is never written here; only post-parse structured fields.
* The audit log is append-only; no record is modified after write.
* When the Phase 10 AI layer reads this log for context, it sees only
  sanitised, structured records — no home directories, usernames, or
  raw conversational text.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from core.action_results import ActionResult, AuditRecord, sanitise_for_audit
from core.parser import Intent

logger = logging.getLogger("AuditLog")

# Written relative to project root so logs/ stays in one place.
_DEFAULT_AUDIT_PATH = Path(__file__).resolve().parents[2] / "logs" / "audit.log"


def build_audit_record(
    intent: Intent,
    result: ActionResult,
    execution_time_s: float,
) -> AuditRecord:
    """
    Construct a sanitised AuditRecord from an executed intent + ActionResult.

    All user-supplied string fields (target, message) are passed through
    sanitise_for_audit() before the record is built.

    Parameters
    ----------
    intent:
        The parsed and session-enriched Intent that was executed.
    result:
        The ActionResult returned by the SystemExecutor boundary.
    execution_time_s:
        Wall-clock duration of the adapter call in seconds.

    Returns
    -------
    AuditRecord
        A fully sanitised, immutable telemetry snapshot ready to persist.
    """
    return AuditRecord(
        intent=intent.intent,
        target=sanitise_for_audit(intent.target),
        success=result.success,
        message=sanitise_for_audit(result.message) or "",
        recoverable=result.recoverable,
        execution_time_s=round(execution_time_s, 4),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def write_audit_record(
    record: AuditRecord,
    audit_path: Path | None = None,
) -> None:
    """
    Append a single AuditRecord to the audit log as a JSON line.

    Each line is a self-contained JSON object (JSONL format) so the log
    can be streamed, grep'd, and parsed incrementally by the Phase 10 AI layer.

    Parameters
    ----------
    record:
        The AuditRecord to persist.  Must have been created via
        build_audit_record() to guarantee PII sanitisation.
    audit_path:
        Override the default log path (used in tests).  Defaults to
        `logs/audit.log` relative to the project root.
    """
    path = audit_path or _DEFAULT_AUDIT_PATH

    entry = {
        "timestamp": record.timestamp,
        "intent": record.intent,
        "target": record.target,
        "success": record.success,
        "recoverable": record.recoverable,
        "execution_time_s": record.execution_time_s,
        "message": record.message,
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 — audit must never crash the assistant
        logger.warning("Audit write failed (non-fatal): %s", exc)
