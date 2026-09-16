"""Shared test doubles and permission helpers (importable from unit tests)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.action_results import ActionResult


class MiniExecutor:
    """Minimal fake system executor for engine pipeline and security tests."""

    def open_app(self, app_name: str) -> str:
        return f"{app_name} opened."

    def close_app(self, app_name: str) -> str:
        return f"{app_name} closed."

    def close_file_explorer_windows(self) -> ActionResult:
        return ActionResult(success=True, message="", data={"count": 0})

    def get_time(self) -> str:
        return "t"

    def get_cpu_usage(self) -> str:
        return "cpu"

    def get_memory_usage(self) -> str:
        return "mem"

    # Phase 9 file tool stubs
    def create_file(self, path: str, content: str = "") -> ActionResult:
        return ActionResult(success=True, message=f"File created: {path}")

    def read_file(self, path: str) -> ActionResult:
        return ActionResult(success=True, message=f"{path} contents:\n(empty)", data={"content": "", "path": path})

    def write_file(self, path: str, content: str) -> ActionResult:
        return ActionResult(success=True, message=f"{path} written.")

    def append_file(self, path: str, content: str) -> ActionResult:
        return ActionResult(success=True, message=f"Content appended to {path}.")

    def delete_file(self, path: str) -> ActionResult:
        return ActionResult(success=True, message=f"{path} deleted.", recoverable=False)

    def copy_file(self, src: str, dst: str) -> ActionResult:
        return ActionResult(success=True, message=f"Copied {src} \u2192 {dst}.")

    def move_file(self, src: str, dst: str) -> ActionResult:
        return ActionResult(success=True, message=f"Moved {src} \u2192 {dst}.")

    def create_folder(self, path: str) -> ActionResult:
        return ActionResult(success=True, message=f"Folder created: {path}")

    def delete_folder(self, path: str) -> ActionResult:
        return ActionResult(success=True, message=f"Folder '{path}' deleted.", recoverable=False)

    def move_folder(self, src: str, dst: str) -> ActionResult:
        return ActionResult(success=True, message=f"Moved {src} \u2192 {dst}.")

    def list_directory(self, path: str = ".") -> ActionResult:
        return ActionResult(success=True, message="Contents of workspace:\n(empty)", data={"entries": [], "path": path})


class SessionTestExecutor(MiniExecutor):
    """Executor with distinct CPU/memory responses for session follow-up tests."""

    def get_cpu_usage(self) -> str:
        return "cpu-ok"

    def get_memory_usage(self) -> str:
        return "mem-ok"


class TrackingMiniExecutor(MiniExecutor):
    """MiniExecutor that records close_app targets (session pronoun tests)."""

    def __init__(self) -> None:
        self.closed: list[str] = []

    def close_app(self, app_name: str) -> str:
        self.closed.append(app_name)
        return f"{app_name} closed."


def write_permissions(
    tmp_path: Path,
    mapping: dict[str, bool],
    *,
    filename: str = "perm.json",
) -> Path:
    """Write a temporary permissions.json and return its path."""
    path = tmp_path / filename
    path.write_text(json.dumps(mapping), encoding="utf-8")
    return path


def repo_permissions_path() -> Path:
    """Committed default permissions used by production engine."""
    return Path(__file__).resolve().parents[1] / "config" / "permissions.json"
