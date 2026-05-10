"""Engine orchestration: validation order, failures, and injected executor behavior."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from engine import AssistantEngine
from core.security.permissions import PermissionChecker


class _MiniExec:
    """Minimal executor for pipeline tests."""

    def open_app(self, app_name: str) -> str:
        return f"{app_name} opened."

    def close_app(self, app_name: str) -> str:
        return f"{app_name} closed."

    def close_file_explorer_windows(self):
        return {"status": "success", "action": "close_file_explorer_windows", "count": 0}

    def get_time(self) -> str:
        return "t"

    def get_cpu_usage(self) -> str:
        return "cpu"

    def get_memory_usage(self) -> str:
        return "mem"


def test_engine_returns_validation_error_for_empty_and_whitespace() -> None:
    p = Path(__file__).resolve().parents[2] / "config" / "permissions.json"
    engine = AssistantEngine(
        system_executor=_MiniExec(),
        permission_checker=PermissionChecker(config_path=p),
    )
    assert engine.handle("") == "Input cannot be empty."
    assert engine.handle("   ") == "Input cannot be empty."


def test_engine_internal_error_when_executor_raises(tmp_path: Path) -> None:
    perm = tmp_path / "perm.json"
    perm.write_text(json.dumps({"get_cpu_usage": True}), encoding="utf-8")

    class Boom(_MiniExec):
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
    with patch("engine.WindowsAdapter", side_effect=RuntimeError("no adapter")):
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
def test_engine_surfaces_validator_messages(text: str, substr: str, tmp_path: Path) -> None:
    perm = tmp_path / "perm.json"
    perm.write_text(json.dumps({"greet": True}), encoding="utf-8")
    engine = AssistantEngine(
        system_executor=_MiniExec(),
        permission_checker=PermissionChecker(config_path=perm),
    )
    out = engine.handle(text)
    assert substr in out.lower()
