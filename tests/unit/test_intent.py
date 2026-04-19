from core.intent_engine import IntentEngine
from core.parser import CommandParser, Intent


class FakeExecutor:
    def open_app(self, app_name: str) -> str:
        return f"{app_name} opened."

    def close_app(self, app_name: str) -> str:
        return f"{app_name} closed."

    def get_time(self) -> str:
        return "Current time is 10:00:00."

    def get_cpu_usage(self) -> str:
        return "Current CPU usage: 10%"

    def get_memory_usage(self) -> str:
        return "Current Memory usage: 40%"


def test_parser_cpu_memory_time_intents():
    parser = CommandParser()

    assert parser.parse("check cpu").intent == "get_cpu_usage"
    assert parser.parse("check memory").intent == "get_memory_usage"
    assert parser.parse("what time is it").intent == "get_time"


def test_parser_greet_and_open_app():
    parser = CommandParser()

    greet_intent = parser.parse("hello")
    assert greet_intent.intent == "greet"

    open_intent = parser.parse("open notepad")
    assert open_intent.intent == "open_app"
    assert open_intent.target == "notepad"


def test_intent_engine_core_actions():
    engine = IntentEngine(system_executor=FakeExecutor())

    assert engine.execute(Intent(intent="greet")) == "Hello. System operational."
    assert engine.execute(Intent(intent="open_app", target="notepad")) == "notepad opened."


def test_intent_engine_phase3_alias_actions():
    engine = IntentEngine(system_executor=FakeExecutor())

    assert engine.execute(Intent(intent="check_cpu")) == "Current CPU usage: 10%"
    assert engine.execute(Intent(intent="check_memory")) == "Current Memory usage: 40%"
    assert engine.execute(Intent(intent="show_time")) == "Current time is 10:00:00."


def test_parser_confirm_yes_no():
    parser = CommandParser()
    assert parser.parse("yes").intent == "confirm_yes"
    assert parser.parse("no").intent == "confirm_no"


def test_intent_engine_confirm_explorer_flow():
    engine = IntentEngine(system_executor=FakeExecutor())

    assert engine.execute(Intent(intent="close_app", target="explorer")).startswith(
        "Explorer is a critical process"
    )
    assert engine.execute(Intent(intent="confirm_yes")) == "explorer closed."
    assert engine.execute(Intent(intent="confirm_no")) == "Nothing to confirm."


def test_intent_engine_confirm_without_pending():
    engine = IntentEngine(system_executor=FakeExecutor())
    assert engine.execute(Intent(intent="confirm_yes")) == "Nothing to confirm."
