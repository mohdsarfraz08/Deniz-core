from automation.manager import AutomationManager
from automation.session import AutomationSession, AutomationActionRecord
from automation.enums import (
    SessionStatus,
    ActionStatus,
    WindowState,
    MouseButton,
    KeyState,
)
from automation.errors import (
    AutomationError,
    BackendError,
    UnsupportedPlatformError,
    UnsupportedActionError,
    SessionError,
)

__all__ = [
    "AutomationManager",
    "AutomationSession",
    "AutomationActionRecord",
    "SessionStatus",
    "ActionStatus",
    "WindowState",
    "MouseButton",
    "KeyState",
    "AutomationError",
    "BackendError",
    "UnsupportedPlatformError",
    "UnsupportedActionError",
    "SessionError",
]
