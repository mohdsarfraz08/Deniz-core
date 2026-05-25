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
_REOPEN_BARE = re.compile(
    r"^(open|launch|start) again$",
    re.IGNORECASE,
)
# Parser splits these from reopen phrases when session should supply last_target.
_REOPEN_LITERAL_TARGETS = frozenset(
    {"again", "it again", "that again", "this again"},
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

        # Reopen last app (parser may emit target "again", "it again", etc.)
        if self._is_reopen_phrase(text) and self.last_target and self.last_intent in (
            "open_app",
            "close_app",
        ):
            return Intent(intent="open_app", target=self.last_target)

        if parsed.intent == "open_app" and parsed.target:
            tgt = parsed.target.strip().lower()
            if (
                tgt in _PRONOUN_TARGETS or tgt in _REOPEN_LITERAL_TARGETS
            ) and self.last_target and self.last_intent in ("open_app", "close_app"):
                return Intent(intent="open_app", target=self.last_target)

        if parsed.intent == "close_app" and parsed.target:
            tgt = parsed.target.strip().lower()
            if tgt in _PRONOUN_TARGETS and self.last_intent == "open_app" and self.last_target:
                return Intent(intent="close_app", target=self.last_target)

        if parsed.intent == "unknown":
            resolved = self._resolve_unknown(text)
            if resolved is not None:
                return resolved

        return parsed

    @staticmethod
    def _is_reopen_phrase(text: str) -> bool:
        t = text.strip()
        return bool(_REOPEN.match(t) or _REOPEN_BARE.match(t))

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
            if self._is_reopen_phrase(text):
                return Intent(intent="open_app", target=self.last_target)
            if _close_pronoun_phrase(text):
                return Intent(intent="close_app", target=self.last_target)

        if last == "close_app" and self.last_target and self._is_reopen_phrase(text):
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
            return SessionManager._is_successful_open_response(response)
        if executed.intent == "close_app" and executed.target:
            return SessionManager._is_successful_close_response(response)

        return False

    @staticmethod
    def _is_successful_open_response(response: str) -> bool:
        """Do not record failed opens (e.g. target 'again') into session memory."""
        lower = response.lower()
        if lower.startswith("error opening"):
            return False
        if " opened." in lower or lower.endswith(" opened"):
            return True
        if lower.startswith("ignored duplicate terminal launch"):
            return True
        return False

    @staticmethod
    def _is_successful_close_response(response: str) -> bool:
        lower = response.lower()
        if lower.startswith("error") or lower.startswith("blocked:"):
            return False
        if "can't close" in lower or "cannot" in lower[:30]:
            return False
        if "closed" in lower or "no file explorer" in lower:
            return True
        if lower.startswith("cancelled"):
            return False
        return False
