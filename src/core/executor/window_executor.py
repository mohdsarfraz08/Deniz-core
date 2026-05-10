"""
Close File Explorer folder windows via Shell.Application COM.

Does not terminate explorer.exe (shell). See module docstring in intent_resolution.
"""

from __future__ import annotations

from core.action_results import CloseFileExplorerWindowsResult


def close_file_explorer_windows_impl() -> CloseFileExplorerWindowsResult:
    try:
        import win32com.client  # type: ignore[import-untyped]
    except ImportError:
        return {
            "status": "error",
            "action": "close_file_explorer_windows",
            "count": 0,
            "detail": "win32com not found. Install pywin32 to use this feature.",
        }

    try:
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
    except Exception as e:
        return {
            "status": "error",
            "action": "close_file_explorer_windows",
            "count": 0,
            "detail": f"Could not access Shell windows: {e}",
        }

    closed = 0
    try:
        count = int(windows.Count)
    except Exception:
        count = 0

    for i in reversed(range(count)):
        try:
            window = windows.Item(i)
        except Exception:
            continue
        if not _is_file_explorer_folder_window(window):
            continue
        try:
            window.Quit()
            closed += 1
        except Exception:
            continue

    return {
        "status": "success",
        "action": "close_file_explorer_windows",
        "count": closed,
    }


def _is_file_explorer_folder_window(window: object) -> bool:
    try:
        full = window.FullName
    except Exception:
        return False
    if not full or not str(full).lower().endswith("explorer.exe"):
        return False

    try:
        url = window.LocationURL
    except Exception:
        url = ""
    url_s = (str(url) if url is not None else "").strip()
    if not url_s:
        return True
    return url_s.lower().startswith("file:///")
