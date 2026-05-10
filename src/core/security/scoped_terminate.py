"""
Scoped single-PID termination with exit verification.

Used for assistant-initiated closes only — not global executable kills.
"""

from __future__ import annotations

import psutil


def terminate_pid_scoped(pid: int) -> str | None:
    """
    Signal termination and wait until ``pid`` is gone.

    On Windows, ``terminate()`` can return before the process finishes exiting; callers
    should not claim success without waiting. Escalates to ``kill()`` on timeout.

    Returns ``None`` if the process no longer exists (including already exited before
    we ran). Returns a user-facing error string on failure.
    """
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return None

    try:
        proc.terminate()
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied as e:
        return f"Couldn't close that session (access denied: {e})."

    try:
        proc.wait(timeout=12)
    except psutil.NoSuchProcess:
        return None
    except psutil.TimeoutExpired:
        try:
            proc.kill()
        except psutil.NoSuchProcess:
            return None
        except psutil.AccessDenied as e:
            return f"Couldn't close that session (access denied: {e})."
        try:
            proc.wait(timeout=8)
        except psutil.NoSuchProcess:
            return None
        except psutil.TimeoutExpired:
            return (
                "Couldn't confirm the process exited; it may still be running. "
                "Check Task Manager or try closing the window manually."
            )
    return None
