"""Shared pytest fixtures for engine and permission tests."""

from __future__ import annotations

import json
import sys

import pytest

from core.security.permissions import PermissionChecker
from engine import AssistantEngine
from helpers import (
    MiniExecutor,
    SessionTestExecutor,
    TrackingMiniExecutor,
    write_permissions,
)

__all__ = [
    "MiniExecutor",
    "SessionTestExecutor",
    "TrackingMiniExecutor",
    "write_permissions",
]


def pytest_collection_modifyitems(config, items):
    """Skip windows_only tests on Linux/macOS CI and local non-Windows runs."""
    if sys.platform == "win32":
        return
    skip = pytest.mark.skip(reason="Windows-only test")
    for item in items:
        if "windows_only" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def mini_executor() -> MiniExecutor:
    return MiniExecutor()


@pytest.fixture
def session_test_executor() -> SessionTestExecutor:
    return SessionTestExecutor()


@pytest.fixture
def tracking_mini_executor() -> TrackingMiniExecutor:
    return TrackingMiniExecutor()


@pytest.fixture
def permission_checker_factory(tmp_path):
    """Build a PermissionChecker from a dict mapping (uses tmp_path)."""

    def _factory(mapping: dict[str, bool], *, filename: str = "perm.json") -> PermissionChecker:
        path = write_permissions(tmp_path, mapping, filename=filename)
        return PermissionChecker(config_path=path)

    return _factory


@pytest.fixture
def assistant_engine_factory(mini_executor: MiniExecutor, permission_checker_factory):
    """Build AssistantEngine(system_executor=..., permission_checker=...)."""

    def _factory(
        permissions: dict[str, bool],
        *,
        executor: MiniExecutor | None = None,
        perm_filename: str = "perm.json",
    ) -> AssistantEngine:
        checker = permission_checker_factory(permissions, filename=perm_filename)
        return AssistantEngine(
            system_executor=executor if executor is not None else mini_executor,
            permission_checker=checker,
        )

    return _factory
