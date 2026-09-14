class AutomationError(Exception):
    """Base exception for all automation-related errors."""
    pass


class BackendError(AutomationError):
    """Exceptions encountered within the backend implementation."""
    pass


class UnsupportedPlatformError(BackendError):
    """Raised when the current operating system is not supported by the selected backend."""
    pass


class UnsupportedActionError(BackendError):
    """Raised when the requested action is not supported by the current backend."""
    pass


class SessionError(AutomationError):
    """Errors related to session state, lifecycle, or tracking."""
    pass
