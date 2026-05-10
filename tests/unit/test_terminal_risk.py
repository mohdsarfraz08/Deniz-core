"""Risk tiers and close-confirmation copy for terminal workloads."""

from unittest.mock import MagicMock

from core.security.terminal_trust import (
    RiskLevel,
    _classify_child_risk,
    analyze_terminal_workload,
    format_close_confirmation_prompt,
    workload_requires_close_confirmation,
)


def test_workload_requires_confirmation_only_above_low():
    assert workload_requires_close_confirmation(RiskLevel.LOW) is False
    assert workload_requires_close_confirmation(RiskLevel.MEDIUM) is True
    assert workload_requires_close_confirmation(RiskLevel.HIGH) is True


def test_classify_node_high():
    p = MagicMock()
    p.name.return_value = "node.exe"
    p.cmdline.return_value = ["node", "server.js"]
    lvl, line = _classify_child_risk(p)
    assert lvl == RiskLevel.HIGH
    assert line and "node" in line.lower()


def test_classify_python_medium():
    p = MagicMock()
    p.name.return_value = "python.exe"
    p.cmdline.return_value = ["python", "script.py"]
    lvl, line = _classify_child_risk(p)
    assert lvl == RiskLevel.MEDIUM


def test_format_close_confirmation_prompt_lists_lines():
    text = format_close_confirmation_prompt(["node — node server.js"])
    assert "appears to be running" in text
    assert "node server.js" in text
    assert "yes/no" in text.lower()


def test_analyze_terminal_workload_empty(monkeypatch):
    root = MagicMock()
    root.children = MagicMock(return_value=[])

    monkeypatch.setattr("core.security.terminal_trust.psutil.Process", lambda pid: root)
    lvl, lines = analyze_terminal_workload(1)
    assert lvl == RiskLevel.LOW
    assert lines == []
