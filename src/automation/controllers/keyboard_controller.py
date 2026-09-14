from abc import ABC, abstractmethod
from automation.controllers.base_controller import BaseController


class BaseKeyboardController(BaseController, ABC):
    """
    Abstract interface for keyboard interaction.
    """

    @abstractmethod
    def press(self, key: str) -> None:
        """
        Press and hold a key.
        """
        pass

    @abstractmethod
    def release(self, key: str) -> None:
        """
        Release a key.
        """
        pass


class WindowsKeyboardController(BaseKeyboardController):
    """
    Windows implementation of the keyboard controller (placeholder for Phase 1).
    """

    def press(self, key: str) -> None:
        # Placeholder for actual Win32 keyboard press implementation in Phase 4
        pass

    def release(self, key: str) -> None:
        # Placeholder for actual Win32 keyboard release implementation in Phase 4
        pass
