"""Engine resolves yes/no before intents when a risky terminal close is pending."""

from unittest.mock import MagicMock

import pytest

from engine import AssistantEngine
from adapters.windows_adapter import PendingRiskyClose, WindowsAdapter
from core.security.terminal_trust import RiskLevel


@pytest.fixture
def engine_with_pending() -> AssistantEngine:
    adapter = WindowsAdapter()
    adapter._pending_risky_close = PendingRiskyClose(
        pid=99999,
        risk_level=RiskLevel.HIGH,
        workload_lines=["node — node app.js"],
    )
    return AssistantEngine(system_executor=adapter)


def test_yes_closes_pending_session(engine_with_pending: AssistantEngine, monkeypatch):
    terminated = []

    def fake_term(pid):
        terminated.append(pid)
        return None

    monkeypatch.setattr("adapters.windows_adapter.terminate_pid_scoped", fake_term)

    out = engine_with_pending.handle("yes")
    assert "Closed as requested" in out
    assert 99999 in terminated
    assert engine_with_pending.executor._pending_risky_close is None


def test_no_cancels_pending(engine_with_pending: AssistantEngine):
    out = engine_with_pending.handle("no")
    assert "cancelled" in out.lower()
    assert engine_with_pending.executor._pending_risky_close is None


def test_unclear_reply_when_pending(engine_with_pending: AssistantEngine):
    out = engine_with_pending.handle("maybe")
    assert "yes" in out.lower() and "no" in out.lower()
