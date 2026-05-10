"""
Rule-based session memory for follow-up utterances (Phase 5).
No background threads; state is updated after successful turns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.parser import CommandParser, Intent

_METRIC_CPU = frozenset({"get_cpu_usage", "check_cpu"})
_METRIC_MEM = frozenset({"get_memory_usage", "check_memory"})
_METRIC_TIME = frozenset({"get_time", "show_time"})
_METRICS = _METRIC_CPU | _METRIC_MEM | _METRIC_TIME

_PRONOUN_TARGETS = frozenset({"it", "that", "this"})

_REOPEN = re.compile(
    r"^(open|launch|start) (it|that)( again)?$",
    re.IGNORECASE,
)


def _norm(text: str) -> str:
    return text.strip().lower()


def _bare_bridge(text: str) -> bool:
    t = _norm(text).rstrip("?.!").strip()
    return t in {"and", "also", "what else", "how about that", "more"}


def _mentions_cpu(text: str) -> bool:
    n = _norm(text)
    return any(k in n for k in CommandParser.CPU_KEYWORDS)


def _mentions_memory(text: str) -> bool:
    n = _norm(text)
    return any(k in n for k in CommandParser.MEMORY_KEYWORDS)


def _mentions_time(text: str) -> bool:
    n = _norm(text)
    return any(k in n for k in CommandParser.TIME_KEYWORDS)


def _close_pronoun_phrase(text: str) -> bool:
    n = _norm(text)
    return bool(re.match(r"^close (it|that|this)( now)?$", n))


@dataclass
class SessionManager:
    """Tracks last successful intent (and optional app target) for contextual follow-ups."""

    last_intent: str | None = None
    last_target: str | None = None

    def clear(self) -> None:
        self.last_intent = None
        self.last_target = None

    def enrich(self, raw_text: str, parsed: Intent) -> Intent:
        """
        Refine parser output using session state (pronoun targets, unknown follow-ups).
        """
        text = _norm(raw_text)

        if parsed.intent == "close_app" and parsed.target:
            tgt = parsed.target.strip().lower()
            if tgt in _PRONOUN_TARGETS and self.last_intent == "open_app" and self.last_target:
                return Intent(intent="close_app", target=self.last_target)

        if parsed.intent == "unknown":
            resolved = self._resolve_unknown(text)
            if resolved is not None:
                return resolved

        return parsed

    def _resolve_unknown(self, text: str) -> Intent | None:
        last = self.last_intent

        if last in _METRIC_CPU:
            if _mentions_memory(text):
                return Intent(intent="get_memory_usage")
            if _mentions_time(text):
                return Intent(intent="get_time")
            if _bare_bridge(text):
                return Intent(intent="get_memory_usage")

        if last in _METRIC_MEM:
            if _mentions_cpu(text):
                return Intent(intent="get_cpu_usage")
            if _mentions_time(text):
                return Intent(intent="get_time")
            if _bare_bridge(text):
                return Intent(intent="get_cpu_usage")

        if last in _METRIC_TIME:
            if _mentions_memory(text):
                return Intent(intent="get_memory_usage")
            if _mentions_cpu(text):
                return Intent(intent="get_cpu_usage")
            if _bare_bridge(text):
                return Intent(intent="get_cpu_usage")

        if last == "open_app" and self.last_target:
            if _REOPEN.match(text.strip()):
                return Intent(intent="open_app", target=self.last_target)
            if _close_pronoun_phrase(text):
                return Intent(intent="close_app", target=self.last_target)

        if last == "close_app" and self.last_target and _REOPEN.match(text.strip()):
            return Intent(intent="open_app", target=self.last_target)

        return None

    def record_successful_turn(self, executed: Intent, response: str) -> None:
        """Persist context after a completed handler response."""
        if not self._should_record(executed, response):
            return

        self.last_intent = executed.intent

        if executed.intent == "open_app" and executed.target:
            self.last_target = executed.target.strip()
        elif executed.intent == "close_app" and executed.target:
            self.last_target = executed.target.strip()
        else:
            self.last_target = None

    @staticmethod
    def _should_record(executed: Intent, response: str) -> bool:
        if executed.intent == "unknown":
            return False
        if executed.intent in ("confirm_yes", "confirm_no"):
            return False

        no_context = (
            "Unknown intent",
            "Nothing to confirm.",
            "Action cancelled.",
            "No application specified.",
            "Internal processing error.",
        )
        if response in no_context:
            return False
        if response == "Access denied for this action.":
            return False

        if executed.intent in _METRICS | {"greet"}:
            return True
        if executed.intent == "open_app" and executed.target:
            return True
        if executed.intent == "close_app" and executed.target:
            return True

        return False
