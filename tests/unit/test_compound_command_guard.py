"""
Phase 5 UX hardening -- compound command guard.

Verifies that:
  1. Compound inputs (action + conjunction + action) return 'compound_command'.
  2. Legitimate single-intent inputs are NOT caught by the guard.
  3. The engine surfaces MSG_COMPOUND_COMMAND to the user.
"""

import pytest

from core.parser import CommandParser, Intent
from engine import MSG_COMPOUND_COMMAND


# ---------------------------------------------------------------------------
# TRUE POSITIVES -- guard must fire
# ---------------------------------------------------------------------------

class TestCompoundCommandDetected:

    def setup_method(self):
        self.p = CommandParser()

    @pytest.mark.parametrize("phrase", [
        "open chrome and open notepad",
        "open chrome then open notepad",
        "open chrome also open notepad",
        "open chrome and close notepad",
        "open notepad then close calc",
        "open chrome and check cpu",
        "launch notepad then show time",
        "start calc also check memory",
        "close notepad and check cpu",
        "quit chrome then show time",
        "check cpu and show time",
        "check memory then check cpu",
        "show time also check memory",
        "check cpu also show time",
        "check cpu and open chrome",
    ])
    def test_compound_intent_returned(self, phrase: str) -> None:
        it = self.p.parse(phrase)
        assert it.intent == "compound_command", (
            f"Expected compound_command for {phrase!r}, got {it.intent!r}"
        )

    def test_compound_intent_has_no_target(self) -> None:
        it = self.p.parse("open chrome and check cpu")
        assert it.intent == "compound_command"
        assert it.target is None


# ---------------------------------------------------------------------------
# FALSE NEGATIVES -- guard must NOT fire
# ---------------------------------------------------------------------------

class TestCompoundCommandNotFired:

    def setup_method(self):
        self.p = CommandParser()

    def test_bare_also_not_caught(self) -> None:
        it = self.p.parse("also")
        assert it.intent != "compound_command"

    def test_and_question_not_caught(self) -> None:
        it = self.p.parse("and?")
        assert it.intent != "compound_command"

    def test_check_cpu_and_memory_not_caught(self) -> None:
        it = self.p.parse("check cpu and memory")
        assert it.intent == "get_cpu_usage"

    def test_check_cpu_and_time_not_caught(self) -> None:
        it = self.p.parse("check cpu and time")
        assert it.intent == "get_cpu_usage"

    def test_open_chrome_not_caught(self) -> None:
        it = self.p.parse("open chrome")
        assert it.intent == "open_app"
        assert it.target == "chrome"

    def test_close_notepad_not_caught(self) -> None:
        it = self.p.parse("close notepad")
        assert it.intent == "close_app"

    def test_what_else_not_caught(self) -> None:
        it = self.p.parse("what else")
        assert it.intent == "unknown"

    def test_open_time_machine_not_caught(self) -> None:
        it = self.p.parse("open time machine")
        assert it.intent == "open_app"
        assert it.target == "time machine"

    def test_open_chrome_and_firefox_not_caught(self) -> None:
        """Right side has no action keyword -- not compound."""
        it = self.p.parse("open chrome and firefox")
        assert it.intent == "open_app"

    def test_conjunction_without_action_on_right_not_caught(self) -> None:
        it = self.p.parse("check cpu and performance graphs")
        assert it.intent == "get_cpu_usage"

    def test_greet_not_caught(self) -> None:
        it = self.p.parse("hello")
        assert it.intent == "greet"

    def test_confirm_yes_not_caught(self) -> None:
        it = self.p.parse("yes")
        assert it.intent == "confirm_yes"

    def test_confirm_no_not_caught(self) -> None:
        it = self.p.parse("no")
        assert it.intent == "confirm_no"


# ---------------------------------------------------------------------------
# ENGINE INTEGRATION -- correct user-facing message
# ---------------------------------------------------------------------------

class TestEngineCompoundResponse:

    def test_engine_returns_compound_message(
        self, assistant_engine_factory, session_test_executor
    ) -> None:
        engine = assistant_engine_factory(
            {"open_app": True, "get_cpu_usage": True},
            executor=session_test_executor,
        )
        response = engine.handle("open chrome and check cpu")
        assert response == MSG_COMPOUND_COMMAND

    def test_engine_compound_does_not_advance_session(
        self, assistant_engine_factory, session_test_executor
    ) -> None:
        engine = assistant_engine_factory(
            {"get_cpu_usage": True, "get_memory_usage": True},
            executor=session_test_executor,
        )
        engine.handle("check cpu")
        engine.handle("check cpu also show time")
        assert engine.session.last_intent == "get_cpu_usage"

    def test_engine_compound_check_cpu_then_show_time(
        self, assistant_engine_factory, session_test_executor
    ) -> None:
        engine = assistant_engine_factory(
            {"get_cpu_usage": True, "get_time": True},
            executor=session_test_executor,
        )
        assert engine.handle("check cpu then show time") == MSG_COMPOUND_COMMAND

    @pytest.mark.parametrize("phrase", [
        "check cpu also show time",
        "open notepad and check memory",
        "close chrome then show time",
    ])
    def test_engine_compound_variants_all_return_graceful_message(
        self, assistant_engine_factory, session_test_executor, phrase: str
    ) -> None:
        engine = assistant_engine_factory(
            {"open_app": True, "close_app": True, "get_cpu_usage": True,
             "get_memory_usage": True, "get_time": True},
            executor=session_test_executor,
        )
        assert engine.handle(phrase) == MSG_COMPOUND_COMMAND
