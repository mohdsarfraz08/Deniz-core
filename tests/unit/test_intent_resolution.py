from core.intent_resolution import (
    format_close_file_explorer_message,
    is_file_explorer_window_target,
    terminal_close_request_key,
)
from core.action_results import CloseFileExplorerWindowsResult


def test_is_file_explorer_window_target_aliases():
    assert is_file_explorer_window_target("explorer")
    assert is_file_explorer_window_target("  Explorer.exe  ")
    assert is_file_explorer_window_target("file manager")
    assert is_file_explorer_window_target("my folders")
    assert not is_file_explorer_window_target("notepad")
    assert not is_file_explorer_window_target("")


def test_format_close_file_explorer_message_success():
    r: CloseFileExplorerWindowsResult = {
        "status": "success",
        "action": "close_file_explorer_windows",
        "count": 0,
    }
    assert format_close_file_explorer_message(r) == "No File Explorer windows were open."
    r2: CloseFileExplorerWindowsResult = {**r, "count": 5}
    assert "5 File Explorer windows" in format_close_file_explorer_message(r2)


def test_format_close_file_explorer_message_error():
    r: CloseFileExplorerWindowsResult = {
        "status": "error",
        "action": "close_file_explorer_windows",
        "count": 0,
        "detail": "COM failed",
    }
    assert format_close_file_explorer_message(r) == "COM failed"


def test_terminal_close_request_key_aliases():
    assert terminal_close_request_key("powershell") == "powershell"
    assert terminal_close_request_key("Windows PowerShell") == "powershell"
    assert terminal_close_request_key("pwsh") == "pwsh"
    assert terminal_close_request_key("terminal") == "terminal"
    assert terminal_close_request_key("Windows Terminal") == "terminal"
    assert terminal_close_request_key("notepad") is None


def test_format_close_file_explorer_message_error_without_detail():
    r: CloseFileExplorerWindowsResult = {
        "status": "error",
        "action": "close_file_explorer_windows",
        "count": 0,
    }
    assert (
        format_close_file_explorer_message(r)
        == "Could not close File Explorer windows."
    )
