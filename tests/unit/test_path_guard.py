"""Unit test battery for PathGuard (Phase 9.1: Test-Driven Security).

Aggressively tests sandboxing, path traversal, DOS devices, symlink escapes,
alternate data streams, UNC paths, encoding bypasses, and cross-platform edge cases.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from core.security.path_guard import PathGuard, PathSecurityError


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """Fixture providing an isolated workspace sandbox for testing."""
    ws = tmp_path / "sandbox_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@pytest.fixture
def guard(workspace_dir: Path) -> PathGuard:
    """Fixture providing a PathGuard instance bound to the isolated workspace sandbox."""
    return PathGuard(workspace_root=workspace_dir)


class TestDirectoryTraversal:
    """Tests mitigating directory traversal attacks (CWE-22 / CWE-23).

    Ensures relative navigation patterns ('..', mixed slashes, redundant segments)
    cannot escape the designated workspace sandbox root.
    """

    @pytest.mark.parametrize(
        "escape_path",
        [
            "../secret.txt",
            "../../secret.txt",
            "../../../etc/passwd",
            "....//....//secret.txt",
            "foo/../../secret.txt",
            "foo/bar/../../../outside.txt",
            "foo/bar/../../../../Windows/System32/cmd.exe",
            "./../escape.txt",
            "sub/./../../escape.txt",
        ],
    )
    def test_relative_parent_traversals_rejected(self, guard: PathGuard, escape_path: str) -> None:
        """Any relative path attempting to navigate above the workspace root must raise PathSecurityError."""
        assert guard.is_safe(escape_path) is False
        with pytest.raises(PathSecurityError, match="traversal|outside|boundary"):
            guard.validate_path(escape_path)

    @pytest.mark.parametrize(
        "mixed_slash_path",
        [
            "foo/..\\../secret.txt",
            "foo\\..\\../secret.txt",
            "sub\\..\\..\\..\\outside.txt",
            "..\\../escape.txt",
            "..\\..\\Windows\\System32",
        ],
    )
    def test_mixed_and_backslash_traversals_rejected(self, guard: PathGuard, mixed_slash_path: str) -> None:
        """Mixed forward/backward slash traversal sequences must be normalized and rejected."""
        assert guard.is_safe(mixed_slash_path) is False
        with pytest.raises(PathSecurityError, match="traversal|outside|boundary"):
            guard.validate_path(mixed_slash_path)

    def test_root_and_parent_boundary_rejected(self, guard: PathGuard) -> None:
        """Direct boundary specifiers targeting the parent directory must be rejected."""
        assert guard.is_safe("..") is False
        with pytest.raises(PathSecurityError):
            guard.validate_path("..")

    def test_nonexistent_ancestor_traversal_rejected(self, guard: PathGuard) -> None:
        """Traversal attempts traversing nonexistent subpaths back out must be caught by strict=False resolution."""
        nonexistent_escape = "nonexistent_dir/sub/../../../../escaped_target.txt"
        assert guard.is_safe(nonexistent_escape) is False
        with pytest.raises(PathSecurityError):
            guard.validate_path(nonexistent_escape)


class TestDOSDeviceNames:
    """Tests mitigating Windows DOS Device Name vulnerabilities (CWE-440 / MS-DOS legacy).

    On Windows, files named CON, PRN, AUX, NUL, COM1-COM9, or LPT1-LPT9 (with or without
    extensions) can freeze the process, trigger kernel timeouts, or cause system faults.
    """

    DOS_DEVICES = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]

    @pytest.mark.parametrize("device", DOS_DEVICES)
    def test_bare_dos_devices_rejected(self, guard: PathGuard, device: str) -> None:
        """Bare reserved DOS device names must be rejected."""
        assert guard.is_safe(device) is False
        with pytest.raises(PathSecurityError, match="reserved|device"):
            guard.validate_path(device)

    @pytest.mark.parametrize("device", ["nul", "NuL", "cOm1", "CoM9", "pRn", "AuX"])
    def test_dos_devices_case_insensitive_rejected(self, guard: PathGuard, device: str) -> None:
        """DOS device detection must be case-insensitive."""
        assert guard.is_safe(device) is False
        with pytest.raises(PathSecurityError, match="reserved|device"):
            guard.validate_path(device)

    @pytest.mark.parametrize("device", ["NUL.txt", "con.json", "aux.py", "com1.log", "prn.dat"])
    def test_dos_devices_with_extensions_rejected(self, guard: PathGuard, device: str) -> None:
        """DOS devices appended with arbitrary extensions remain reserved and must be rejected."""
        assert guard.is_safe(device) is False
        with pytest.raises(PathSecurityError, match="reserved|device"):
            guard.validate_path(device)

    @pytest.mark.parametrize("device", ["subdir/nul", "a/b/c/prn.txt", "workspace_child\\COM1"])
    def test_nested_dos_devices_rejected(self, guard: PathGuard, device: str) -> None:
        """DOS devices placed inside subdirectories must be rejected."""
        assert guard.is_safe(device) is False
        with pytest.raises(PathSecurityError, match="reserved|device"):
            guard.validate_path(device)


class TestAlternateDataStreams:
    """Tests mitigating NTFS Alternate Data Stream (ADS) attacks.

    On NTFS, appending a colon allows referencing hidden data streams (e.g., 'file.txt:hidden').
    This can be used to bypass file extension filters or store stealth data.
    """

    @pytest.mark.parametrize(
        "ads_path",
        [
            "file.txt:hidden",
            "file.txt:stream:$DATA",
            "nested/file.txt:hidden",
            "file.txt:",
            "sub:stream/file.txt",
        ],
    )
    def test_alternate_data_streams_rejected(self, guard: PathGuard, ads_path: str) -> None:
        """Any path containing an unescaped colon outside a drive letter specifier must be blocked."""
        assert guard.is_safe(ads_path) is False
        with pytest.raises(PathSecurityError, match="alternate data stream|colon|invalid"):
            guard.validate_path(ads_path)


class TestUNCAndDeviceNamespaces:
    """Tests mitigating Windows NT and UNC Namespace Injections.

    Rejects paths targeting network shares (\\\\server\\share) or Win32 NT namespaces (\\\\?\\, \\\\.\\).
    """

    @pytest.mark.parametrize(
        "unc_path",
        [
            r"\\server\share\file.txt",
            r"\\localhost\c$\Windows\System32",
            r"\\?\C:\Windows\System32",
            r"\\.\COM1",
            r"\\?\Volume{b75e2c83-0000-0000-0000-602200000000}\file.txt",
            "//server/share/file.txt",
            "//localhost/c$/test",
        ],
    )
    def test_unc_and_nt_namespaces_rejected(self, guard: PathGuard, unc_path: str) -> None:
        """UNC paths, network admin shares, and raw NT device namespaces must be rejected."""
        assert guard.is_safe(unc_path) is False
        with pytest.raises(PathSecurityError, match="unc|device|namespace|network"):
            guard.validate_path(unc_path)


class TestCrossDriveAndAbsolutePaths:
    """Tests mitigating absolute path and cross-drive escapes.

    Verifies that absolute system paths and cross-volume specifications cannot
    escape the sandbox boundary.
    """

    def test_absolute_system_paths_rejected(self, guard: PathGuard) -> None:
        """Absolute system paths outside the workspace must be rejected."""
        target = r"C:\Windows\System32\calc.exe" if sys.platform == "win32" else "/etc/shadow"
        assert guard.is_safe(target) is False
        with pytest.raises(PathSecurityError, match="outside|boundary"):
            guard.validate_path(target)

    def test_arbitrary_temp_outside_sandbox_rejected(self, guard: PathGuard, tmp_path: Path) -> None:
        """An absolute path to an external directory created outside the sandbox must be rejected."""
        outside_file = tmp_path / "outside_dir" / "secret.txt"
        outside_file.parent.mkdir(parents=True, exist_ok=True)
        outside_file.touch()

        assert guard.is_safe(str(outside_file)) is False
        with pytest.raises(PathSecurityError, match="outside|boundary"):
            guard.validate_path(str(outside_file))

    def test_cross_drive_reference_rejected(self, guard: PathGuard) -> None:
        """On Windows or mock setups, referencing an alternate drive letter must be rejected."""
        # Drive Z: is guaranteed different from any active workspace drive
        cross_drive = r"Z:\untrusted\exploit.txt"
        assert guard.is_safe(cross_drive) is False
        with pytest.raises(PathSecurityError):
            guard.validate_path(cross_drive)

    def test_drive_relative_path_rejected(self, guard: PathGuard) -> None:
        """Drive-relative syntax (e.g., 'C:foo.txt') must be rejected or securely resolved."""
        drive_relative = "Z:foo.txt"
        assert guard.is_safe(drive_relative) is False
        with pytest.raises(PathSecurityError):
            guard.validate_path(drive_relative)


class TestEncodingAndObfuscation:
    """Tests mitigating URL encoding and character-obfuscation bypasses (CWE-173 / CWE-177).

    Ensures percent-encoded traversals, double-encoded strings, and null bytes are rejected.
    """

    @pytest.mark.parametrize(
        "encoded_path",
        [
            "%2e%2e%2fsecret.txt",
            "..%2fsecret.txt",
            "%2e%2e/secret.txt",
            "%252e%252e%252fsecret.txt",
            "..%5csecret.txt",
            "%2e%2e%5csecret.txt",
        ],
    )
    def test_url_encoded_traversal_rejected(self, guard: PathGuard, encoded_path: str) -> None:
        """Percent-encoded or double-encoded path traversal sequences must be rejected."""
        assert guard.is_safe(encoded_path) is False
        with pytest.raises(PathSecurityError, match="encoded|invalid|traversal"):
            guard.validate_path(encoded_path)

    @pytest.mark.parametrize(
        "null_byte_path",
        [
            "file.txt\0.png",
            "\0../secret.txt",
            "valid_name.txt\x00extra",
        ],
    )
    def test_null_byte_injection_rejected(self, guard: PathGuard, null_byte_path: str) -> None:
        """Null bytes (\\0) must be rejected immediately without causing unhandled interpreter exceptions."""
        assert guard.is_safe(null_byte_path) is False
        with pytest.raises(PathSecurityError, match="null byte|invalid"):
            guard.validate_path(null_byte_path)

    @pytest.mark.parametrize(
        "control_char_path",
        [
            "file\nname.txt",
            "file\rname.txt",
            "file\x01test.txt",
            "sub\x1fname/test.txt",
        ],
    )
    def test_control_characters_rejected(self, guard: PathGuard, control_char_path: str) -> None:
        """ASCII control characters and newlines must be rejected."""
        assert guard.is_safe(control_char_path) is False
        with pytest.raises(PathSecurityError, match="control character|invalid"):
            guard.validate_path(control_char_path)


class TestSymlinkEscapes:
    """Tests mitigating symlink/reparse point breakout vulnerabilities (CWE-59).

    Ensures that symbolic links inside the sandbox pointing to targets outside
    the sandbox cannot be dereferenced to leak or modify external host files.
    """

    def test_symlink_pointing_outside_workspace_rejected(
        self, guard: PathGuard, workspace_dir: Path, tmp_path: Path
    ) -> None:
        """A symlink located inside the workspace targeting an external file must be rejected."""
        external_dir = tmp_path / "external_target"
        external_dir.mkdir(parents=True, exist_ok=True)
        external_file = external_dir / "confidential.txt"
        external_file.write_text("classified", encoding="utf-8")

        evil_symlink = workspace_dir / "evil_link"
        try:
            evil_symlink.symlink_to(external_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not permitted or supported on this host.")

        # Attempting to access confidential.txt through the internal symlink
        attempt = "evil_link/confidential.txt"
        assert guard.is_safe(attempt) is False
        with pytest.raises(PathSecurityError, match="symlink|outside|boundary"):
            guard.validate_path(attempt)

    def test_symlink_inside_workspace_allowed(self, guard: PathGuard, workspace_dir: Path) -> None:
        """A symlink located inside the workspace targeting another path inside the workspace is permitted."""
        internal_target = workspace_dir / "real_dir"
        internal_target.mkdir(parents=True, exist_ok=True)
        valid_file = internal_target / "hello.txt"
        valid_file.write_text("ok", encoding="utf-8")

        safe_symlink = workspace_dir / "safe_link"
        try:
            safe_symlink.symlink_to(internal_target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("Symlink creation not permitted or supported on this host.")

        result = guard.validate_path("safe_link/hello.txt")
        assert result.resolve() == valid_file.resolve()


class TestWindowsSpecificTruncation:
    """Tests mitigating Windows trailing dot and space truncation anomalies.

    Windows automatically strips trailing dots and spaces, which can lead to
    path aliasing or extension filter evasion (e.g., 'file.txt.' -> 'file.txt').
    """

    @pytest.mark.parametrize(
        "truncated_path",
        [
            "file.txt.",
            "file.txt..",
            "file.txt ",
            "dir. /file.txt",
        ],
    )
    def test_trailing_dots_and_spaces_rejected(self, guard: PathGuard, truncated_path: str) -> None:
        """Trailing dots and spaces that trigger Win32 path truncation anomalies must be blocked."""
        assert guard.is_safe(truncated_path) is False
        with pytest.raises(PathSecurityError, match="trailing|dot|space|invalid"):
            guard.validate_path(truncated_path)


class TestValidWorkspacePaths:
    """Tests confirming valid, legitimate workspace file access works smoothly."""

    def test_simple_relative_file_accepted(self, guard: PathGuard, workspace_dir: Path) -> None:
        """Simple relative filenames inside workspace must resolve accurately."""
        resolved = guard.validate_path("notes.txt")
        assert resolved == (workspace_dir / "notes.txt").resolve()
        assert guard.is_safe("notes.txt") is True

    def test_nested_relative_file_accepted(self, guard: PathGuard, workspace_dir: Path) -> None:
        """Nested subdirectories inside workspace must resolve accurately."""
        resolved = guard.validate_path("reports/2026/audit.json")
        assert resolved == (workspace_dir / "reports" / "2026" / "audit.json").resolve()
        assert guard.is_safe("reports/2026/audit.json") is True

    def test_absolute_path_within_workspace_accepted(self, guard: PathGuard, workspace_dir: Path) -> None:
        """An absolute path pointing directly into the workspace must be accepted."""
        inside_abs = workspace_dir / "config" / "app.json"
        resolved = guard.validate_path(str(inside_abs))
        assert resolved == inside_abs.resolve()
        assert guard.is_safe(str(inside_abs)) is True

    def test_nonexistent_leaf_file_for_creation_accepted(self, guard: PathGuard, workspace_dir: Path) -> None:
        """Files that do not exist yet (e.g. for create_file) must be validated safely."""
        new_file = "new_folder/created_file.txt"
        resolved = guard.validate_path(new_file)
        assert resolved == (workspace_dir / "new_folder" / "created_file.txt").resolve()

    def test_to_workspace_relative_guarantees_data_privacy(self, guard: PathGuard, workspace_dir: Path) -> None:
        """to_workspace_relative must strip host directory prefixes so LLMs never see host paths."""
        abs_path = workspace_dir / "reports" / "weekly.txt"
        rel_path = guard.to_workspace_relative(abs_path)
        assert rel_path == Path("reports/weekly.txt")
        assert not str(rel_path).startswith(str(workspace_dir))

    def test_sanitize_path_helper_contract(self, guard: PathGuard, workspace_dir: Path) -> None:
        """sanitize_path must return a structured (is_safe, resolved_path, message) tuple."""
        # Safe case
        ok, res, msg = guard.sanitize_path("data.csv")
        assert ok is True
        assert res == (workspace_dir / "data.csv").resolve()
        assert msg == ""

        # Unsafe case
        ok_bad, res_bad, msg_bad = guard.sanitize_path("../../etc/shadow")
        assert ok_bad is False
        assert res_bad is None
        assert len(msg_bad) > 0


class TestSettingsFallbackAndConfiguration:
    """Tests verifying config/settings.json parsing, error handling, and graceful degradation."""

    def test_custom_workspace_root_instantiation(self, tmp_path: Path) -> None:
        """PathGuard correctly binds to an explicitly provided root directory."""
        custom_root = tmp_path / "custom_dir"
        custom_root.mkdir()
        guard = PathGuard(workspace_root=custom_root)
        assert guard.workspace_root == custom_root.resolve()

    def test_missing_settings_file_graceful_fallback(self, tmp_path: Path) -> None:
        """When settings.json is missing, PathGuard falls back safely to default workspace root."""
        nonexistent_config = tmp_path / "missing_settings.json"
        with patch("core.security.path_guard.DEFAULT_SETTINGS_PATH", nonexistent_config):
            guard = PathGuard()
            assert guard.workspace_root is not None
            assert guard.workspace_root.is_dir()

    def test_empty_settings_file_graceful_fallback(self, tmp_path: Path) -> None:
        """When settings.json is 0 bytes, PathGuard logs a warning and uses safe fallback."""
        empty_config = tmp_path / "empty_settings.json"
        empty_config.touch()
        with patch("core.security.path_guard.DEFAULT_SETTINGS_PATH", empty_config):
            guard = PathGuard()
            assert guard.workspace_root is not None
            assert guard.workspace_root.is_dir()

    def test_corrupted_json_settings_graceful_fallback(self, tmp_path: Path) -> None:
        """When settings.json has corrupt JSON syntax, PathGuard catches it and falls back safely."""
        corrupt_config = tmp_path / "corrupt_settings.json"
        corrupt_config.write_text("{invalid_json: true,", encoding="utf-8")
        with patch("core.security.path_guard.DEFAULT_SETTINGS_PATH", corrupt_config):
            guard = PathGuard()
            assert guard.workspace_root is not None
            assert guard.workspace_root.is_dir()

    def test_relative_workspace_root_in_settings_anchors_to_project_root(self, tmp_path: Path) -> None:
        """A relative path specified in settings.json must resolve relative to project root, not cwd."""
        config_file = tmp_path / "settings.json"
        config_file.write_text('{"workspace_root": "sandbox"}', encoding="utf-8")
        with patch("core.security.path_guard.DEFAULT_SETTINGS_PATH", config_file):
            guard = PathGuard()
            assert guard.workspace_root.name == "sandbox"
            assert guard.workspace_root.is_absolute()
