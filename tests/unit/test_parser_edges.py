"""Command parser edge cases and substring coupling documented by tests."""

import pytest

from core.parser import CommandParser


@pytest.mark.parametrize(
    "phrase,expected_intent,expected_target",
    [
        ("OPEN NOTepad", "open_app", "notepad"),
        ("launch   CALC", "open_app", "calc"),
        ("start  paint", "open_app", "paint"),
        ("Hi", "greet", None),
        ("YES", "confirm_yes", None),
        ("NO", "confirm_no", None),
    ],
)
def test_parse_normalizes_case_and_whitespace(
    phrase: str, expected_intent: str, expected_target: str | None
) -> None:
    p = CommandParser()
    it = p.parse(phrase)
    assert it.intent == expected_intent
    assert it.target == expected_target


def test_parse_open_without_app_name_is_unknown() -> None:
    """Only bare \"open\" after normalization — no \"open \" prefix with target."""
    p = CommandParser()
    assert p.parse("open").intent == "unknown"


@pytest.mark.parametrize(
    "phrase",
    [
        "hello world",
        "please open sesame",
        "maybe close stuff",
    ],
)
def test_parse_unrecognized_phrases_are_unknown(phrase: str) -> None:
    assert CommandParser().parse(phrase).intent == "unknown"


def test_parse_ram_substring_matches_inside_other_words() -> None:
    """\"ram\" appears inside \"program\" — parser maps to memory intent."""
    p = CommandParser()
    it = p.parse("misprogram error log")
    assert it.intent == "get_memory_usage"


def test_parse_open_shutdown_targets_app_not_dangerous_intent() -> None:
    """Open wins before dangerous-system routing."""
    p = CommandParser()
    it = p.parse("open shutdown")
    assert it.intent == "open_app"
    assert it.target == "shutdown"


def test_parse_shutdown_system_is_dangerous_system() -> None:
    assert CommandParser().parse("shutdown system").intent == "dangerous_system"


def test_parse_remind_me_prefix_is_not_implemented() -> None:
    assert CommandParser().parse("remind me at noon").intent == "not_implemented"


@pytest.mark.parametrize(
    "phrase",
    [
        "set timer",
        "set alarm",
        "translate hello to french",
        "send email to bob",
        "schedule meeting tomorrow",
    ],
)
def test_parse_not_implemented_exact_and_prefixes(phrase: str) -> None:
    assert CommandParser().parse(phrase).intent == "not_implemented"


@pytest.mark.parametrize(
    "phrase",
    [
        "poweroff now",
        "halt machine",
        "reboot the system",
        "restart computer",
        "format c: drive",
        "wipe the disk clean",
    ],
)
def test_parse_dangerous_system_variants(phrase: str) -> None:
    assert CommandParser().parse(phrase).intent == "dangerous_system"
