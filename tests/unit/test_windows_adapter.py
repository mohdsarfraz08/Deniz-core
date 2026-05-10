from unittest.mock import patch

from adapters.windows_adapter import WindowsAdapter


def test_close_app_explorer_exe_returns_window_level_hint():
    adapter = WindowsAdapter()
    msg = adapter.close_app("explorer.exe")
    assert "window-level" in msg.lower()
    assert "file explorer" in msg.lower()


def test_close_app_critical_process_blocked_without_termination():
    adapter = WindowsAdapter()
    msg = adapter.close_app("winlogon")
    assert "blocked" in msg.lower()
    assert "critical" in msg.lower()


def test_open_app_oserror_surfaces_message():
    adapter = WindowsAdapter()
    with patch("adapters.windows_adapter.os.startfile", side_effect=OSError("access denied")):
        msg = adapter.open_app("fake-app-xyz")
    assert "error opening" in msg.lower()
    assert "access denied" in msg.lower()
