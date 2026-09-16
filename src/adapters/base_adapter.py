from abc import ABC, abstractmethod

from core.action_results import ActionResult


class BaseAdapter(ABC):
    @abstractmethod
    def execute_command(self, command: str):
        pass

    @abstractmethod
    def get_status(self):
        pass

    @abstractmethod
    def open_app(self, app_name: str):
        pass

    @abstractmethod
    def close_app(self, app_name: str):
        pass

    @abstractmethod
    def close_file_explorer_windows(self) -> ActionResult:
        pass

    @abstractmethod
    def get_time(self):
        pass

    @abstractmethod
    def get_cpu_usage(self):
        pass

    @abstractmethod
    def get_memory_usage(self):
        pass

    # -------------------------------------------------------------------------
    # Phase 9 — File System Tool Contracts
    # -------------------------------------------------------------------------

    @abstractmethod
    def create_file(self, path: str, content: str = "") -> ActionResult:
        """Create a new file at *path* inside the workspace sandbox.

        If parent directories do not exist they are created automatically.
        Returns ActionResult(success=False, recoverable=False) when the path
        violates sandbox containment (PathSecurityError).
        """

    @abstractmethod
    def read_file(self, path: str) -> ActionResult:
        """Read and return the text contents of *path* from the workspace sandbox.

        Returns ActionResult.data["content"] with the file text on success.
        """

    @abstractmethod
    def write_file(self, path: str, content: str) -> ActionResult:
        """Overwrite *path* in the workspace sandbox with *content*.

        Creates the file if it does not exist; truncates it if it does.
        """

    @abstractmethod
    def append_file(self, path: str, content: str) -> ActionResult:
        """Append *content* to *path* in the workspace sandbox.

        Creates the file if it does not exist.
        """

    @abstractmethod
    def delete_file(self, path: str) -> ActionResult:
        """Permanently delete *path* from the workspace sandbox.

        DESTRUCTIVE — callers must obtain explicit user confirmation before
        invoking this method. The IntentEngine PendingRiskyClose gate is the
        authoritative enforcement point.
        """

    @abstractmethod
    def copy_file(self, src: str, dst: str) -> ActionResult:
        """Copy *src* to *dst*, both within the workspace sandbox.

        Both paths are independently validated by PathGuard before any I/O.
        """

    @abstractmethod
    def move_file(self, src: str, dst: str) -> ActionResult:
        """Move or rename a file within the workspace sandbox.

        Backing implementation is shared with move_folder; the caller
        (IntentEngine) logs them as distinct telemetry actions.
        """

    @abstractmethod
    def create_folder(self, path: str) -> ActionResult:
        """Create *path* as a directory (and any missing parents) in the workspace sandbox."""

    @abstractmethod
    def delete_folder(self, path: str) -> ActionResult:
        """Recursively delete *path* from the workspace sandbox.

        DESTRUCTIVE — same confirmation requirements as delete_file.
        """

    @abstractmethod
    def move_folder(self, src: str, dst: str) -> ActionResult:
        """Move or rename a directory within the workspace sandbox.

        Backing implementation is shared with move_file; the caller
        (IntentEngine) logs them as distinct telemetry actions (Q2 decision).
        """

    @abstractmethod
    def list_directory(self, path: str = ".") -> ActionResult:
        """List the immediate children of *path* in the workspace sandbox.

        Returns ActionResult.data["entries"] as a list of name strings.
        """