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


def test_permission_checker_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        PermissionChecker(config_path=p)


def test_permission_checker_ignores_non_bool_values(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"greet": True, "open_app": "yes"}), encoding="utf-8")
    checker = PermissionChecker(config_path=p)
    assert checker.is_allowed("greet") is True
    assert checker.is_allowed("open_app") is False


def test_project_root_missing_raises_runtime_error(monkeypatch, tmp_path: Path) -> None:
    from core.security import permissions as perm_mod

    isolated = tmp_path / "nested" / "permissions.py"
    isolated.parent.mkdir(parents=True)
    monkeypatch.setattr(perm_mod, "__file__", str(isolated))
    with pytest.raises(RuntimeError, match="Could not locate project root"):
        perm_mod._project_root()
