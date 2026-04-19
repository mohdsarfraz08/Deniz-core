import pytest

from core.security.validator import validate_input


@pytest.mark.parametrize(
    "text",
    [
        "hello",
        "open notepad",
        "check cpu",
        "what time is it",
    ],
)
def test_validate_accepts_normal_phrases(text: str) -> None:
    ok, err = validate_input(text)
    assert ok is True
    assert err == ""


def test_validate_rejects_empty() -> None:
    ok, err = validate_input("")
    assert ok is False
    assert "empty" in err.lower()

    ok2, err2 = validate_input("   ")
    assert ok2 is False


@pytest.mark.parametrize(
    "text",
    [
        "foo;rm -rf /",
        "a && b",
        "a || b",
        "a|b",
        "echo `id`",
        "$(whoami)",
        "a\nb",
    ],
)
def test_validate_rejects_injection_patterns(text: str) -> None:
    ok, err = validate_input(text)
    assert ok is False
    assert "disallowed" in err.lower()
