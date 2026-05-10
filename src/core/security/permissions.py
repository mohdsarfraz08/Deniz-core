import json
from pathlib import Path
from typing import Any


def _project_root() -> Path:
    """Repository root (contains ``config/permissions.json``), works with ``src/`` layout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config" / "permissions.json").is_file():
            return parent
    raise RuntimeError("Could not locate project root (config/permissions.json missing).")


class PermissionChecker:
    """Loads per-intent flags from JSON. Missing keys default to deny (False)."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._path = config_path or (_project_root() / "config" / "permissions.json")
        self._permissions: dict[str, bool] = {}
        self._load()

    def _load(self) -> None:
        with open(self._path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        self._permissions = {
            k: bool(v) for k, v in data.items() if isinstance(v, bool)
        }

    def is_allowed(self, intent_name: str) -> bool:
        return self._permissions.get(intent_name, False)
