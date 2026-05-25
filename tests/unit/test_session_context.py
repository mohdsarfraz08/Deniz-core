"""Phase 5 — session memory and rule-based follow-up resolution."""

import json
from pathlib import Path

from core.parser import CommandParser, Intent
from core.session_context import SessionManager
from engine import AssistantEngine
from core.security.permissions import PermissionChecker
from helpers import write_permissions


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


def test_record_skips_failed_open_so_reopen_stays_valid() -> None:
    """Failed \"open again\" must not set last_target to \"again\"."""
    s = SessionManager()
    s.record_successful_turn(Intent(intent="close_app", target="notepad"), "notepad.exe closed successfully.")
    s.record_successful_turn(
        Intent(intent="open_app", target="again"),
        "Error opening again: [WinError 2] not found",
    )
    assert s.last_target == "notepad"
    p = CommandParser()
    it = s.enrich("open it again", p.parse("open it again"))
    assert it.target == "notepad"


def test_enrich_open_again_after_close() -> None:
    s = SessionManager()
    s.last_intent = "close_app"
    s.last_target = "notepad"
    p = CommandParser()
    it = s.enrich("open again", p.parse("open again"))
    assert it.intent == "open_app"
    assert it.target == "notepad"


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


def test_enrich_reopen_when_parser_emits_open_it_again_target() -> None:
    """Regression: parser maps \"open it again\" to target \"it again\", not unknown."""
    s = SessionManager()
    s.last_intent = "close_app"
    s.last_target = "notepad"
    p = CommandParser()
    it = s.enrich("open it again", p.parse("open it again"))
    assert it.intent == "open_app"
    assert it.target == "notepad"


def test_enrich_open_pronoun_after_close() -> None:
    s = SessionManager()
    s.last_intent = "close_app"
    s.last_target = "notepad"
    p = CommandParser()
    it = s.enrich("open it", p.parse("open it"))
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


def test_engine_follow_up_cpu_to_memory(
    assistant_engine_factory,
    session_test_executor,
) -> None:
    engine = assistant_engine_factory(
        {"get_cpu_usage": True, "get_memory_usage": True, "unknown": False},
        executor=session_test_executor,
    )
    assert engine.handle("check cpu") == "cpu-ok"
    assert engine.handle("also") == "mem-ok"


def test_engine_access_denied_does_not_advance_session(
    tmp_path: Path,
    assistant_engine_factory,
    session_test_executor,
) -> None:
    engine = assistant_engine_factory(
        {"get_cpu_usage": True, "get_memory_usage": False},
        executor=session_test_executor,
    )
    engine.handle("check cpu")
    out = engine.handle("also")
    assert out == "Access denied for this action."
    p2 = write_permissions(
        tmp_path,
        {"get_cpu_usage": True, "get_memory_usage": True},
        filename="perm2.json",
    )
    engine.permissions = PermissionChecker(config_path=p2)
    assert engine.handle("also") == "mem-ok"


def test_engine_close_it_after_open(
    assistant_engine_factory,
    tracking_mini_executor,
) -> None:
    engine = assistant_engine_factory(
        {"open_app": True, "close_app": True, "unknown": False},
        executor=tracking_mini_executor,
    )
    assert engine.handle("open notepad") == "notepad opened."
    assert engine.handle("close it") == "notepad closed."
    assert tracking_mini_executor.closed == ["notepad"]


def test_engine_reopen_it_again_after_close(
    assistant_engine_factory,
    tracking_mini_executor,
) -> None:
    engine = assistant_engine_factory(
        {"open_app": True, "close_app": True, "unknown": False},
        executor=tracking_mini_executor,
    )
    assert engine.handle("open notepad") == "notepad opened."
    assert engine.handle("close notepad") == "notepad closed."
    assert engine.handle("open it again") == "notepad opened."


def test_engine_open_again_after_close(
    assistant_engine_factory,
    tracking_mini_executor,
) -> None:
    engine = assistant_engine_factory(
        {"open_app": True, "close_app": True, "unknown": False},
        executor=tracking_mini_executor,
    )
    assert engine.handle("open notepad") == "notepad opened."
    assert engine.handle("close notepad") == "notepad closed."
    assert engine.handle("open again") == "notepad opened."
