import json
from pathlib import Path

import pytest

from core.security.permissions import PermissionChecker


def test_permission_checker_default_deny(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"greet": True}), encoding="utf-8")
    checker = PermissionChecker(config_path=p)

    assert checker.is_allowed("greet") is True
    assert checker.is_allowed("open_app") is False
    assert checker.is_allowed("unknown") is False


def test_permission_checker_explicit_false(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"greet": False}), encoding="utf-8")
    checker = PermissionChecker(config_path=p)

    assert checker.is_allowed("greet") is False
