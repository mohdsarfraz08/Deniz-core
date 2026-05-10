from unittest.mock import MagicMock

from core.security.terminal_trust import (
    ObservableTerminal,
    append_workload_hint_if_any,
    format_multi_terminal_disambiguation,
    format_single_terminal_need_focus,
    is_assistant_owned_session,
)


def test_is_assistant_owned_session():
    assert is_assistant_owned_session("assistant_launch") is True
    assert is_assistant_owned_session("other") is False


def test_format_multi_terminal_disambiguation():
    text = format_multi_terminal_disambiguation(
        [
            ObservableTerminal(1, "x.exe", "X"),
            ObservableTerminal(2, "y.exe", "Y"),
        ]
    )
    assert "multiple terminal sessions" in text.lower()
    assert "PID 1" in text and "PID 2" in text
    assert "risk" in text.lower()
    assert "reply with" in text.lower()
    assert "number" in text.lower() and "pid" in text.lower()


def test_format_single_terminal_need_focus():
    assert "focus" in format_single_terminal_need_focus().lower()


def test_append_workload_hint_if_any(monkeypatch):
    monkeypatch.setattr(
        "core.security.terminal_trust.collect_risky_child_hints",
        lambda pid, max_names=5: ["node.exe"],
    )
    out = append_workload_hint_if_any(1, "Closed.")
    assert "Heads-up" in out
    assert "node.exe" in out


def test_list_observable_terminal_sessions_filters(monkeypatch):
    proc = MagicMock()
    proc.info = {"pid": 42, "name": "powershell.exe"}

    def fake_iter(attrs):
        yield proc

    monkeypatch.setattr("core.security.terminal_trust.psutil.process_iter", fake_iter)
    from core.security.terminal_trust import list_observable_terminal_sessions

    lst = list_observable_terminal_sessions(max_items=5)
    assert len(lst) == 1
    assert lst[0].pid == 42
