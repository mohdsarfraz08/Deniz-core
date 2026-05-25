"""Engine orchestration: validation order, failures, and injected executor behavior."""

from pathlib import Path
from unittest.mock import patch

import pytest

from core.security.permissions import PermissionChecker
from engine import AssistantEngine
from helpers import MiniExecutor, repo_permissions_path, write_permissions


def test_engine_returns_validation_error_for_empty_and_whitespace(
    mini_executor: MiniExecutor,
) -> None:
    engine = AssistantEngine(
        system_executor=mini_executor,
        permission_checker=PermissionChecker(config_path=repo_permissions_path()),
    )
    assert engine.handle("") == "Input cannot be empty."
    assert engine.handle("   ") == "Input cannot be empty."


def test_engine_internal_error_when_executor_raises(tmp_path: Path) -> None:
    perm = write_permissions(tmp_path, {"get_cpu_usage": True})

    class Boom(MiniExecutor):
        def get_cpu_usage(self) -> str:
            raise RuntimeError("simulated adapter failure")

    engine = AssistantEngine(
        system_executor=Boom(),
        permission_checker=PermissionChecker(config_path=perm),
    )
    assert engine.handle("check cpu") == "Internal processing error."


def test_engine_init_propagates_executor_construct_failure() -> None:
    class Bad:
        def __init__(self) -> None:
            raise RuntimeError("cannot construct adapter")

    with pytest.raises(RuntimeError, match="cannot construct"):
        AssistantEngine(system_executor=Bad())


def test_engine_init_logs_and_raises_when_default_adapter_fails() -> None:
    with patch(
        "engine.create_system_executor",
        side_effect=RuntimeError("no adapter"),
    ):
        with pytest.raises(RuntimeError, match="no adapter"):
            AssistantEngine()


@pytest.mark.parametrize(
    "text,substr",
    [
        ("foo`bar", "disallowed"),
        ("x$y", "disallowed"),
        ("a\r\nb", "disallowed"),
    ],
)
def test_engine_surfaces_validator_messages(
    text: str,
    substr: str,
    tmp_path: Path,
    mini_executor: MiniExecutor,
) -> None:
    perm = write_permissions(tmp_path, {"greet": True})
    engine = AssistantEngine(
        system_executor=mini_executor,
        permission_checker=PermissionChecker(config_path=perm),
    )
    out = engine.handle(text)
    assert substr in out.lower()
