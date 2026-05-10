from core.security.process_kill_policy import (
    GLOBAL_PROCESS_KILL_BLOCKLIST,
    is_global_mass_kill_blocked,
    normalize_exe_name,
)


def test_normalize_exe_adds_exe_suffix():
    assert normalize_exe_name("NOTEPAD") == "notepad.exe"


def test_blocklist_contains_terminal_hosts():
    assert "powershell.exe" in GLOBAL_PROCESS_KILL_BLOCKLIST
    assert "conhost.exe" in GLOBAL_PROCESS_KILL_BLOCKLIST


def test_is_global_mass_kill_blocked():
    assert is_global_mass_kill_blocked("powershell") is True
    assert is_global_mass_kill_blocked("notepad.exe") is False
