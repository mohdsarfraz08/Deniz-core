import json
from pathlib import Path

import pytest

from engine import AssistantEngine
from core.security.permissions import PermissionChecker


class FakeExecutor:
    def open_app(self, app_name: str) -> str:
        return f"{app_name} opened."

    def close_app(self, app_name: str) -> str:
        return f"{app_name} closed."

    def get_time(self) -> str:
        return "Current time is 10:00:00."

    def get_cpu_usage(self) -> str:
        return "Current CPU usage: 10%"

    def get_memory_usage(self) -> str:
        return "Current Memory usage: 40%"


def test_engine_denies_when_intent_not_permitted(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"greet": False, "open_app": True}), encoding="utf-8")
    engine = AssistantEngine(
        system_executor=FakeExecutor(),
        permission_checker=PermissionChecker(config_path=p),
    )

    assert engine.handle("hello") == "Access denied for this action."
    assert engine.handle("open calc") == "calc opened."


def test_engine_rejects_invalid_input_before_permissions(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"greet": True}), encoding="utf-8")
    engine = AssistantEngine(
        system_executor=FakeExecutor(),
        permission_checker=PermissionChecker(config_path=p),
    )

    ok_msg = engine.handle("bad;echo")
    assert "disallowed" in ok_msg.lower()


def test_engine_unknown_intent_denied_by_default_config(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Shipped config sets unknown:false — user should get denial without adapter work."""
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"greet": True, "unknown": False}), encoding="utf-8")
    engine = AssistantEngine(
        system_executor=FakeExecutor(),
        permission_checker=PermissionChecker(config_path=p),
    )

    with caplog.at_level("WARNING"):
        out = engine.handle("xyzzy nonsense phrase")
    assert out == "Access denied for this action."
    assert "Access Denied" in caplog.text
