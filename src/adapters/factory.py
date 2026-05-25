"""Platform-specific SystemExecutor factory."""

from __future__ import annotations

import sys

from core.session.app_registry import SessionRegistry
from core.system_executor import SystemExecutor


def create_system_executor(
    session_registry: SessionRegistry | None = None,
) -> SystemExecutor:
    """Load the adapter for the current OS (lazy import keeps pywin32 Windows-only)."""
    if sys.platform == "win32":
        from adapters.windows_adapter import WindowsAdapter

        return WindowsAdapter(session_registry=session_registry)
    if sys.platform.startswith("linux"):
        from adapters.linux_adapter import LinuxAdapter

        return LinuxAdapter(session_registry=session_registry)
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
