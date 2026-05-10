"""Workload-aware terminal labels, advisory risk, and disambiguation ordering."""

from unittest.mock import MagicMock

from core.security.terminal_session_analysis import (
    TerminalRiskLevel,
    analyze_terminal_session,
    analyze_sessions_for_disambiguation,
    resolve_focused_listed_pid,
    risk_label_public,
)
from core.security.terminal_trust import ObservableTerminal
from core.session.app_registry import AppSessionEntry


def test_risk_label_public_never_says_safe():
    low = risk_label_public(TerminalRiskLevel.LOW).lower()
    assert "safe" not in low
    assert "low" in low and "risk" in low


def test_idle_powershell(monkeypatch):
    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(100, "powershell.exe", "PowerShell")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert info.display_name == "Idle PowerShell"
    assert info.risk_level == TerminalRiskLevel.LOW


def test_python_workload(monkeypatch):
    ch = MagicMock()
    ch.name = MagicMock(return_value="python.exe")
    ch.cmdline = MagicMock(return_value=["python", "tool.py"])

    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[ch])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(101, "powershell.exe", "PowerShell")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert "Python Script" in info.display_name
    assert info.risk_level == TerminalRiskLevel.MEDIUM


def test_node_npm_classification(monkeypatch):
    ch = MagicMock()
    ch.name = MagicMock(return_value="node.exe")
    ch.cmdline = MagicMock(return_value=["node", "server.js"])

    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[ch])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(102, "powershell.exe", "PowerShell")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert "npm dev server" in info.display_name
    assert info.risk_level == TerminalRiskLevel.HIGH


def test_ssh_classification(monkeypatch):
    ch = MagicMock()
    ch.name = MagicMock(return_value="ssh.exe")
    ch.cmdline = MagicMock(return_value=["ssh", "user@host"])

    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[ch])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(103, "powershell.exe", "PowerShell")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert info.display_name == "SSH Session"
    assert info.risk_level == TerminalRiskLevel.HIGH


def test_assistant_owned_sorted_first(monkeypatch):
    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.pid_exists", lambda pid: True)
    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = [
        ObservableTerminal(10, "powershell.exe", "PowerShell"),
        ObservableTerminal(20, "powershell.exe", "PowerShell"),
    ]
    assistant = AppSessionEntry(
        pid=20,
        process_name="WindowsTerminal.exe",
        launch_method="wt",
        launch_canonical="terminal",
    )
    out = analyze_sessions_for_disambiguation(
        obs,
        assistant_entries=[assistant],
        foreground_pid=None,
    )
    assert out[0].pid == 20
    assert out[0].is_assistant_owned is True
    assert "Assistant" in out[0].display_name


def test_focused_sorted_before_unfocused(monkeypatch):
    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = [
        ObservableTerminal(10, "powershell.exe", "PowerShell"),
        ObservableTerminal(11, "powershell.exe", "PowerShell"),
    ]
    out = analyze_sessions_for_disambiguation(
        obs,
        assistant_entries=[],
        foreground_pid=11,
    )
    assert out[0].pid == 11
    assert out[0].is_focused is True


def test_risk_order_low_before_high(monkeypatch):
    """Same assistant/focus state: lower advisory risk sorts earlier."""

    def factory(pid):
        p = MagicMock()
        if pid == 30:
            ch = MagicMock()
            ch.name = MagicMock(return_value="ssh.exe")
            ch.cmdline = MagicMock(return_value=["ssh", "x"])
            p.children = MagicMock(return_value=[ch])
        else:
            p.children = MagicMock(return_value=[])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = [
        ObservableTerminal(30, "powershell.exe", "PowerShell"),
        ObservableTerminal(31, "powershell.exe", "PowerShell"),
    ]
    out = analyze_sessions_for_disambiguation(obs, assistant_entries=[], foreground_pid=None)
    assert out[0].pid == 31
    assert out[0].risk_level == TerminalRiskLevel.LOW
    assert out[1].pid == 30
    assert out[1].risk_level == TerminalRiskLevel.HIGH


def test_conhost_suppresses_exe_name(monkeypatch):
    ch = MagicMock()
    ch.name = MagicMock(return_value="powershell.exe")
    ch.cmdline = MagicMock(return_value=["powershell"])

    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[ch])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(200, "conhost.exe", "Console host")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert "conhost" not in info.display_name.lower()
    assert "Idle PowerShell" in info.display_name


def test_resolve_focused_direct_pid():
    assert resolve_focused_listed_pid(7, [3, 7, 9]) == 7


def test_git_medium(monkeypatch):
    ch = MagicMock()
    ch.name = MagicMock(return_value="git.exe")
    ch.cmdline = MagicMock(return_value=["git", "pull"])

    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[ch])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(104, "powershell.exe", "PowerShell")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert info.display_name == "Git Operation"
    assert info.risk_level == TerminalRiskLevel.MEDIUM


def test_multiple_signals_ssh_wins(monkeypatch):
    """SSH outranks git when both appear under the same tree."""

    ssh = MagicMock()
    ssh.name = MagicMock(return_value="ssh.exe")
    ssh.cmdline = MagicMock(return_value=["ssh", "h"])

    git = MagicMock()
    git.name = MagicMock(return_value="git.exe")
    git.cmdline = MagicMock(return_value=["git", "status"])

    def factory(pid):
        p = MagicMock()
        p.children = MagicMock(return_value=[ssh, git])
        return p

    monkeypatch.setattr("core.security.terminal_session_analysis.psutil.Process", factory)
    obs = ObservableTerminal(105, "powershell.exe", "PowerShell")
    info = analyze_terminal_session(obs, assistant_entry=None, is_focused=False)
    assert info.display_name == "SSH Session"
