"""File Explorer window close via Shell COM (mocked win32com)."""

import builtins
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from core.executor.window_executor import (
    _is_file_explorer_folder_window,
    close_file_explorer_windows_impl,
)


def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name == "win32com.client" or (name == "win32com" and "client" in fromlist):
        raise ImportError("no win32com")
    return builtins.__import__(name, globals, locals, fromlist, level)


@pytest.mark.windows_only
def test_close_file_explorer_import_error():
    with patch("builtins.__import__", side_effect=_fake_import):
        result = close_file_explorer_windows_impl()
    assert result["status"] == "error"
    assert "win32com" in (result.get("detail") or "").lower()


@pytest.mark.windows_only
@patch("win32com.client.Dispatch", side_effect=RuntimeError("COM unavailable"))
def test_close_file_explorer_com_dispatch_failure(_mock_dispatch):
    result = close_file_explorer_windows_impl()
    assert result["status"] == "error"
    assert "Shell" in (result.get("detail") or "")


@pytest.mark.windows_only
@patch("win32com.client.Dispatch")
def test_close_file_explorer_closes_folder_windows(mock_dispatch):
    window_ok = MagicMock()
    window_ok.FullName = "C:\\Windows\\explorer.exe"
    window_ok.LocationURL = "file:///C:/Users/test"
    window_ok.Quit = MagicMock()

    window_skip = MagicMock()
    window_skip.FullName = "C:\\Program Files\\app.exe"
    window_skip.LocationURL = ""

    windows = MagicMock()
    windows.Count = 2
    windows.Item = MagicMock(side_effect=lambda i: window_ok if i == 0 else window_skip)

    shell = MagicMock()
    shell.Windows.return_value = windows
    mock_dispatch.return_value = shell

    result = close_file_explorer_windows_impl()

    assert result["status"] == "success"
    assert result["count"] == 1
    window_ok.Quit.assert_called_once()


@pytest.mark.windows_only
@patch("win32com.client.Dispatch")
def test_close_file_explorer_item_access_error_skipped(mock_dispatch):
    windows = MagicMock()
    windows.Count = 1
    windows.Item.side_effect = RuntimeError("no item")

    shell = MagicMock()
    shell.Windows.return_value = windows
    mock_dispatch.return_value = shell

    result = close_file_explorer_windows_impl()
    assert result["status"] == "success"
    assert result["count"] == 0


@pytest.mark.windows_only
@patch("win32com.client.Dispatch")
def test_close_file_explorer_count_parse_failure(mock_dispatch):
    windows = MagicMock()
    windows.Count = "not-a-number"

    shell = MagicMock()
    shell.Windows.return_value = windows
    mock_dispatch.return_value = shell

    result = close_file_explorer_windows_impl()
    assert result["status"] == "success"
    assert result["count"] == 0


@pytest.mark.windows_only
@patch("win32com.client.Dispatch")
def test_close_file_explorer_quit_failure_continues(mock_dispatch):
    window_ok = MagicMock()
    window_ok.FullName = "explorer.exe"
    window_ok.LocationURL = "file:///C:/x"
    window_ok.Quit.side_effect = RuntimeError("access denied")

    windows = MagicMock()
    windows.Count = 1
    windows.Item.return_value = window_ok

    shell = MagicMock()
    shell.Windows.return_value = windows
    mock_dispatch.return_value = shell

    result = close_file_explorer_windows_impl()
    assert result["status"] == "success"
    assert result["count"] == 0


def test_is_file_explorer_folder_window_url_variants():
    w = MagicMock()
    w.FullName = "Explorer.EXE"
    w.LocationURL = ""
    assert _is_file_explorer_folder_window(w) is True

    w2 = MagicMock()
    w2.FullName = "explorer.exe"
    w2.LocationURL = "https://example.com"
    assert _is_file_explorer_folder_window(w2) is False

    w3 = MagicMock()
    w3.FullName = "notepad.exe"
    assert _is_file_explorer_folder_window(w3) is False

    w4 = MagicMock()
    w4.FullName = "explorer.exe"
    type(w4).LocationURL = PropertyMock(side_effect=RuntimeError("no url"))
    assert _is_file_explorer_folder_window(w4) is True

    w5 = MagicMock()
    type(w5).FullName = PropertyMock(side_effect=RuntimeError("no name"))
    assert _is_file_explorer_folder_window(w5) is False
