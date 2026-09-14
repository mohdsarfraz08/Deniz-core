import sys
from typing import Any, List, Optional, Type
from automation.backends.base_backend import BaseBackend
from automation.backends.windows_backend import WindowsBackend
from automation.session import AutomationSession
from automation.enums import SessionStatus, ActionStatus
from automation.errors import UnsupportedPlatformError, SessionError
from automation.controllers.mouse_controller import BaseMouseController
from automation.controllers.keyboard_controller import BaseKeyboardController
from automation.controllers.window_controller import BaseWindowController
from utils.logger import setup_logger

logger = setup_logger("AutomationManager")

# Registry of supported backends
BACKENDS: List[Type[BaseBackend]] = [
    WindowsBackend,
]


class AutomationManager:
    """
    High-level manager for coordinating OS automation sessions and action execution.
    """

    def __init__(self, backend: Optional[BaseBackend] = None) -> None:
        self.backend: BaseBackend = (
            backend if backend is not None else self._detect_and_create_backend()
        )
        self._active_session: Optional[AutomationSession] = None

    def _detect_and_create_backend(self) -> BaseBackend:
        for backend_cls in BACKENDS:
            if backend_cls.is_supported():
                return backend_cls()

        raise UnsupportedPlatformError(
            f"No supported automation backend found for platform: '{sys.platform}'"
        )

    def start_session(self) -> AutomationSession:
        if self._active_session is not None and self._active_session.status == SessionStatus.ACTIVE:
            raise SessionError("A session is already active.")

        self.backend.initialize()
        session = AutomationSession()
        session.start()
        self._active_session = session
        logger.info(f"Started automation session '{session.session_id}'.")
        return session

    def end_session(self) -> None:
        if self._active_session is None or self._active_session.status != SessionStatus.ACTIVE:
            raise SessionError("No active session to end.")

        session = self._active_session
        try:
            self.backend.shutdown()
            session.close(SessionStatus.COMPLETED)
            logger.info(f"Ended automation session '{session.session_id}' successfully.")
        except Exception as e:
            session.close(SessionStatus.FAILED)
            logger.error(f"Error during backend shutdown in session '{session.session_id}': {e}")
            raise
        finally:
            self._active_session = None

    def get_active_session(self) -> Optional[AutomationSession]:
        return self._active_session

    def execute(self, action_name: str, **kwargs) -> Any:
        if self._active_session is None or self._active_session.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot execute action: No active session.")

        session = self._active_session
        action_id = session.record_action_start(action_name, kwargs)

        try:
            result = self.backend.execute_action(action_name, **kwargs)
            session.record_action_end(action_id, ActionStatus.SUCCESS)
            return result
        except Exception as e:
            session.record_action_end(action_id, ActionStatus.FAILURE, error=str(e))
            raise

    # --- Controller Layer Delegations ---

    @property
    def mouse(self) -> BaseMouseController:
        if self._active_session is None or self._active_session.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot access mouse controller: No active session.")
        return self.backend.mouse

    @property
    def keyboard(self) -> BaseKeyboardController:
        if self._active_session is None or self._active_session.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot access keyboard controller: No active session.")
        return self.backend.keyboard

    @property
    def window(self) -> BaseWindowController:
        if self._active_session is None or self._active_session.status != SessionStatus.ACTIVE:
            raise SessionError("Cannot access window controller: No active session.")
        return self.backend.window

    # --- Context Manager Protocol ---

    def __enter__(self) -> "AutomationManager":
        self.start_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._active_session is not None and self._active_session.status == SessionStatus.ACTIVE:
            if exc_type is not None:
                # Close the session as failed if an error occurred in the with block
                try:
                    self.backend.shutdown()
                except Exception as e:
                    logger.error(f"Error during backend shutdown in exit handler: {e}")
                self._active_session.close(SessionStatus.FAILED)
                self._active_session = None
            else:
                self.end_session()
