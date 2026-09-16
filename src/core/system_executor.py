from typing import Protocol

from core.action_results import ActionResult


class SystemExecutor(Protocol):
    """Contract that all platform adapters should satisfy."""

    def open_app(self, app_name: str) -> str:  # pragma: no cover
        ...

    def close_app(self, app_name: str) -> str:  # pragma: no cover
        ...

    def close_file_explorer_windows(self) -> ActionResult:  # pragma: no cover
        ...

    def get_time(self) -> str:  # pragma: no cover
        ...

    def get_cpu_usage(self) -> str:  # pragma: no cover
        ...

    def get_memory_usage(self) -> str:  # pragma: no cover
        ...

    # -------------------------------------------------------------------------
    # Phase 9 — File System Tool Protocol Signatures
    # -------------------------------------------------------------------------

    def create_file(self, path: str, content: str = "") -> ActionResult:  # pragma: no cover
        ...

    def read_file(self, path: str) -> ActionResult:  # pragma: no cover
        ...

    def write_file(self, path: str, content: str) -> ActionResult:  # pragma: no cover
        ...

    def append_file(self, path: str, content: str) -> ActionResult:  # pragma: no cover
        ...

    def delete_file(self, path: str) -> ActionResult:  # pragma: no cover
        ...

    def copy_file(self, src: str, dst: str) -> ActionResult:  # pragma: no cover
        ...

    def move_file(self, src: str, dst: str) -> ActionResult:  # pragma: no cover
        ...

    def create_folder(self, path: str) -> ActionResult:  # pragma: no cover
        ...

    def delete_folder(self, path: str) -> ActionResult:  # pragma: no cover
        ...

    def move_folder(self, src: str, dst: str) -> ActionResult:  # pragma: no cover
        ...

    def list_directory(self, path: str = ".") -> ActionResult:  # pragma: no cover
        ...