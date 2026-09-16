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


# ---------------------------------------------------------------------------
# Phase 9 — IntentEngine file handler coverage
# Uses MiniExecutor stubs so no real filesystem I/O occurs.
# ---------------------------------------------------------------------------


def _file_engine(tmp_path: Path, mini_executor: MiniExecutor) -> AssistantEngine:
    """Return an engine with all Phase 9 file intents permitted."""
    perm = write_permissions(tmp_path, {
        "create_file": True,
        "read_file": True,
        "write_file": True,
        "append_file": True,
        "delete_file": True,
        "copy_file": True,
        "move_file": True,
        "create_folder": True,
        "delete_folder": True,
        "move_folder": True,
        "list_directory": True,
        "confirm_yes": True,
        "confirm_no": True,
    })
    return AssistantEngine(
        system_executor=mini_executor,
        permission_checker=PermissionChecker(config_path=perm),
    )


def test_engine_create_file(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("create file notes.txt")
    assert "notes.txt" in out


def test_engine_read_file(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("read file notes.txt")
    assert "notes.txt" in out


def test_engine_write_file(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("write to notes.txt hello")
    assert "written" in out.lower() or "notes.txt" in out


def test_engine_append_file(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("append to notes.txt more")
    assert "append" in out.lower() or "notes.txt" in out


def test_engine_delete_file_requires_confirmation(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("delete file notes.txt")
    # Must return confirmation prompt, NOT execute immediately
    assert "yes" in out.lower() or "sure" in out.lower() or "confirm" in out.lower()


def test_engine_delete_file_confirmed(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    eng.handle("delete file notes.txt")
    out = eng.handle("yes")
    assert "deleted" in out.lower() or "notes.txt" in out


def test_engine_delete_file_cancelled(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    eng.handle("delete file notes.txt")
    out = eng.handle("no")
    assert "cancel" in out.lower()


def test_engine_copy_file(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("copy file a.txt b.txt")
    assert "copied" in out.lower() or "a.txt" in out


def test_engine_move_file(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("move file a.txt b.txt")
    assert "moved" in out.lower() or "a.txt" in out


def test_engine_create_folder(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("create folder reports")
    assert "reports" in out


def test_engine_delete_folder_requires_confirmation(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("delete folder reports")
    assert "yes" in out.lower() or "sure" in out.lower() or "confirm" in out.lower()


def test_engine_delete_folder_confirmed(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    eng.handle("delete folder reports")
    out = eng.handle("yes")
    assert "deleted" in out.lower() or "reports" in out


def test_engine_move_folder(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("move folder src dst")
    assert "moved" in out.lower() or "src" in out


def test_engine_list_directory(tmp_path, mini_executor) -> None:
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("list files")
    assert "contents" in out.lower() or "workspace" in out.lower()


def test_engine_create_file_no_target(tmp_path, mini_executor) -> None:
    """Bare 'create file' has no path so parser emits unknown; engine responds accordingly."""
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("create file")
    # Parser cannot extract a path from bare keyword — falls through to unknown intent
    assert out  # engine returns a non-empty response


def test_engine_read_file_no_target(tmp_path, mini_executor) -> None:
    """Bare 'read file' has no path so parser emits unknown; engine responds accordingly."""
    eng = _file_engine(tmp_path, mini_executor)
    out = eng.handle("read file")
    # Parser cannot extract a path from bare keyword — falls through to unknown intent
    assert out  # engine returns a non-empty response
