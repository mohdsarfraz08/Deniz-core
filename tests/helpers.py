"""Shared test doubles and permission helpers (importable from unit tests)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MiniExecutor:
    """Minimal fake system executor for engine pipeline and security tests."""

    def open_app(self, app_name: str) -> str:
        return f"{app_name} opened."

    def close_app(self, app_name: str) -> str:
        return f"{app_name} closed."

    def close_file_explorer_windows(self) -> dict[str, Any]:
        return {
            "status": "success",
            "action": "close_file_explorer_windows",
            "count": 0,
        }

    def get_time(self) -> str:
        return "t"

    def get_cpu_usage(self) -> str:
        return "cpu"

    def get_memory_usage(self) -> str:
        return "mem"


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
