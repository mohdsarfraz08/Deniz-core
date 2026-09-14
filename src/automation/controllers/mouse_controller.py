from abc import ABC, abstractmethod
from typing import Union
from automation.controllers.base_controller import BaseController
from automation.enums import MouseButton


class BaseMouseController(BaseController, ABC):
    """
    Abstract interface for mouse interaction.
    """

    @abstractmethod
    def click(self, x: int, y: int, button: Union[MouseButton, str] = MouseButton.LEFT) -> None:
        """
        Click at (x, y) with the specified button.
        """
        pass

    @abstractmethod
    def move(self, x: int, y: int) -> None:
        """
        Move mouse to coordinate (x, y).
        """
        pass


class WindowsMouseController(BaseMouseController):
    """
    Windows implementation of the mouse controller (placeholder for Phase 1).
    """

    def click(self, x: int, y: int, button: Union[MouseButton, str] = MouseButton.LEFT) -> None:
        # Placeholder for actual Win32 mouse click implementation in Phase 3
        pass

    def move(self, x: int, y: int) -> None:
        # Placeholder for actual Win32 mouse move implementation in Phase 3
        pass
