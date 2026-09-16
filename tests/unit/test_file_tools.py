"""Unit tests for Phase 9 file system tools.

Tests cover:
- TestFileToolsSafeOps:          All 10 safe operations succeed for valid sandbox paths.
- TestFileToolsSandboxRejection: Every tool rejects traversal paths without I/O.
- TestFileToolsDestructiveGate:  delete_file / delete_folder require 'yes' confirmation.
- TestFileToolsOSErrors:         OS-level failures return ActionResult(recoverable=True).
- TestParserFileIntents:         CommandParser correctly extracts file intents (positional, Q1).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from core.security.path_guard import PathGuard


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def _make_adapter(ws: Path):
    """Return a platform-appropriate adapter with PathGuard bound to *ws*."""
    guard = PathGuard(workspace_root=ws)
    if sys.platform == "win32":
        from adapters.windows_adapter import WindowsAdapter
        adapter = WindowsAdapter()
    else:
        from adapters.linux_adapter import LinuxAdapter
        adapter = LinuxAdapter()
    # Override the guard with our test sandbox
    adapter._path_guard = guard
    return adapter


@pytest.fixture
def ws(tmp_path: Path) -> Path:
    """Isolated sandbox workspace for each test."""
    d = tmp_path / "workspace"
    d.mkdir()
    return d


@pytest.fixture
def adapter(ws: Path):
    return _make_adapter(ws)


# ---------------------------------------------------------------------------
# TestFileToolsSafeOps
# ---------------------------------------------------------------------------


class TestFileToolsSafeOps:
    """All safe file operations return ActionResult(success=True) for valid sandbox paths."""

    def test_create_file_empty(self, adapter, ws: Path) -> None:
        result = adapter.create_file("hello.txt")
        assert result.success is True
        assert "hello.txt" in result.message
        assert (ws / "hello.txt").exists()
        assert (ws / "hello.txt").read_text(encoding="utf-8") == ""

    def test_create_file_with_content(self, adapter, ws: Path) -> None:
        result = adapter.create_file("greet.txt", "Hello World")
        assert result.success is True
        assert (ws / "greet.txt").read_text(encoding="utf-8") == "Hello World"

    def test_create_file_creates_parent_dirs(self, adapter, ws: Path) -> None:
        result = adapter.create_file("a/b/c/deep.txt", "deep")
        assert result.success is True
        assert (ws / "a" / "b" / "c" / "deep.txt").exists()

    def test_read_file_returns_content(self, adapter, ws: Path) -> None:
        (ws / "readme.txt").write_text("docs here", encoding="utf-8")
        result = adapter.read_file("readme.txt")
        assert result.success is True
        assert "docs here" in result.message
        assert result.data is not None
        assert result.data["content"] == "docs here"

    def test_read_file_not_found(self, adapter) -> None:
        result = adapter.read_file("missing.txt")
        assert result.success is False
        assert result.recoverable is False

    def test_write_file_creates_and_overwrites(self, adapter, ws: Path) -> None:
        adapter.create_file("data.txt", "old")
        result = adapter.write_file("data.txt", "new content")
        assert result.success is True
        assert (ws / "data.txt").read_text(encoding="utf-8") == "new content"

    def test_append_file_adds_content(self, adapter, ws: Path) -> None:
        adapter.create_file("log.txt", "line1\n")
        result = adapter.append_file("log.txt", "line2\n")
        assert result.success is True
        assert (ws / "log.txt").read_text(encoding="utf-8") == "line1\nline2\n"

    def test_append_file_creates_if_missing(self, adapter, ws: Path) -> None:
        result = adapter.append_file("new_log.txt", "first line")
        assert result.success is True
        assert (ws / "new_log.txt").exists()

    def test_delete_file_removes_file(self, adapter, ws: Path) -> None:
        (ws / "temp.txt").write_text("x", encoding="utf-8")
        result = adapter.delete_file("temp.txt")
        assert result.success is True
        assert not (ws / "temp.txt").exists()

    def test_delete_file_not_found(self, adapter) -> None:
        result = adapter.delete_file("ghost.txt")
        assert result.success is False
        assert result.recoverable is False

    def test_copy_file_duplicates(self, adapter, ws: Path) -> None:
        (ws / "original.txt").write_text("data", encoding="utf-8")
        result = adapter.copy_file("original.txt", "copy.txt")
        assert result.success is True
        assert (ws / "copy.txt").exists()
        assert (ws / "original.txt").exists()
        assert (ws / "copy.txt").read_text(encoding="utf-8") == "data"

    def test_copy_file_source_not_found(self, adapter) -> None:
        result = adapter.copy_file("nonexistent.txt", "out.txt")
        assert result.success is False

    def test_move_file_renames(self, adapter, ws: Path) -> None:
        (ws / "before.txt").write_text("mv", encoding="utf-8")
        result = adapter.move_file("before.txt", "after.txt")
        assert result.success is True
        assert not (ws / "before.txt").exists()
        assert (ws / "after.txt").exists()

    def test_create_folder(self, adapter, ws: Path) -> None:
        result = adapter.create_folder("reports/2026")
        assert result.success is True
        assert (ws / "reports" / "2026").is_dir()

    def test_delete_folder_removes_tree(self, adapter, ws: Path) -> None:
        (ws / "old").mkdir()
        (ws / "old" / "file.txt").write_text("x", encoding="utf-8")
        result = adapter.delete_folder("old")
        assert result.success is True
        assert not (ws / "old").exists()

    def test_delete_folder_not_found(self, adapter) -> None:
        result = adapter.delete_folder("ghost_dir")
        assert result.success is False

    def test_move_folder_renames(self, adapter, ws: Path) -> None:
        (ws / "src_dir").mkdir()
        (ws / "src_dir" / "item.txt").write_text("hi", encoding="utf-8")
        result = adapter.move_folder("src_dir", "dst_dir")
        assert result.success is True
        assert not (ws / "src_dir").exists()
        assert (ws / "dst_dir").is_dir()

    def test_list_directory_returns_entries(self, adapter, ws: Path) -> None:
        (ws / "a.txt").write_text("", encoding="utf-8")
        (ws / "b.txt").write_text("", encoding="utf-8")
        (ws / "subdir").mkdir()
        result = adapter.list_directory(".")
        assert result.success is True
        assert result.data is not None
        assert "a.txt" in result.data["entries"]
        assert "b.txt" in result.data["entries"]
        assert "subdir" in result.data["entries"]

    def test_list_directory_empty(self, adapter) -> None:
        result = adapter.list_directory(".")
        assert result.success is True
        assert result.data["entries"] == []

    def test_list_directory_not_found(self, adapter) -> None:
        result = adapter.list_directory("nonexistent_dir")
        assert result.success is False

    def test_list_directory_not_a_directory(self, adapter, ws: Path) -> None:
        (ws / "file.txt").write_text("x", encoding="utf-8")
        result = adapter.list_directory("file.txt")
        assert result.success is False


# ---------------------------------------------------------------------------
# TestFileToolsSandboxRejection
# ---------------------------------------------------------------------------


class TestFileToolsSandboxRejection:
    """Every file tool must reject traversal/escape paths without touching the filesystem."""

    TRAVERSAL_PATHS = [
        "../escape.txt",
        "../../etc/passwd",
        "sub/../../outside.txt",
    ]

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_create_file_rejects_traversal(self, adapter, ws: Path, bad_path: str) -> None:
        result = adapter.create_file(bad_path, "evil")
        assert result.success is False
        assert result.recoverable is False
        # No file created outside workspace
        assert not any(ws.parent.glob("escape.txt"))
        assert not any(ws.parent.glob("outside.txt"))

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_read_file_rejects_traversal(self, adapter, bad_path: str) -> None:
        result = adapter.read_file(bad_path)
        assert result.success is False
        assert result.recoverable is False

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_write_file_rejects_traversal(self, adapter, bad_path: str) -> None:
        result = adapter.write_file(bad_path, "evil")
        assert result.success is False
        assert result.recoverable is False

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_delete_file_rejects_traversal(self, adapter, bad_path: str) -> None:
        result = adapter.delete_file(bad_path)
        assert result.success is False
        assert result.recoverable is False

    def test_copy_file_rejects_traversal_src(self, adapter, ws: Path) -> None:
        result = adapter.copy_file("../../outside.txt", "inside.txt")
        assert result.success is False
        assert result.recoverable is False

    def test_copy_file_rejects_traversal_dst(self, adapter, ws: Path) -> None:
        (ws / "real.txt").write_text("x", encoding="utf-8")
        result = adapter.copy_file("real.txt", "../../stolen.txt")
        assert result.success is False
        assert result.recoverable is False

    def test_move_file_rejects_traversal_dst(self, adapter, ws: Path) -> None:
        (ws / "real.txt").write_text("x", encoding="utf-8")
        result = adapter.move_file("real.txt", "../../exfil.txt")
        assert result.success is False
        assert result.recoverable is False

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_create_folder_rejects_traversal(self, adapter, bad_path: str) -> None:
        result = adapter.create_folder(bad_path)
        assert result.success is False
        assert result.recoverable is False

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_delete_folder_rejects_traversal(self, adapter, bad_path: str) -> None:
        result = adapter.delete_folder(bad_path)
        assert result.success is False
        assert result.recoverable is False

    @pytest.mark.parametrize("bad_path", TRAVERSAL_PATHS)
    def test_list_directory_rejects_traversal(self, adapter, bad_path: str) -> None:
        result = adapter.list_directory(bad_path)
        assert result.success is False
        assert result.recoverable is False


# ---------------------------------------------------------------------------
# TestFileToolsDestructiveGate
# ---------------------------------------------------------------------------


class TestFileToolsDestructiveGate:
    """delete_file and delete_folder must pass through IntentEngine confirmation gate."""

    def test_delete_file_requires_confirmation(self, ws: Path) -> None:
        """Engine must return a confirmation prompt; file must remain until 'yes'."""
        from helpers import MiniExecutor, write_permissions
        from engine import AssistantEngine
        from core.security.permissions import PermissionChecker

        perm_path = write_permissions(ws, {
            "delete_file": True, "confirm_yes": True, "confirm_no": True,
        }, filename="perm.json")
        exe = _make_adapter(ws)
        checker = PermissionChecker(config_path=perm_path)
        engine = AssistantEngine(system_executor=exe, permission_checker=checker)

        # Create a real file to delete
        (ws / "target.txt").write_text("data", encoding="utf-8")

        # First turn — should return confirmation prompt, NOT delete
        response = engine.handle("delete file target.txt")
        assert "yes" in response.lower() or "confirm" in response.lower() or "sure" in response.lower()
        assert (ws / "target.txt").exists(), "File must NOT be deleted until confirmed"

        # Second turn — confirm with yes
        response2 = engine.handle("yes")
        assert "deleted" in response2.lower() or "target.txt" in response2.lower()
        assert not (ws / "target.txt").exists(), "File must be deleted after confirmation"

    def test_delete_file_can_be_cancelled(self, ws: Path) -> None:
        """Replying 'no' to delete confirmation must leave the file intact."""
        from helpers import write_permissions
        from engine import AssistantEngine
        from core.security.permissions import PermissionChecker

        perm_path = write_permissions(ws, {
            "delete_file": True, "confirm_yes": True, "confirm_no": True,
        }, filename="perm.json")
        exe = _make_adapter(ws)
        checker = PermissionChecker(config_path=perm_path)
        engine = AssistantEngine(system_executor=exe, permission_checker=checker)

        (ws / "keep.txt").write_text("safe", encoding="utf-8")
        engine.handle("delete file keep.txt")
        response = engine.handle("no")
        assert "cancel" in response.lower()
        assert (ws / "keep.txt").exists()

    def test_delete_folder_requires_confirmation(self, ws: Path) -> None:
        """Same confirmation gate applies to delete_folder."""
        from helpers import write_permissions
        from engine import AssistantEngine
        from core.security.permissions import PermissionChecker

        perm_path = write_permissions(ws, {
            "delete_folder": True, "confirm_yes": True, "confirm_no": True,
        }, filename="perm.json")
        exe = _make_adapter(ws)
        checker = PermissionChecker(config_path=perm_path)
        engine = AssistantEngine(system_executor=exe, permission_checker=checker)

        folder = ws / "old_reports"
        folder.mkdir()
        (folder / "report.txt").write_text("x", encoding="utf-8")

        response = engine.handle("delete folder old_reports")
        assert "yes" in response.lower() or "sure" in response.lower()
        assert folder.exists(), "Folder must NOT be deleted until confirmed"

        engine.handle("yes")
        assert not folder.exists()


# ---------------------------------------------------------------------------
# TestFileToolsOSErrors
# ---------------------------------------------------------------------------


class TestFileToolsOSErrors:
    """OS-level failures must return ActionResult(success=False, recoverable=True)."""

    def test_create_file_os_error(self, adapter, ws: Path) -> None:
        with patch("pathlib.Path.write_text", side_effect=OSError("disk full")):
            result = adapter.create_file("fail.txt", "data")
        assert result.success is False
        assert result.recoverable is True

    def test_read_file_os_error(self, adapter, ws: Path) -> None:
        (ws / "exist.txt").write_text("x", encoding="utf-8")
        with patch("pathlib.Path.read_text", side_effect=OSError("perm denied")):
            result = adapter.read_file("exist.txt")
        assert result.success is False
        assert result.recoverable is True

    def test_write_file_os_error(self, adapter, ws: Path) -> None:
        with patch("pathlib.Path.write_text", side_effect=OSError("read-only fs")):
            result = adapter.write_file("fail.txt", "data")
        assert result.success is False
        assert result.recoverable is True

    def test_append_file_os_error(self, adapter, ws: Path) -> None:
        with patch("pathlib.Path.open", side_effect=OSError("no space")):
            result = adapter.append_file("fail.txt", "data")
        assert result.success is False
        assert result.recoverable is True


# ---------------------------------------------------------------------------
# TestParserFileIntents  (Q1 — positional extraction)
# ---------------------------------------------------------------------------


class TestParserFileIntents:
    """CommandParser correctly routes file intents and extracts path/content positionally."""

    @pytest.fixture(autouse=True)
    def _parser(self):
        from core.parser import CommandParser
        self.parser = CommandParser()

    def test_create_file_intent(self) -> None:
        intent = self.parser.parse("create file notes.txt")
        assert intent.intent == "create_file"
        assert intent.target == "notes.txt"

    def test_create_file_with_content(self) -> None:
        intent = self.parser.parse("create file notes.txt hello world")
        assert intent.intent == "create_file"
        assert intent.target == "notes.txt"
        assert intent.value == "hello world"

    def test_read_file_intent(self) -> None:
        intent = self.parser.parse("read file notes.txt")
        assert intent.intent == "read_file"
        assert intent.target == "notes.txt"

    def test_show_file_alias(self) -> None:
        intent = self.parser.parse("show file report.txt")
        assert intent.intent == "read_file"

    def test_write_to_intent(self) -> None:
        intent = self.parser.parse("write to notes.txt hello world")
        assert intent.intent == "write_file"
        assert intent.target == "notes.txt"
        assert intent.value == "hello world"

    def test_append_to_intent(self) -> None:
        intent = self.parser.parse("append to log.txt new line")
        assert intent.intent == "append_file"
        assert intent.target == "log.txt"
        assert intent.value == "new line"

    def test_delete_file_intent(self) -> None:
        intent = self.parser.parse("delete file old.txt")
        assert intent.intent == "delete_file"
        assert intent.target == "old.txt"

    def test_remove_file_alias(self) -> None:
        intent = self.parser.parse("remove file old.txt")
        assert intent.intent == "delete_file"

    def test_copy_file_intent(self) -> None:
        intent = self.parser.parse("copy file source.txt dest.txt")
        assert intent.intent == "copy_file"
        assert intent.target == "source.txt"
        assert intent.value == "dest.txt"

    def test_move_file_intent(self) -> None:
        intent = self.parser.parse("move file old.txt new.txt")
        assert intent.intent == "move_file"
        assert intent.target == "old.txt"
        assert intent.value == "new.txt"

    def test_create_folder_intent(self) -> None:
        intent = self.parser.parse("create folder reports")
        assert intent.intent == "create_folder"
        assert intent.target == "reports"

    def test_mkdir_alias(self) -> None:
        intent = self.parser.parse("mkdir docs")
        assert intent.intent == "create_folder"
        assert intent.target == "docs"

    def test_delete_folder_intent(self) -> None:
        intent = self.parser.parse("delete folder old")
        assert intent.intent == "delete_folder"
        assert intent.target == "old"

    def test_move_folder_intent(self) -> None:
        """Q2: move_folder must be a distinct intent (not move_file) for telemetry."""
        intent = self.parser.parse("move folder src dst")
        assert intent.intent == "move_folder"
        assert intent.target == "src"
        assert intent.value == "dst"

    def test_list_directory_intent(self) -> None:
        intent = self.parser.parse("list files")
        assert intent.intent == "list_directory"

    def test_ls_alias(self) -> None:
        intent = self.parser.parse("ls .")
        assert intent.intent == "list_directory"

    def test_dir_alias(self) -> None:
        intent = self.parser.parse("dir .")
        assert intent.intent == "list_directory"

    def test_bare_ls_defaults_to_root(self) -> None:
        intent = self.parser.parse("ls")
        assert intent.intent == "list_directory"
        assert intent.target == "."

    def test_bare_dir_defaults_to_root(self) -> None:
        intent = self.parser.parse("dir")
        assert intent.intent == "list_directory"
        assert intent.target == "."
