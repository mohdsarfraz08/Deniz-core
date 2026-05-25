import pytest

from engine import AssistantEngine, MSG_UNKNOWN_COMMAND, MSG_NOT_IMPLEMENTED
def test_engine_denies_when_intent_not_permitted(
    mini_executor,
    assistant_engine_factory,
) -> None:
    engine = assistant_engine_factory(
        {"greet": False, "open_app": True},
        executor=mini_executor,
    )
    assert engine.handle("hello") == "Access denied for this action."
    assert engine.handle("open calc") == "calc opened."


def test_engine_rejects_invalid_input_before_permissions(
    assistant_engine_factory,
    mini_executor,
) -> None:
    engine = assistant_engine_factory({"greet": True}, executor=mini_executor)
    ok_msg = engine.handle("bad;echo")
    assert "disallowed" in ok_msg.lower()


def test_engine_unknown_intent_is_not_security_denial(
    assistant_engine_factory,
    mini_executor,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown input is a parser miss — friendly message, no permission warning."""
    engine = assistant_engine_factory(
        {"greet": True, "unknown": False},
        executor=mini_executor,
    )
    with caplog.at_level("WARNING"):
        out = engine.handle("xyzzy nonsense phrase")
    assert out == MSG_UNKNOWN_COMMAND
    assert "Access Denied" not in caplog.text


def test_engine_dangerous_system_is_permission_denial(
    assistant_engine_factory,
    mini_executor,
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine = assistant_engine_factory(
        {"dangerous_system": False, "greet": True},
        executor=mini_executor,
    )
    with caplog.at_level("WARNING"):
        out = engine.handle("shutdown system")
    assert out == "Access denied for this action."
    assert "Access Denied" in caplog.text


def test_engine_not_implemented_returns_capability_message(
    assistant_engine_factory,
    mini_executor,
) -> None:
    engine = assistant_engine_factory({"greet": True}, executor=mini_executor)
    assert engine.handle("remind me at noon") == MSG_NOT_IMPLEMENTED
