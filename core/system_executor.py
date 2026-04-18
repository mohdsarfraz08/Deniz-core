from typing import Protocol


class SystemExecutor(Protocol):
    """Contract that all platform adapters should satisfy."""

    def open_app(self, app_name: str) -> str:
        ...

    def close_app(self, app_name: str) -> str:
        ...

    def get_time(self) -> str:
        ...

    def get_cpu_usage(self) -> str:
        ...

    def get_memory_usage(self) -> str:
        ...