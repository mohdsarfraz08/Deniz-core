"""
Phase 8 — ActionResult, AuditRecord, and PII sanitisation tests.

Covers:
  - ActionResult field defaults and invariants
  - sanitise_for_audit() PII redaction (Windows + Linux paths)
  - build_audit_record() sanitises target and message
  - write_audit_record() writes valid JSONL and is non-fatal on IO failure
  - format_close_file_explorer_message() with ActionResult input
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.action_results import (
    ActionResult,
    AuditRecord,
    CloseFileExplorerWindowsResult,
    sanitise_for_audit,
)
from core.audit_log import build_audit_record, write_audit_record
from core.intent_resolution import format_close_file_explorer_message
from core.parser import Intent


# ---------------------------------------------------------------------------
# ActionResult
# ---------------------------------------------------------------------------

class TestActionResult:

    def test_success_defaults(self) -> None:
        r = ActionResult(success=True, message="chrome opened.")
        assert r.success is True
        assert r.message == "chrome opened."
        assert r.data is None
        assert r.recoverable is True  # default

    def test_failure_non_recoverable(self) -> None:
        r = ActionResult(success=False, message="Blocked: critical process.", recoverable=False)
        assert r.success is False
        assert r.recoverable is False

    def test_data_payload(self) -> None:
        r = ActionResult(success=True, message="", data={"count": 3})
        assert r.data is not None
        assert r.data["count"] == 3

    def test_message_must_be_string(self) -> None:
        """message must never be None — enforce by asserting type."""
        r = ActionResult(success=True, message="")
        assert isinstance(r.message, str)


# ---------------------------------------------------------------------------
# sanitise_for_audit — PII redaction
# ---------------------------------------------------------------------------

class TestSanitiseForAudit:

    def test_windows_path_redacted(self) -> None:
        raw = r"C:\Users\alice\Documents\report.docx"
        result = sanitise_for_audit(raw)
        assert "alice" not in result
        assert "<REDACTED>" in result
        assert "Documents" in result  # non-username segment preserved

    def test_linux_home_path_redacted(self) -> None:
        raw = "/home/bob/projects/deniz/main.py"
        result = sanitise_for_audit(raw)
        assert "bob" not in result
        assert "<REDACTED>" in result
        assert "projects" in result

    def test_macos_users_path_redacted(self) -> None:
        raw = "/Users/carol/Desktop/notes.txt"
        result = sanitise_for_audit(raw)
        assert "carol" not in result
        assert "<REDACTED>" in result

    def test_plain_app_name_unchanged(self) -> None:
        assert sanitise_for_audit("chrome") == "chrome"

    def test_none_returns_none(self) -> None:
        assert sanitise_for_audit(None) is None

    def test_no_path_unchanged(self) -> None:
        assert sanitise_for_audit("notepad.exe") == "notepad.exe"

    def test_windows_case_insensitive(self) -> None:
        raw = r"c:\users\Dave\AppData\app.exe"
        result = sanitise_for_audit(raw)
        assert "Dave" not in result


# ---------------------------------------------------------------------------
# build_audit_record — construction + sanitisation
# ---------------------------------------------------------------------------

class TestBuildAuditRecord:

    def test_basic_fields(self) -> None:
        intent = Intent(intent="open_app", target="notepad")
        result = ActionResult(success=True, message="notepad opened.")
        rec = build_audit_record(intent, result, execution_time_s=0.05)

        assert rec.intent == "open_app"
        assert rec.target == "notepad"
        assert rec.success is True
        assert rec.message == "notepad opened."
        assert rec.recoverable is True
        assert abs(rec.execution_time_s - 0.05) < 0.001
        assert rec.timestamp  # non-empty ISO string

    def test_pii_target_sanitised(self) -> None:
        intent = Intent(intent="open_app", target=r"C:\Users\secret\app.exe")
        result = ActionResult(success=True, message="app.exe opened.")
        rec = build_audit_record(intent, result, execution_time_s=0.0)
        assert "secret" not in (rec.target or "")
        assert "<REDACTED>" in (rec.target or "")

    def test_pii_message_sanitised(self) -> None:
        intent = Intent(intent="open_app", target="app")
        result = ActionResult(
            success=False,
            message=r"Error opening C:\Users\alice\app.exe: not found",
        )
        rec = build_audit_record(intent, result, execution_time_s=0.0)
        assert "alice" not in rec.message
        assert "<REDACTED>" in rec.message

    def test_no_target_stays_none(self) -> None:
        intent = Intent(intent="get_cpu_usage")
        result = ActionResult(success=True, message="CPU 12%")
        rec = build_audit_record(intent, result, execution_time_s=1.001)
        assert rec.target is None


# ---------------------------------------------------------------------------
# write_audit_record — JSONL persistence
# ---------------------------------------------------------------------------

class TestWriteAuditRecord:

    def _make_record(self) -> AuditRecord:
        return AuditRecord(
            intent="open_app",
            target="notepad",
            success=True,
            message="notepad opened.",
            recoverable=True,
            execution_time_s=0.05,
            timestamp="2026-09-14T15:00:00+00:00",
        )

    def test_writes_jsonl_line(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log"
        rec = self._make_record()
        write_audit_record(rec, audit_path=log_file)

        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["intent"] == "open_app"
        assert entry["target"] == "notepad"
        assert entry["success"] is True

    def test_appends_multiple_records(self, tmp_path: Path) -> None:
        log_file = tmp_path / "audit.log"
        write_audit_record(self._make_record(), audit_path=log_file)
        write_audit_record(self._make_record(), audit_path=log_file)
        lines = log_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_non_fatal_on_unwritable_path(self, tmp_path: Path) -> None:
        """IO failure during mkdir or open must not propagate to the caller."""
        from unittest.mock import patch
        rec = self._make_record()
        log_file = tmp_path / "audit.log"
        with patch("pathlib.Path.mkdir", side_effect=OSError("Permission denied")):
            # Should not raise — write_audit_record must be non-fatal
            write_audit_record(rec, audit_path=log_file)
        # Log file should not exist since mkdir was blocked
        assert not log_file.exists()


# ---------------------------------------------------------------------------
# format_close_file_explorer_message with ActionResult
# ---------------------------------------------------------------------------

class TestFormatCloseFileExplorerActionResult:

    def test_zero_windows(self) -> None:
        r = ActionResult(success=True, message="", data={"count": 0})
        assert format_close_file_explorer_message(r) == "No File Explorer windows were open."

    def test_one_window(self) -> None:
        r = ActionResult(success=True, message="", data={"count": 1})
        assert format_close_file_explorer_message(r) == "Closed 1 File Explorer window."

    def test_many_windows(self) -> None:
        r = ActionResult(success=True, message="", data={"count": 5})
        assert format_close_file_explorer_message(r) == "Closed 5 File Explorer windows."

    def test_failure_result(self) -> None:
        r = ActionResult(success=False, message="COM error: access denied.", recoverable=True)
        assert format_close_file_explorer_message(r) == "COM error: access denied."

    def test_failure_no_message_fallback(self) -> None:
        r = ActionResult(success=False, message="")
        assert format_close_file_explorer_message(r) == "Could not close File Explorer windows."

    def test_legacy_dict_still_works(self) -> None:
        """Backward-compat: old dict format must still produce correct output."""
        legacy: CloseFileExplorerWindowsResult = {
            "status": "success",
            "action": "close_file_explorer_windows",
            "count": 2,
        }
        assert format_close_file_explorer_message(legacy) == "Closed 2 File Explorer windows."
