from typing import Protocol

from core.action_results import ActionResult


class SystemExecutor(Protocol):
    """Contract that all platform adapters should satisfy."""

    def open_app(self, app_name: str) -> str:
        ...

    def close_app(self, app_name: str) -> str:
        ...

    def close_file_explorer_windows(self) -> ActionResult:
        ...

    def get_time(self) -> str:
        ...

    def get_cpu_usage(self) -> str:
        ...

    def get_memory_usage(self) -> str:
        ...