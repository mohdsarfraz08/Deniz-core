from abc import ABC, abstractmethod
from typing import Any
from automation.controllers.mouse_controller import BaseMouseController
from automation.controllers.keyboard_controller import BaseKeyboardController
from automation.controllers.window_controller import BaseWindowController


class BaseBackend(ABC):
    """
    Abstract base class for all operating system automation backends.
    """

    @classmethod
    @abstractmethod
    def is_supported(cls) -> bool:
        """
        Return True if this backend is supported on the current platform.
        """
        pass

    @property
    @abstractmethod
    def initialized(self) -> bool:
        """
        Return True if the backend is initialized.
        """
        pass

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the backend and allocate any necessary resources.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Clean up resources allocated during initialization.
        """
        pass

    @abstractmethod
    def execute_action(self, action_name: str, **kwargs) -> Any:
        """
        Execute a specific automation action with the given arguments.
        """
        pass

    @property
    @abstractmethod
    def mouse(self) -> BaseMouseController:
        """
        Return the mouse controller for this backend.
        """
        pass

    @property
    @abstractmethod
    def keyboard(self) -> BaseKeyboardController:
        """
        Return the keyboard controller for this backend.
        """
        pass

    @property
    @abstractmethod
    def window(self) -> BaseWindowController:
        """
        Return the window controller for this backend.
        """
        pass
