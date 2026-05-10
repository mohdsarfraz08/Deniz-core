from core.action_registry import ActionRegistry


def test_get_action_missing_returns_none() -> None:
    r = ActionRegistry()
    assert r.get_action("nonexistent") is None


def test_register_and_retrieve_roundtrip() -> None:
    r = ActionRegistry()

    def hi():
        return "x"

    r.register_action("custom", hi)
    assert r.get_action("custom") is hi
