"""PathGuard: Three-Layer Sandbox and Path Containment Security Module.

Enforces strict containment of all file operations within a designated workspace sandbox.
Prevents directory traversal (CWE-22/23), DOS device locks (CWE-440), symlink escapes (CWE-59),
NTFS Alternate Data Streams, UNC path injection, and obfuscation bypasses.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# Repository and default paths
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DEFAULT_SETTINGS_PATH: Path = REPO_ROOT / "config" / "settings.json"
DEFAULT_WORKSPACE_ROOT: Path = REPO_ROOT / "workspace"

# Windows DOS device names (CWE-440)
_DOS_DEVICES: Final[set[str]] = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Regex for URL/percent-encoding and control characters
_URL_ENCODED_RE: Final[re.Pattern[str]] = re.compile(r"%[0-9a-fA-F]{2}")
_CONTROL_CHAR_RE: Final[re.Pattern[str]] = re.compile(r"[\x01-\x1f]")
_REPEATED_DOTS_RE: Final[re.Pattern[str]] = re.compile(r"\.{3,}")


class PathSecurityError(ValueError):
    """Raised when a path violates sandbox containment or security constraints."""


def _resolve_workspace_root_from_settings(config_path: Path | None = None) -> Path:
    """Safely reads and resolves the workspace_root from settings with graceful fallbacks."""
    target_config = config_path or DEFAULT_SETTINGS_PATH

    if target_config.is_file():
        try:
            content = target_config.read_text(encoding="utf-8").strip()
            if content:
                data = json.loads(content)
                if isinstance(data, dict) and "workspace_root" in data:
                    raw_root = data["workspace_root"]
                    if isinstance(raw_root, str) and raw_root.strip():
                        root_path = Path(raw_root.strip())
                        if not root_path.is_absolute():
                            root_path = REPO_ROOT / root_path
                        resolved = root_path.resolve()
                        resolved.mkdir(parents=True, exist_ok=True)
                        return resolved
        except Exception as exc:
            logger.warning(
                "Failed to parse workspace_root from settings '%s': %s. Falling back to default workspace.",
                target_config,
                exc,
            )

    fallback = DEFAULT_WORKSPACE_ROOT.resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


class PathGuard:
    """Guards file operations by enforcing canonical workspace sandbox containment."""

    def __init__(self, workspace_root: Path | str | None = None) -> None:
        if workspace_root is not None:
            ws = Path(workspace_root)
            if not ws.is_absolute():
                ws = REPO_ROOT / ws
            self.workspace_root: Path = ws.resolve()
            self.workspace_root.mkdir(parents=True, exist_ok=True)
        else:
            self.workspace_root = _resolve_workspace_root_from_settings(DEFAULT_SETTINGS_PATH)

    def is_safe(self, target_path: Path | str) -> bool:
        """Returns True if the path is safe and strictly within the workspace, False otherwise."""
        ok, _, _ = self.sanitize_path(target_path)
        return ok

    def sanitize_path(self, target_path: Path | str) -> tuple[bool, Path | None, str]:
        """Returns (is_safe, resolved_path, error_message)."""
        try:
            resolved = self.validate_path(target_path)
            return True, resolved, ""
        except PathSecurityError as err:
            return False, None, str(err)
        except Exception as exc:
            return False, None, f"Invalid path: {exc}"

    def to_workspace_relative(self, target_path: Path | str) -> Path:
        """Converts an absolute or relative path to a safe workspace-relative path.

        Protects host directory structure privacy from LLMs and planners.
        """
        resolved = self.validate_path(target_path)
        return resolved.relative_to(self.workspace_root)

    def validate_path(self, target_path: Path | str) -> Path:
        """Validates and resolves a path within the workspace sandbox.

        Raises:
            PathSecurityError: If any security constraints or boundary limits are breached.
        """
        if target_path is None:
            raise PathSecurityError("Path cannot be empty or None.")

        raw_str = str(target_path)
        if not raw_str.strip():
            raise PathSecurityError("Path cannot be empty.")

        # --- LAYER 1: Fast String & Threat Vector Inspection ---

        # 1. Null byte injection
        if "\0" in raw_str or "\x00" in raw_str:
            raise PathSecurityError("Path contains disallowed null byte.")

        # 2. Control characters & newlines
        if _CONTROL_CHAR_RE.search(raw_str):
            raise PathSecurityError("Path contains disallowed control characters.")

        # 3. URL/percent-encoded traversal obfuscation
        if _URL_ENCODED_RE.search(raw_str):
            raise PathSecurityError("Disallowed URL-encoded traversal characters detected.")

        # 4. UNC, network shares, and Win32 NT device namespaces
        if raw_str.startswith(("\\\\", "//", "\\??\\", "/??/")):
            raise PathSecurityError("UNC, network share, and NT device namespaces are disallowed.")

        # 5. Repeated dot traversal tricks (e.g. ....//)
        if _REPEATED_DOTS_RE.search(raw_str):
            raise PathSecurityError("Path traversal pattern disallowed: repeated dots outside boundary.")

        # 6. Drive letters, Alternate Data Streams (ADS), and colons
        has_drive = len(raw_str) >= 2 and raw_str[1] == ":" and raw_str[0].isalpha()
        if has_drive:
            # Check drive compatibility
            ws_drive = self.workspace_root.drive
            if not ws_drive or raw_str[0].upper() != ws_drive[0].upper():
                raise PathSecurityError(
                    f"Cross-drive reference '{raw_str[:2]}' is outside workspace boundary '{self.workspace_root}'."
                )
            # Drive-relative path check (e.g. C:foo.txt without slash)
            if len(raw_str) == 2 or raw_str[2] not in ("/", "\\"):
                raise PathSecurityError("Drive-relative paths outside workspace boundary are disallowed.")
            # Alternate data stream check on remaining path
            if ":" in raw_str[2:]:
                raise PathSecurityError("Alternate data stream (colon syntax) is invalid and disallowed.")
        else:
            if ":" in raw_str:
                raise PathSecurityError("Alternate data stream (colon syntax) is invalid and disallowed.")

        # 7. Path component inspection: DOS devices and trailing dots/spaces
        parts = [p for p in re.split(r"[/\\]+", raw_str) if p]
        for part in parts:
            # Trailing dots and spaces causing Win32 truncation/filter evasion
            if (part.endswith(".") and part not in (".", "..")) or part.endswith(" "):
                raise PathSecurityError(
                    f"Trailing dots or spaces in '{part}' are invalid and disallowed."
                )

            # DOS device names
            base = part.split(".")[0].strip().upper()
            if base in _DOS_DEVICES:
                raise PathSecurityError(f"Reserved DOS device name '{part}' is disallowed.")

        # --- LAYER 2: Canonical Resolution & Sandbox Containment ---

        # Normalize backslashes to forward slashes for cross-platform containment
        # (on POSIX, backslashes are not treated as directory separators by pathlib)
        normalized_str = raw_str.replace("\\", "/")
        candidate_path = Path(normalized_str)
        if candidate_path.is_absolute():
            if candidate_path.drive and self.workspace_root.drive:
                if candidate_path.drive.upper() != self.workspace_root.drive.upper():
                    raise PathSecurityError(
                        f"Path drive '{candidate_path.drive}' is outside workspace boundary."
                    )
            candidate = candidate_path
        else:
            candidate = self.workspace_root / candidate_path

        try:
            resolved = candidate.resolve(strict=False)
        except Exception as exc:
            raise PathSecurityError(f"Failed to resolve path '{raw_str}': {exc}") from exc

        # Check if resolved path is strictly within workspace_root
        try:
            is_contained = resolved.is_relative_to(self.workspace_root)
        except (ValueError, AttributeError):
            is_contained = False

        if not is_contained:
            raise PathSecurityError(
                f"Path traversal detected: '{raw_str}' resolves to '{resolved}' which is outside workspace boundary."
            )

        return resolved
