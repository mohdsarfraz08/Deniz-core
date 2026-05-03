from core.intent_engine import IntentEngine
from core.parser import CommandParser, Intent


class FakeExecutor:
    def __init__(self, file_explorer_count: int = 1):
        self.file_explorer_count = file_explorer_count
        self.close_app_calls: list[str] = []
        self.close_file_explorer_calls = 0

    def open_app(self, app_name: str) -> str:
        return f"{app_name} opened."

    def close_file_explorer_windows(self):
        self.close_file_explorer_calls += 1
        return {
            "status": "success",
            "action": "close_file_explorer_windows",
            "count": self.file_explorer_count,
        }

    def close_app(self, app_name: str) -> str:
        self.close_app_calls.append(app_name)
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


def test_parser_close_file_manager_phrases():
    parser = CommandParser()
    for phrase, expected_target in (
        ("close file manager", "file manager"),
        ("close explorer", "explorer"),
        ("close file explorer", "file explorer"),
        ("close my files", "my files"),
    ):
        it = parser.parse(phrase)
        assert it.intent == "close_app", phrase
        assert it.target == expected_target, phrase


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


def test_close_explorer_aliases_use_window_path():
    for target in ("explorer", "file manager", "file explorer", "my files", "explorer.exe"):
        fe = FakeExecutor(file_explorer_count=2)
        engine = IntentEngine(system_executor=fe)
        out = engine.execute(Intent(intent="close_app", target=target))
        assert fe.close_file_explorer_calls == 1
        assert not fe.close_app_calls
        assert "2 File Explorer windows" in out


def test_close_notepad_uses_process_close_app():
    fe = FakeExecutor()
    engine = IntentEngine(system_executor=fe)
    assert engine.execute(Intent(intent="close_app", target="notepad")) == "notepad closed."
    assert fe.close_app_calls == ["notepad"]
    assert fe.close_file_explorer_calls == 0


def test_close_explorer_zero_windows_message():
    fe = FakeExecutor(file_explorer_count=0)
    engine = IntentEngine(system_executor=fe)
    assert engine.execute(Intent(intent="close_app", target="explorer")) == (
        "No File Explorer windows were open."
    )


def test_close_explorer_single_window_message():
    fe = FakeExecutor(file_explorer_count=1)
    engine = IntentEngine(system_executor=fe)
    assert engine.execute(Intent(intent="close_app", target="explorer")) == (
        "Closed 1 File Explorer window."
    )


def test_intent_engine_confirm_without_pending():
    engine = IntentEngine(system_executor=FakeExecutor())
    assert engine.execute(Intent(intent="confirm_yes")) == "Nothing to confirm."
