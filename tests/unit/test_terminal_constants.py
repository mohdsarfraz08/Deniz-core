"""Terminal executable constants and close-request matching."""

from adapters.terminal_constants import exe_matches_close_request


def test_exe_matches_close_request_powershell_family():
    assert exe_matches_close_request("powershell", "powershell.exe")
    assert exe_matches_close_request("powershell", "pwsh.exe")
    assert not exe_matches_close_request("powershell", "cmd.exe")


def test_exe_matches_close_request_pwsh_and_cmd():
    assert exe_matches_close_request("pwsh", "pwsh.exe")
    assert not exe_matches_close_request("pwsh", "powershell.exe")
    assert exe_matches_close_request("cmd", "cmd.exe")
    assert not exe_matches_close_request("cmd", "powershell.exe")


def test_exe_matches_close_request_terminal_key():
    assert exe_matches_close_request("terminal", "powershell.exe")
    assert exe_matches_close_request("terminal", "windowsterminal.exe")
    assert not exe_matches_close_request("terminal", "notepad.exe")
    assert not exe_matches_close_request("unknown", "cmd.exe")
