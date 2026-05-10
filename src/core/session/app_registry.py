"""
Assistant-opened application sessions (PID-backed, cleaned when processes exit).

Not a global: inject one ``SessionRegistry`` per engine / adapter graph.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

import psutil

Category = Literal["terminal"]
SessionSource = Literal["assistant_launch"]


@dataclass
class AppSessionEntry:
    pid: int
    process_name: str
    launch_method: str
    launch_canonical: str
    opened_at: float = field(default_factory=lambda: time.monotonic())
    window_title: str | None = None
    """Highest-confidence closes: only sessions we spawned and recorded."""
    source: SessionSource = "assistant_launch"


class SessionRegistry:
    """
    Tracks assistant-launched apps by category. Terminals use a list (most recent last).

    ``recent_actions`` holds short human-readable log lines for debugging / future UX.
    """

    def __init__(self) -> None:
        self._opened_apps: dict[str, list[AppSessionEntry]] = {}
        self.recent_actions: list[str] = []

    def register_app(
        self,
        *,
        category: Category | str,
        pid: int,
        process_name: str,
        launch_method: str,
        launch_canonical: str,
        window_title: str | None = None,
        source: SessionSource = "assistant_launch",
    ) -> AppSessionEntry:
        self.cleanup_dead_processes(category)
        entry = AppSessionEntry(
            pid=pid,
            process_name=process_name,
            launch_method=launch_method,
            launch_canonical=launch_canonical,
            window_title=window_title,
            source=source,
        )
        self._opened_apps.setdefault(category, []).append(entry)
        self.recent_actions.append(
            f"register {category} pid={pid} ({process_name}) via {launch_method}"
        )
        return entry

    def get_last_app(self, category: str) -> AppSessionEntry | None:
        """Most recently registered alive session in category, or None."""
        self.cleanup_dead_processes(category)
        lst = self._opened_apps.get(category)
        if not lst:
            return None
        for e in reversed(lst):
            if psutil.pid_exists(e.pid):
                return e
        return None

    def remove_app(self, category: str, pid: int) -> bool:
        lst = self._opened_apps.get(category)
        if not lst:
            return False
        for i, e in enumerate(lst):
            if e.pid == pid:
                lst.pop(i)
                self.recent_actions.append(f"remove {category} pid={pid}")
                return True
        return False

    def cleanup_dead_processes(self, category: str | None = None) -> None:
        """Drop registry entries whose PIDs are gone."""
        cats = [category] if category is not None else list(self._opened_apps.keys())
        for cat in cats:
            lst = self._opened_apps.get(cat)
            if not lst:
                continue
            alive: list[AppSessionEntry] = []
            for e in lst:
                if psutil.pid_exists(e.pid):
                    alive.append(e)
                else:
                    self.recent_actions.append(f"cleanup stale {cat} pid={e.pid}")
            self._opened_apps[cat] = alive

    def pop_close_candidate(self, request_key: str) -> AppSessionEntry | None:
        """
        Remove and return the best assistant-managed terminal to close for this phrase.

        ``request_key``: powershell | pwsh | cmd | terminal
        """
        self.cleanup_dead_processes("terminal")
        lst = self._opened_apps.get("terminal")
        if not lst:
            return None

        def pop_first_matching(predicate) -> AppSessionEntry | None:
            for i in range(len(lst) - 1, -1, -1):
                e = lst[i]
                if not psutil.pid_exists(e.pid):
                    continue
                if predicate(e):
                    return lst.pop(i)
            return None

        if request_key == "terminal":
            return pop_first_matching(lambda _e: True)

        if request_key == "powershell":
            e = pop_first_matching(
                lambda x: x.launch_canonical in ("powershell", "pwsh")
            )
            if e is not None:
                return e
            return pop_first_matching(lambda x: x.launch_canonical == "terminal")

        if request_key == "pwsh":
            e = pop_first_matching(lambda x: x.launch_canonical == "pwsh")
            if e is not None:
                return e
            return pop_first_matching(
                lambda x: x.launch_canonical in ("powershell", "terminal")
            )

        if request_key == "cmd":
            return pop_first_matching(lambda x: x.launch_canonical == "cmd")

        return None

    def count_category(self, category: str) -> int:
        self.cleanup_dead_processes(category)
        return len(self._opened_apps.get(category, []))

    def list_alive_terminal_entries(self) -> list[AppSessionEntry]:
        """All alive assistant-tracked terminal sessions (for UX enrichment, not mass close)."""
        self.cleanup_dead_processes("terminal")
        lst = self._opened_apps.get("terminal")
        if not lst:
            return []
        return [e for e in lst if psutil.pid_exists(e.pid)]
