"""Phase 5 — session memory and rule-based follow-up resolution."""

import json
from pathlib import Path

from core.parser import CommandParser, Intent
from core.session_context import SessionManager
from engine import AssistantEngine
from core.security.permissions import PermissionChecker


def test_enrich_cpu_then_bare_bridge_to_memory() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    p = CommandParser()
    assert s.enrich("also", p.parse("also")).intent == "get_memory_usage"
    assert s.enrich("and?", p.parse("and?")).intent == "get_memory_usage"


def test_enrich_memory_then_bare_bridge_to_cpu() -> None:
    s = SessionManager()
    s.last_intent = "get_memory_usage"
    p = CommandParser()
    assert s.enrich("what else", p.parse("what else")).intent == "get_cpu_usage"


def test_enrich_time_then_bare_bridge_to_cpu() -> None:
    s = SessionManager()
    s.last_intent = "get_time"
    p = CommandParser()
    assert s.enrich("more", p.parse("more")).intent == "get_cpu_usage"


def test_enrich_metric_then_explicit_other_metric() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    p = CommandParser()
    # Parser alone would already resolve "ram" — still ensure session path is consistent
    assert s.enrich("tell me about ram", p.parse("tell me about ram")).intent == "get_memory_usage"


def test_enrich_cpu_session_resolves_memory_via_unknown_intent() -> None:
    """Session bridges when parser output is forced to unknown but text mentions memory."""
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    assert (
        s.enrich("talk about memory usage trends", Intent(intent="unknown")).intent
        == "get_memory_usage"
    )


def test_enrich_cpu_session_resolves_time_via_unknown_intent() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    assert s.enrich("sync the clock please", Intent(intent="unknown")).intent == "get_time"


def test_enrich_memory_session_resolves_cpu_via_unknown_intent() -> None:
    s = SessionManager()
    s.last_intent = "get_memory_usage"
    assert s.enrich("processor fan noise", Intent(intent="unknown")).intent == "get_cpu_usage"


def test_enrich_memory_session_resolves_time_via_unknown_intent() -> None:
    s = SessionManager()
    s.last_intent = "get_memory_usage"
    assert s.enrich("what time is dinner", Intent(intent="unknown")).intent == "get_time"


def test_enrich_time_session_resolves_memory_via_unknown_intent() -> None:
    s = SessionManager()
    s.last_intent = "get_time"
    assert s.enrich("check ram headroom", Intent(intent="unknown")).intent == "get_memory_usage"


def test_enrich_time_session_resolves_cpu_via_unknown_intent() -> None:
    s = SessionManager()
    s.last_intent = "get_time"
    assert s.enrich("cpu scheduling", Intent(intent="unknown")).intent == "get_cpu_usage"


def test_record_skips_confirmation_intents() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    s.record_successful_turn(Intent(intent="confirm_yes"), "Nothing to confirm.")
    assert s.last_intent == "get_cpu_usage"


def test_resolve_unknown_close_pronoun_when_parser_would_be_unknown() -> None:
    """After open_app, bare \"close it\" resolved via session (same as enrich unknown path)."""
    s = SessionManager()
    s.last_intent = "open_app"
    s.last_target = "notepad"
    out = s._resolve_unknown("close it")
    assert out == Intent(intent="close_app", target="notepad")


def test_resolve_unknown_reopen_after_close_via_session() -> None:
    s = SessionManager()
    s.last_intent = "close_app"
    s.last_target = "calc"
    out = s._resolve_unknown("launch it again")
    assert out == Intent(intent="open_app", target="calc")


def test_record_rejects_access_denied_response_string() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    s.record_successful_turn(Intent(intent="greet"), "Access denied for this action.")
    assert s.last_intent == "get_cpu_usage"


def test_record_skips_arbitrary_future_intent_not_modeled() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    s.record_successful_turn(Intent(intent="future_capability"), "done")
    assert s.last_intent == "get_cpu_usage"


def test_enrich_close_pronoun_after_open() -> None:
    s = SessionManager()
    s.last_intent = "open_app"
    s.last_target = "notepad"
    p = CommandParser()
    it = s.enrich("close it", p.parse("close it"))
    assert it.intent == "close_app"
    assert it.target == "notepad"


def test_enrich_reopen_after_open() -> None:
    s = SessionManager()
    s.last_intent = "open_app"
    s.last_target = "calc"
    it = s.enrich("launch it again", Intent(intent="unknown"))
    assert it.intent == "open_app"
    assert it.target == "calc"


def test_enrich_reopen_after_close() -> None:
    s = SessionManager()
    s.last_intent = "close_app"
    s.last_target = "notepad"
    it = s.enrich("open it again", Intent(intent="unknown"))
    assert it.intent == "open_app"
    assert it.target == "notepad"


def test_enrich_unknown_without_context_stays_unknown() -> None:
    s = SessionManager()
    p = CommandParser()
    assert s.enrich("mystery phrase", p.parse("mystery phrase")).intent == "unknown"


def test_record_skips_unknown_and_failed_handlers() -> None:
    s = SessionManager()
    s.last_intent = "get_cpu_usage"
    s.record_successful_turn(Intent(intent="unknown"), "Unknown intent")
    assert s.last_intent == "get_cpu_usage"

    s.record_successful_turn(Intent(intent="greet"), "No application specified.")
    assert s.last_intent == "get_cpu_usage"


def test_record_open_sets_target() -> None:
    s = SessionManager()
    s.record_successful_turn(Intent(intent="open_app", target="notepad"), "notepad opened.")
    assert s.last_intent == "open_app"
    assert s.last_target == "notepad"


def test_record_close_sets_target_for_reopen() -> None:
    s = SessionManager()
    s.record_successful_turn(Intent(intent="close_app", target="calc"), "calc closed.")
    assert s.last_intent == "close_app"
    assert s.last_target == "calc"


def test_clear_session() -> None:
    s = SessionManager()
    s.last_intent = "greet"
    s.last_target = "x"
    s.clear()
    assert s.last_intent is None
    assert s.last_target is None


def test_engine_follow_up_cpu_to_memory(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(
        json.dumps(
            {
                "get_cpu_usage": True,
                "get_memory_usage": True,
                "unknown": False,
            }
        ),
        encoding="utf-8",
    )

    class Ex:
        def open_app(self, app_name: str) -> str:
            return f"{app_name} opened."

        def close_app(self, app_name: str) -> str:
            return f"{app_name} closed."

        def close_file_explorer_windows(self):
            return {"status": "success", "action": "close_file_explorer_windows", "count": 0}

        def get_time(self) -> str:
            return "t"

        def get_cpu_usage(self) -> str:
            return "cpu-ok"

        def get_memory_usage(self) -> str:
            return "mem-ok"

    engine = AssistantEngine(
        system_executor=Ex(),
        permission_checker=PermissionChecker(config_path=p),
    )

    assert engine.handle("check cpu") == "cpu-ok"
    assert engine.handle("also") == "mem-ok"


def test_engine_access_denied_does_not_advance_session(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(json.dumps({"get_cpu_usage": True, "get_memory_usage": False}), encoding="utf-8")

    class Ex:
        def open_app(self, app_name: str) -> str:
            return f"{app_name} opened."

        def close_app(self, app_name: str) -> str:
            return f"{app_name} closed."

        def close_file_explorer_windows(self):
            return {"status": "success", "action": "x", "count": 0}

        def get_time(self) -> str:
            return "t"

        def get_cpu_usage(self) -> str:
            return "cpu-ok"

        def get_memory_usage(self) -> str:
            return "mem-ok"

    engine = AssistantEngine(
        system_executor=Ex(),
        permission_checker=PermissionChecker(config_path=p),
    )
    engine.handle("check cpu")
    out = engine.handle("also")
    assert out == "Access denied for this action."
    # Session should still be CPU so a permitted follow-up still works
    p2 = tmp_path / "perm2.json"
    p2.write_text(json.dumps({"get_cpu_usage": True, "get_memory_usage": True}), encoding="utf-8")
    engine.permissions = PermissionChecker(config_path=p2)
    assert engine.handle("also") == "mem-ok"


def test_engine_close_it_after_open(tmp_path: Path) -> None:
    p = tmp_path / "perm.json"
    p.write_text(
        json.dumps({"open_app": True, "close_app": True, "unknown": False}),
        encoding="utf-8",
    )

    class Ex:
        def __init__(self) -> None:
            self.closed: list[str] = []

        def open_app(self, app_name: str) -> str:
            return f"{app_name} opened."

        def close_app(self, app_name: str) -> str:
            self.closed.append(app_name)
            return f"{app_name} closed."

        def close_file_explorer_windows(self):
            return {"status": "success", "action": "x", "count": 0}

        def get_time(self) -> str:
            return "t"

        def get_cpu_usage(self) -> str:
            return "c"

        def get_memory_usage(self) -> str:
            return "m"

    ex = Ex()
    engine = AssistantEngine(
        system_executor=ex,
        permission_checker=PermissionChecker(config_path=p),
    )
    assert engine.handle("open notepad") == "notepad opened."
    assert engine.handle("close it") == "notepad closed."
    assert ex.closed == ["notepad"]
