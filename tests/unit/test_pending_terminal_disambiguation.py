"""Ephemeral terminal disambiguation: follow-up parsing and pending lifecycle."""

import time
from unittest.mock import MagicMock

import pytest

from adapters.terminal_windows import TerminalLaunchResult
from adapters.windows_adapter import WindowsAdapter
from core.security.terminal_trust import ObservableTerminal, RiskLevel
from core.session.pending_terminal_disambiguation import (
    TERMINAL_DISAMBIGUATION_TTL_SEC,
    DisambiguationResolveKind,
    PendingTerminalDisambiguation,
    TerminalDisambiguationOption,
    resolve_terminal_disambiguation_followup,
)
from engine import AssistantEngine


def _opts_two_ps() -> list[TerminalDisambiguationOption]:
    return [
        TerminalDisambiguationOption(1, 14956, "PowerShell", "powershell.exe"),
        TerminalDisambiguationOption(2, 18452, "PowerShell", "powershell.exe"),
    ]


def _pending(options=None, expires_shift: float = 1000.0) -> PendingTerminalDisambiguation:
    now = time.monotonic()
    return PendingTerminalDisambiguation(
        options=options or _opts_two_ps(),
        expires_at=now + expires_shift,
    )


def test_numeric_selection_by_index():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("2", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option is not None and r.option.pid == 18452


def test_numeric_selection_close_prefix():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("close 1", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option.pid == 14956


def test_numeric_selection_close_number():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("close number 2", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option.pid == 18452


def test_terminal_prefix_number():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("terminal 2", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option.pid == 18452


def test_pid_selection_explicit():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("close pid 18452", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option.pid == 18452


def test_pid_selection_bare_digits_matching_list():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("18452", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option.pid == 18452


def test_reject_pid_not_in_options():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("pid 99999", p)
    assert r.kind == DisambiguationResolveKind.ERROR_KEEP
    assert "99999" in (r.message or "")


def test_name_single_match():
    opts = [
        TerminalDisambiguationOption(1, 100, "Console Host", "conhost.exe"),
        TerminalDisambiguationOption(2, 200, "PowerShell", "powershell.exe"),
    ]
    p = _pending(opts)
    r = resolve_terminal_disambiguation_followup("powershell", p)
    assert r.kind == DisambiguationResolveKind.CLOSE_OPTION
    assert r.option.pid == 200


def test_name_ambiguous_narrows():
    p = _pending()
    r = resolve_terminal_disambiguation_followup("powershell", p)
    assert r.kind == DisambiguationResolveKind.NARROW
    assert r.new_pending is not None
    assert len(r.new_pending.options) == 2
    assert "Which" in (r.message or "") and "PowerShell" in (r.message or "")


def test_pending_expiration_message_from_adapter():
    adapter = WindowsAdapter()
    adapter._pending_disambiguation = _pending(expires_shift=-1.0)
    msg = adapter.try_resolve_pending_terminal_disambiguation("2")
    assert "expired" in msg.lower()
    assert adapter._pending_disambiguation is None


def test_clear_pending_after_successful_close(monkeypatch):
    adapter = WindowsAdapter()
    adapter._pending_disambiguation = _pending()

    monkeypatch.setattr(
        "adapters.windows_adapter.WindowsAdapter._risk_gate_before_terminate",
        lambda self, pid: None,
    )
    terminated = []

    def fake_term(pid):
        terminated.append(pid)
        return None

    monkeypatch.setattr("adapters.windows_adapter.terminate_pid_scoped", fake_term)

    msg = adapter.try_resolve_pending_terminal_disambiguation("1")
    assert "Closed" in msg
    assert "14956" in msg or "PowerShell" in msg
    assert adapter._pending_disambiguation is None
    assert 14956 in terminated


def test_fallback_to_parser_when_unresolved():
    adapter = WindowsAdapter()
    adapter._pending_disambiguation = _pending()
    assert adapter.try_resolve_pending_terminal_disambiguation("hello world") is None


@pytest.fixture
def engine_disambig(monkeypatch):
    adapter = WindowsAdapter()
    adapter._pending_disambiguation = _pending()

    monkeypatch.setattr(
        "adapters.windows_adapter.WindowsAdapter._risk_gate_before_terminate",
        lambda self, pid: None,
    )
    terminated = []

    def fake_term(pid):
        terminated.append(pid)
        return None

    monkeypatch.setattr("adapters.windows_adapter.terminate_pid_scoped", fake_term)
    eng = AssistantEngine(system_executor=adapter)
    return eng, terminated


def test_engine_disambiguation_flow_numeric(engine_disambig):
    eng, terminated = engine_disambig
    out = eng.handle("2")
    assert "Closed" in out
    assert 18452 in terminated


def test_engine_order_risky_before_disambig(monkeypatch):
    adapter = WindowsAdapter()
    from adapters.windows_adapter import PendingRiskyClose
    from core.security.terminal_trust import RiskLevel

    adapter._pending_risky_close = PendingRiskyClose(
        pid=111,
        risk_level=RiskLevel.HIGH,
        workload_lines=["x"],
    )
    adapter._pending_disambiguation = _pending()

    risky_called = []

    def risky(txt):
        risky_called.append(txt)
        return "risky handled"

    monkeypatch.setattr(adapter, "try_resolve_pending_risky_close", risky)
    eng = AssistantEngine(system_executor=adapter)
    out = eng.handle("anything")
    assert out == "risky handled"
    assert risky_called == ["anything"]


def test_ttl_constant_in_reasonable_range():
    assert 30 <= TERMINAL_DISAMBIGUATION_TTL_SEC <= 60


def test_close_terminal_multiple_candidates_sets_pending_and_prompt(monkeypatch):
    adapter = WindowsAdapter()
    monkeypatch.setattr(
        "adapters.windows_adapter.close_focused_terminal_session",
        lambda *a, **k: "The focused window isn't a terminal (notepad.exe).",
    )
    monkeypatch.setattr(
        "adapters.windows_adapter.list_observable_terminal_sessions",
        lambda: [
            ObservableTerminal(14956, "powershell.exe", "PowerShell"),
            ObservableTerminal(18452, "powershell.exe", "PowerShell"),
        ],
    )
    out = adapter.close_app("terminal")
    assert "multiple" in out.lower()
    assert "— PID" in out or "PID" in out
    assert adapter._pending_disambiguation is not None
    assert len(adapter._pending_disambiguation.options) == 2
    assert adapter._pending_disambiguation.options[0].pid == 14956


def test_open_terminal_clears_disambiguation_pending(monkeypatch):
    adapter = WindowsAdapter()
    adapter._pending_disambiguation = _pending()
    monkeypatch.setattr(
        "adapters.windows_adapter.launch_terminal_app",
        lambda canonical: TerminalLaunchResult(
            message="ok",
            pid=1,
            process_name="powershell.exe",
            launch_method="powershell",
        ),
    )
    adapter.open_app("powershell")
    assert adapter._pending_disambiguation is None


def test_disambiguation_choice_then_risk_gate(monkeypatch):
    """After picking from list, MEDIUM/HIGH workload uses existing yes/no flow."""
    adapter = WindowsAdapter()
    adapter._pending_disambiguation = _pending()

    monkeypatch.setattr(
        "adapters.windows_adapter.analyze_terminal_workload",
        lambda pid: (RiskLevel.HIGH, ["node — app.js"]),
    )
    out = adapter.try_resolve_pending_terminal_disambiguation("1")
    assert "yes" in out.lower() and "no" in out.lower()
    assert adapter._pending_disambiguation is None
    assert adapter._pending_risky_close is not None
    assert adapter._pending_risky_close.pid == 14956
