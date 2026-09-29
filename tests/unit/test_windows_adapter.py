from unittest.mock import patch

import pytest

from adapters.windows_adapter import WindowsAdapter

pytestmark = pytest.mark.windows_only


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


def test_open_app_canonical_aliases_resolved():
    adapter = WindowsAdapter()
    with patch("adapters.windows_adapter.os.startfile") as mock_start:
        assert "my browser opened" in adapter.open_app("my browser").lower()
        mock_start.assert_called_with("msedge")

        mock_start.reset_mock()
        assert "vs code opened" in adapter.open_app("vs code").lower()
        mock_start.assert_called_with("code")

        mock_start.reset_mock()
        assert "file manager opened" in adapter.open_app("file manager").lower()
        mock_start.assert_called_with("explorer")

        mock_start.reset_mock()
        assert "chrome opened" in adapter.open_app("chrome").lower()
        mock_start.assert_called_with("chrome")
