"""Focused terminal close / launch helpers (mocked; no real processes)."""

from unittest.mock import ANY, MagicMock, patch

import pytest

from adapters.terminal_windows import (
    TerminalLaunchResult,
    close_focused_terminal_session,
    launch_terminal_app,
    normalize_terminal_open_target,
)
from adapters.windows_adapter import WindowsAdapter
from core.session.app_registry import SessionRegistry

pytestmark = pytest.mark.windows_only


def test_normalize_terminal_open_target_powershell_family():
    assert normalize_terminal_open_target("powershell") == "powershell"
    assert normalize_terminal_open_target("PowerShell.exe") == "powershell"
    assert normalize_terminal_open_target("Windows Terminal") == "terminal"


@patch("adapters.terminal_windows.terminate_pid_scoped", return_value=None)
@patch("adapters.terminal_windows.psutil.Process")
@patch("adapters.terminal_windows._get_foreground_pid", return_value=(100, None))
def test_close_focused_powershell_terminates_single_pid(mock_fg, mock_Process, mock_term):
    proc = MagicMock()
    proc.name.return_value = "powershell.exe"
    proc.pid = 100
    mock_Process.return_value = proc

    msg = close_focused_terminal_session("powershell")

    assert "Closed focused session" in msg
    assert "PID 100" in msg
    mock_term.assert_called_once_with(100)


@patch("adapters.terminal_windows.psutil.Process")
@patch("adapters.terminal_windows._get_foreground_pid", return_value=(100, None))
def test_close_focused_wrong_kind_returns_guidance(mock_fg, mock_Process):
    proc = MagicMock()
    proc.name.return_value = "powershell.exe"
    proc.pid = 100
    mock_Process.return_value = proc

    msg = close_focused_terminal_session("pwsh")

    assert "does not match" in msg
    proc.terminate.assert_not_called()


@patch("adapters.terminal_windows.terminate_pid_scoped", return_value=None)
@patch("adapters.terminal_windows._shell_children_recursive")
@patch("adapters.terminal_windows.psutil.Process")
@patch(
    "adapters.terminal_windows._get_foreground_pid",
    return_value=(8000, None),
)
def test_close_inside_windows_terminal_single_child(
    mock_fg, mock_Process, mock_children, mock_term
):
    host = MagicMock()
    host.name.return_value = "WindowsTerminal.exe"
    mock_Process.return_value = host

    shell = MagicMock()
    shell.name.return_value = "pwsh.exe"
    shell.pid = 9001
    shell.terminate = MagicMock()
    mock_children.return_value = [shell]

    msg = close_focused_terminal_session("pwsh")

    assert "9001" in msg or "pwsh" in msg.lower()
    mock_term.assert_called_once_with(9001)


def test_launch_terminal_app_powershell_prefers_wt(monkeypatch):
    calls = []

    def fake_which(name: str):
        return name if name == "wt.exe" else None

    def fake_popen(args, creationflags=0):
        calls.append(args)
        m = MagicMock()
        m.pid = 555
        return m

    monkeypatch.setattr("adapters.terminal_windows.shutil.which", fake_which)
    monkeypatch.setattr("adapters.terminal_windows.time.sleep", lambda _: None)
    monkeypatch.setattr("adapters.terminal_windows.try_focus_window_for_pid", lambda _p: False)
    monkeypatch.setattr("adapters.terminal_windows.try_window_title_for_pid", lambda _p: None)

    result = launch_terminal_app(
        "powershell",
        popen=fake_popen,
        which=fake_which,
        monotonic=lambda: 0.0,
    )

    assert isinstance(result, TerminalLaunchResult)
    assert "Windows Terminal" in result.message
    assert result.pid == 555
    assert calls and "wt.exe" in calls[0]


def test_open_app_registers_terminal_pid(monkeypatch):
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: True)

    def fake_launch(canonical: str):
        return TerminalLaunchResult(
            message="Opened Windows Terminal.",
            pid=777,
            process_name="WindowsTerminal.exe",
            launch_method="mock",
            window_title=None,
        )

    monkeypatch.setattr("adapters.windows_adapter.launch_terminal_app", fake_launch)

    reg = SessionRegistry()
    adapter = WindowsAdapter(session_registry=reg)

    assert adapter.open_app("powershell").startswith("Opened")
    assert reg.get_last_app("terminal") is not None
    assert reg.get_last_app("terminal").pid == 777


def test_open_app_duplicate_launch_debounced(monkeypatch):
    monkeypatch.setattr("adapters.terminal_windows.time.sleep", lambda _: None)
    monkeypatch.setattr("adapters.terminal_windows.try_focus_window_for_pid", lambda _p: False)
    monkeypatch.setattr(
        "adapters.terminal_windows.try_window_title_for_pid", lambda _p: None
    )

    def fake_which(name: str):
        return name if name == "wt.exe" else None

    def fake_popen(args, creationflags=0):
        m = MagicMock()
        m.pid = 888
        return m

    monkeypatch.setattr("adapters.terminal_windows.shutil.which", fake_which)
    monkeypatch.setattr("adapters.terminal_windows.subprocess.Popen", fake_popen)
    monkeypatch.setattr("adapters.windows_adapter.time.monotonic", lambda: 0.0)

    adapter = WindowsAdapter()
    assert adapter.open_app("powershell").startswith("Opened")
    assert "Ignored duplicate" in adapter.open_app("powershell")


def test_open_app_powershell_then_pwsh_registers_two_sessions(monkeypatch):
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: True)

    def fake_launch(canonical: str):
        pid_map = {"powershell": 1000, "pwsh": 1001}
        return TerminalLaunchResult(
            message="Opened.",
            pid=pid_map.get(canonical, 999),
            process_name="shell.exe",
            launch_method="mock",
            window_title=None,
        )

    monkeypatch.setattr("adapters.windows_adapter.launch_terminal_app", fake_launch)

    adapter = WindowsAdapter()
    adapter.open_app("powershell")
    adapter.open_app("pwsh")
    assert adapter._session_registry.count_category("terminal") == 2


def test_close_app_powershell_uses_focus_when_registry_empty():
    adapter = WindowsAdapter()
    with patch(
        "adapters.windows_adapter.close_focused_terminal_session",
        return_value="Closed focused session (powershell.exe, PID 1).",
    ) as scoped:
        msg = adapter.close_app("powershell")
    scoped.assert_called_once_with("powershell", risk_gate=ANY)
    assert "Closed focused" in msg


def test_close_prefers_registry_over_focused_fallback(monkeypatch):
    monkeypatch.setattr("core.session.app_registry.psutil.pid_exists", lambda pid: True)
    reg = SessionRegistry()
    reg.register_app(
        category="terminal",
        pid=4242,
        process_name="WindowsTerminal.exe",
        launch_method="wt.exe",
        launch_canonical="terminal",
    )
    adapter = WindowsAdapter(session_registry=reg)
    terminated = []

    def fake_term(pid):
        terminated.append(pid)
        return None

    monkeypatch.setattr("adapters.windows_adapter.terminate_pid_scoped", fake_term)

    with patch(
        "adapters.windows_adapter.close_focused_terminal_session"
    ) as focus:
        msg = adapter.close_app("terminal")
    focus.assert_not_called()
    assert 4242 in terminated
    assert "started for you" in msg.lower()
    assert reg.get_last_app("terminal") is None


def test_close_safe_refusal_when_no_registry_and_focus_fails():
    adapter = WindowsAdapter()
    with (
        patch(
            "adapters.windows_adapter.close_focused_terminal_session",
            return_value="The focused window isn't a terminal (notepad.exe). ...",
        ),
        patch(
            "adapters.windows_adapter.list_observable_terminal_sessions",
            return_value=[],
        ),
    ):
        msg = adapter.close_app("powershell")
    assert "couldn't find a safe terminal" in msg.lower()


def test_close_lists_multiple_terminals_when_unfocused(monkeypatch):
    adapter = WindowsAdapter()
    from core.security.terminal_trust import ObservableTerminal

    obs = [
        ObservableTerminal(10, "powershell.exe", "PowerShell"),
        ObservableTerminal(20, "windowsterminal.exe", "Windows Terminal"),
    ]
    with (
        patch(
            "adapters.windows_adapter.close_focused_terminal_session",
            return_value="The focused window isn't a terminal (x).",
        ),
        patch(
            "adapters.windows_adapter.list_observable_terminal_sessions",
            return_value=obs,
        ),
    ):
        msg = adapter.close_app("terminal")
    assert "multiple terminal sessions" in msg.lower()
    assert "PID 10" in msg or "PowerShell" in msg


def test_close_app_notepad_still_uses_name_iteration(monkeypatch):
    adapter = WindowsAdapter()
    seen = []

    def fake_iter(attrs):
        yield MagicMock(info={"name": "notepad.exe"}, terminate=lambda: seen.append(1))

    monkeypatch.setattr("adapters.windows_adapter.psutil.process_iter", fake_iter)

    msg = adapter.close_app("notepad")
    assert seen == [1]
    assert "closed successfully" in msg.lower()


def test_close_app_blocklisted_without_terminal_alias(monkeypatch):
    adapter = WindowsAdapter()
    monkeypatch.setattr(
        "adapters.windows_adapter.psutil.process_iter",
        lambda attrs: iter([]),
    )
    msg = adapter.close_app("conhost.exe")
    assert "can't close" in msg.lower() or "close every" in msg.lower()
