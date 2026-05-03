from adapters.windows_adapter import WindowsAdapter


def test_close_app_explorer_exe_returns_window_level_hint():
    adapter = WindowsAdapter()
    msg = adapter.close_app("explorer.exe")
    assert "window-level" in msg.lower()
    assert "file explorer" in msg.lower()
