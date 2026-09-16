"""
Linux integration: core intents (apps, metrics, file managers).

Terminal disambiguation, risky-close confirmation, and session-registry terminal
tracking are Windows-only in v1. This adapter does not expose pending resolvers.
"""

from __future__ import annotations

import datetime
import logging
import shutil
import subprocess

import psutil

from .base_adapter import BaseAdapter
from core.action_results import ActionResult
from core.security.path_guard import PathGuard
from core.security.process_kill_policy import is_global_mass_kill_blocked, normalize_exe_name
from core.session.app_registry import SessionRegistry

# Process names (lowercase) that must not be closed by generic name iteration.
CRITICAL_PROCESSES: frozenset[str] = frozenset(
    {
        "systemd",
        "init",
        "kernel",
        "kthreadd",
        "sshd",
    }
)

logger = logging.getLogger("LinuxAdapter")

# File-manager processes closed by ``close_file_explorer_windows`` (process-level, not per-window).
FILE_MANAGER_PROCESSES: frozenset[str] = frozenset(
    {
        "nautilus",
        "nautilus-desktop",
        "dolphin",
        "dolphin-bin",
        "thunar",
        "nemo",
        "pcmanfm",
    }
)


class LinuxAdapter(BaseAdapter):
    """Minimal Linux ``BaseAdapter`` for core CLI intents."""

    def __init__(self, session_registry: SessionRegistry | None = None) -> None:
        self._session_registry = session_registry  # reserved for future parity
        # PathGuard reads workspace_root from config/settings.json.
        # Falls back to repo_root/workspace on missing or invalid config.
        self._path_guard = PathGuard()

    def execute_command(self, command: str) -> str:
        return f"Executing {command} on Linux"

    def get_status(self) -> str:
        return "Linux System Active"

    def open_app(self, app_name: str) -> str:
        name = app_name.strip()
        if not name:
            return "Error opening : empty name"

        executable = shutil.which(name)
        if executable:
            try:
                subprocess.Popen(
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"{name} opened."
            except OSError as e:
                logger.error(
                    "open_app OS failure: app=%r errno=%r detail=%r",
                    name, e.errno, str(e),
                )
                return f"Error opening {name}: {e}"

        xdg = shutil.which("xdg-open")
        if xdg:
            try:
                subprocess.Popen(
                    [xdg, name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return f"{name} opened."
            except OSError as e:
                logger.error(
                    "open_app xdg-open failure: app=%r errno=%r detail=%r",
                    name, e.errno, str(e),
                )
                return f"Error opening {name}: {e}"

        return f"Error opening {name}: application not found in PATH"

    def close_app(self, app_name: str) -> str:
        target = app_name.strip().lower()
        if target.endswith(".exe"):
            target = target[: -len(".exe")]

        if target in CRITICAL_PROCESSES:
            return f"Blocked: {target} is a critical system process."

        exe_norm = normalize_exe_name(target)
        if is_global_mass_kill_blocked(exe_norm):
            return (
                "Can't close every running instance of that program by name. "
                "Focus the window you mean to close."
            )

        found = False
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                base = pname.removesuffix(".exe")
                if base == target or pname == target:
                    proc.terminate()
                    found = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if found:
            return f"{target} closed successfully."
        return f"{target} is not running."

    def close_file_explorer_windows(self) -> ActionResult:
        """
        Terminate file-manager processes (Nautilus, Dolphin, etc.) and return
        a structured ActionResult.

        Unlike Windows, this does not close individual folder windows via Shell COM.
        """
        closed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                base = pname.removesuffix(".exe")
                if base in FILE_MANAGER_PROCESSES or pname in FILE_MANAGER_PROCESSES:
                    proc.terminate()
                    closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return ActionResult(
            success=True,
            message="",  # formatted by format_close_file_explorer_message in IntentEngine
            data={"count": closed},
        )

    def get_time(self) -> str:
        return f"Current time is {datetime.datetime.now().strftime('%H:%M:%S')}."

    def get_cpu_usage(self) -> str:
        usage = psutil.cpu_percent(interval=1)
        return f"Current CPU usage: {usage}%"

    def get_memory_usage(self) -> str:
        usage = psutil.virtual_memory().percent
        return f"Current Memory usage: {usage}%"

    # -------------------------------------------------------------------------
    # Phase 9 — File System Tools
    # All methods call PathGuard.sanitize_path() as the mandatory first gate.
    # No I/O is performed until the path is verified inside the sandbox.
    # -------------------------------------------------------------------------

    def create_file(self, path: str, content: str = "") -> ActionResult:
        """Create a new file inside the workspace sandbox.

        PathGuard validates the path first. Parent directories are created
        automatically. Returns a non-recoverable failure for sandbox violations.
        """
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("create_file blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return ActionResult(success=True, message=f"File created: {resolved.name}")
        except OSError as exc:
            logger.error("create_file OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not create file: {exc}", recoverable=True)

    def read_file(self, path: str) -> ActionResult:
        """Read and return the text content of a sandboxed file."""
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("read_file blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            content = resolved.read_text(encoding="utf-8")
            return ActionResult(
                success=True,
                message=f"{resolved.name} contents:\n{content}",
                data={"content": content, "path": resolved.name},
            )
        except FileNotFoundError:
            return ActionResult(success=False, message=f"File not found: {resolved.name}", recoverable=False)
        except OSError as exc:
            logger.error("read_file OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not read file: {exc}", recoverable=True)

    def write_file(self, path: str, content: str) -> ActionResult:
        """Overwrite a sandboxed file with new content, creating it if needed."""
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("write_file blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding="utf-8")
            return ActionResult(success=True, message=f"{resolved.name} written.")
        except OSError as exc:
            logger.error("write_file OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not write file: {exc}", recoverable=True)

    def append_file(self, path: str, content: str) -> ActionResult:
        """Append content to a sandboxed file, creating it if needed."""
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("append_file blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
            with resolved.open("a", encoding="utf-8") as fh:
                fh.write(content)
            return ActionResult(success=True, message=f"Content appended to {resolved.name}.")
        except OSError as exc:
            logger.error("append_file OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not append to file: {exc}", recoverable=True)

    def delete_file(self, path: str) -> ActionResult:
        """Permanently delete a sandboxed file.

        DESTRUCTIVE — the IntentEngine PendingRiskyClose confirmation gate
        must obtain explicit user consent before calling this method.
        """
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("delete_file blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            resolved.unlink()
            return ActionResult(success=True, message=f"{resolved.name} deleted.", recoverable=False)
        except FileNotFoundError:
            return ActionResult(success=False, message=f"File not found: {resolved.name}", recoverable=False)
        except OSError as exc:
            logger.error("delete_file OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not delete file: {exc}", recoverable=True)

    def copy_file(self, src: str, dst: str) -> ActionResult:
        """Copy a file within the workspace sandbox. Both paths are validated independently."""
        ok_src, resolved_src, msg_src = self._path_guard.sanitize_path(src)
        if not ok_src:
            logger.error("copy_file src blocked: %s", msg_src)
            return ActionResult(success=False, message=f"Access denied (source): {msg_src}", recoverable=False)
        ok_dst, resolved_dst, msg_dst = self._path_guard.sanitize_path(dst)
        if not ok_dst:
            logger.error("copy_file dst blocked: %s", msg_dst)
            return ActionResult(success=False, message=f"Access denied (destination): {msg_dst}", recoverable=False)
        try:
            resolved_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(resolved_src, resolved_dst)
            return ActionResult(success=True, message=f"Copied {resolved_src.name} \u2192 {resolved_dst.name}.")
        except FileNotFoundError:
            return ActionResult(success=False, message=f"Source not found: {resolved_src.name}", recoverable=False)
        except OSError as exc:
            logger.error("copy_file OS error: src=%r dst=%r error=%r", str(resolved_src), str(resolved_dst), str(exc))
            return ActionResult(success=False, message=f"Could not copy file: {exc}", recoverable=True)

    def move_file(self, src: str, dst: str) -> ActionResult:
        """Move or rename a file within the workspace sandbox.

        Shares the _move_path backend with move_folder (Q2 architectural decision).
        IntentEngine logs this as 'move_file' telemetry; move_folder logs as 'move_folder'.
        """
        return self._move_path(src, dst, kind="file")

    def create_folder(self, path: str) -> ActionResult:
        """Create a directory (and any missing parents) inside the workspace sandbox."""
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("create_folder blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            resolved.mkdir(parents=True, exist_ok=True)
            return ActionResult(success=True, message=f"Folder created: {resolved.name}")
        except OSError as exc:
            logger.error("create_folder OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not create folder: {exc}", recoverable=True)

    def delete_folder(self, path: str) -> ActionResult:
        """Recursively delete a sandboxed directory.

        DESTRUCTIVE — the IntentEngine PendingRiskyClose confirmation gate
        must obtain explicit user consent before calling this method.
        """
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("delete_folder blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            shutil.rmtree(resolved)
            return ActionResult(success=True, message=f"Folder '{resolved.name}' deleted.", recoverable=False)
        except FileNotFoundError:
            return ActionResult(success=False, message=f"Folder not found: {resolved.name}", recoverable=False)
        except OSError as exc:
            logger.error("delete_folder OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not delete folder: {exc}", recoverable=True)

    def move_folder(self, src: str, dst: str) -> ActionResult:
        """Move or rename a directory within the workspace sandbox.

        Shares the _move_path backend with move_file (Q2 architectural decision).
        IntentEngine logs this as 'move_folder' telemetry; move_file logs as 'move_file'.
        """
        return self._move_path(src, dst, kind="folder")

    def list_directory(self, path: str = ".") -> ActionResult:
        """List the immediate children of a sandboxed directory."""
        ok, resolved, msg = self._path_guard.sanitize_path(path)
        if not ok:
            logger.error("list_directory blocked: %s", msg)
            return ActionResult(success=False, message=f"Access denied: {msg}", recoverable=False)
        try:
            entries = sorted(p.name for p in resolved.iterdir())
            listing = "\n".join(entries) if entries else "(empty)"
            return ActionResult(
                success=True,
                message=f"Contents of {resolved.name}:\n{listing}",
                data={"entries": entries, "path": resolved.name},
            )
        except FileNotFoundError:
            return ActionResult(success=False, message=f"Directory not found: {resolved.name}", recoverable=False)
        except NotADirectoryError:
            return ActionResult(success=False, message=f"Not a directory: {resolved.name}", recoverable=False)
        except OSError as exc:
            logger.error("list_directory OS error: path=%r error=%r", str(resolved), str(exc))
            return ActionResult(success=False, message=f"Could not list directory: {exc}", recoverable=True)

    # -------------------------------------------------------------------------
    # Shared move/rename backend  (Q2 architectural decision)
    # Consolidates move_file and move_folder into a single implementation.
    # IntentEngine keeps them as separate telemetry events.
    # -------------------------------------------------------------------------

    def _move_path(self, src: str, dst: str, kind: str) -> ActionResult:
        """Shared backend for move_file and move_folder.

        Both paths are independently validated by PathGuard before any I/O.
        The *kind* parameter ('file' or 'folder') appears only in user-facing
        messages; telemetry differentiation is the responsibility of IntentEngine.
        """
        ok_src, resolved_src, msg_src = self._path_guard.sanitize_path(src)
        if not ok_src:
            logger.error("move_%s src blocked: %s", kind, msg_src)
            return ActionResult(success=False, message=f"Access denied (source): {msg_src}", recoverable=False)
        ok_dst, resolved_dst, msg_dst = self._path_guard.sanitize_path(dst)
        if not ok_dst:
            logger.error("move_%s dst blocked: %s", kind, msg_dst)
            return ActionResult(success=False, message=f"Access denied (destination): {msg_dst}", recoverable=False)
        try:
            resolved_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(resolved_src), str(resolved_dst))
            return ActionResult(success=True, message=f"Moved {resolved_src.name} \u2192 {resolved_dst.name}.")
        except FileNotFoundError:
            return ActionResult(success=False, message=f"Source not found: {resolved_src.name}", recoverable=False)
        except OSError as exc:
            logger.error(
                "move_%s OS error: src=%r dst=%r error=%r",
                kind, str(resolved_src), str(resolved_dst), str(exc),
            )
            return ActionResult(success=False, message=f"Could not move {kind}: {exc}", recoverable=True)
