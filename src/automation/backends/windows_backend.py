import sys
from typing import Any, Dict
from automation.backends.base_backend import BaseBackend
from automation.errors import UnsupportedPlatformError, UnsupportedActionError, BackendError
from automation.controllers.mouse_controller import WindowsMouseController
from automation.controllers.keyboard_controller import WindowsKeyboardController
from automation.controllers.window_controller import WindowsWindowController
from utils.logger import setup_logger

logger = setup_logger("WindowsBackend")


class WindowsBackend(BaseBackend):
    """
    Windows-specific automation backend implementation using pywin32 / Win32 / UIA APIs.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._co_initialized = False
        self._mouse = WindowsMouseController(self)
        self._keyboard = WindowsKeyboardController(self)
        self._window = WindowsWindowController(self)
        self._action_registry: Dict[str, Any] = {}

    @classmethod
    def is_supported(cls) -> bool:
        return sys.platform == "win32"

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def mouse(self) -> WindowsMouseController:
        return self._mouse

    @property
    def keyboard(self) -> WindowsKeyboardController:
        return self._keyboard

    @property
    def window(self) -> WindowsWindowController:
        return self._window

    def initialize(self) -> None:
        if not self.is_supported():
            raise UnsupportedPlatformError("WindowsBackend is only supported on Windows.")
        if self._initialized:
            return

        try:
            # Under Windows, COM initialization is often needed for UI Automation / Shell.Application
            import pythoncom
            pythoncom.CoInitialize()
            self._co_initialized = True
        except ImportError:
            logger.warning("pythoncom/pywin32 not found. Win32 COM features will be unavailable.")
        except Exception as e:
            logger.error(f"Failed to initialize COM library: {e}")
            raise BackendError(f"COM initialization failed: {e}") from e

        # Initialize the Action Registry
        self._action_registry = {
            "ping": self._action_ping,
            "mouse.click": self._mouse.click,
            "mouse.move": self._mouse.move,
            "keyboard.press": self._keyboard.press,
            "keyboard.release": self._keyboard.release,
            "window.focus": self._window.focus,
            "window.maximize": self._window.maximize,
        }

        self._initialized = True
        logger.info("WindowsBackend successfully initialized.")

    def shutdown(self) -> None:
        if not self._initialized:
            return

        if self._co_initialized:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception as e:
                logger.error(f"Failed to uninitialize COM library: {e}")
            self._co_initialized = False

        self._action_registry.clear()
        self._initialized = False
        logger.info("WindowsBackend shut down successfully.")

    def execute_action(self, action_name: str, **kwargs) -> Any:
        if not self._initialized:
            raise BackendError("Backend is not initialized. Call initialize() first.")

        if action_name not in self._action_registry:
            raise UnsupportedActionError(f"Action '{action_name}' is not supported by WindowsBackend.")

        handler = self._action_registry[action_name]
        try:
            logger.info(f"Executing action '{action_name}' with parameters {kwargs}")
            return handler(**kwargs)
        except Exception as e:
            logger.exception(f"Error executing action '{action_name}': {e}")
            raise BackendError(f"Action '{action_name}' failed: {e}") from e

    # --- Foundation Actions for Phase 1 ---

    def _action_ping(self) -> str:
        """
        A basic ping action to verify the pipeline works.
        """
        return "pong"
