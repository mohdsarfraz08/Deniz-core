"""Unit tests for Milestone 10.1 — ai/schema.py

Tests cover:
- TestIntentResult:           Dataclass construction, invariants, properties.
- TestIntentValidationError:  Exception carries raw_response for audit trail.
- TestValidateIntentResult:   Full validation pipeline — happy paths and all
                              rejection branches.
- TestAllowlistBinding:       validate_intent_result() uses the live permissions
                              registry to gate unknown intent names.
- TestUnknownResult:          Fail-closed factory returns correct sentinel.

No network I/O. No LLM calls. All tests are pure unit tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai.schema import (
    IntentResult,
    IntentValidationError,
    unknown_result,
    validate_intent_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def perm_file(tmp_path: Path) -> Path:
    """Write a minimal permissions.json to a temp dir and return its path."""
    data = {
        "open_app": True,
        "close_app": True,
        "create_file": True,
        "delete_file": True,
        "get_time": True,
    }
    p = tmp_path / "permissions.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _valid(overrides: dict | None = None, perm: Path | None = None) -> IntentResult:
    """Helper: build a valid payload and run validate_intent_result."""
    payload: dict = {
        "intent": "open_app",
        "target": "chrome",
        "value": None,
        "confidence": 0.95,
    }
    if overrides:
        payload.update(overrides)
    return validate_intent_result(payload, raw_response="<raw>", permissions_path=perm)


# ---------------------------------------------------------------------------
# TestIntentResult
# ---------------------------------------------------------------------------


class TestIntentResult:

    def test_basic_construction(self) -> None:
        r = IntentResult(intent="open_app", target="chrome", confidence=0.9)
        assert r.intent == "open_app"
        assert r.target == "chrome"
        assert r.confidence == 0.9
        assert r.value is None
        assert r.raw_response == ""
        assert r.tier == -1

    def test_is_unknown_true(self) -> None:
        assert IntentResult(intent="unknown", confidence=0.0).is_unknown is True

    def test_is_unknown_false(self) -> None:
        assert IntentResult(intent="open_app", confidence=0.8).is_unknown is False

    def test_is_actionable_true(self) -> None:
        r = IntentResult(intent="open_app", confidence=0.8)
        assert r.is_actionable is True

    def test_is_actionable_false_when_unknown(self) -> None:
        r = IntentResult(intent="unknown", confidence=0.0)
        assert r.is_actionable is False

    def test_is_actionable_false_when_zero_confidence(self) -> None:
        r = IntentResult(intent="open_app", confidence=0.0)
        assert r.is_actionable is False

    def test_confidence_boundary_zero(self) -> None:
        r = IntentResult(intent="unknown", confidence=0.0)
        assert r.confidence == 0.0

    def test_confidence_boundary_one(self) -> None:
        r = IntentResult(intent="open_app", confidence=1.0)
        assert r.confidence == 1.0

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            IntentResult(intent="open_app", confidence=1.1)

    def test_confidence_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="confidence"):
            IntentResult(intent="open_app", confidence=-0.01)

    def test_tier_field_default(self) -> None:
        assert IntentResult(intent="unknown", confidence=0.0).tier == -1

    def test_tier_field_set(self) -> None:
        r = IntentResult(intent="open_app", confidence=0.9, tier=2)
        assert r.tier == 2

    def test_raw_response_not_in_repr(self) -> None:
        r = IntentResult(intent="open_app", confidence=0.9, raw_response="secret")
        assert "secret" not in repr(r)


# ---------------------------------------------------------------------------
# TestIntentValidationError
# ---------------------------------------------------------------------------


class TestIntentValidationError:

    def test_carries_raw_response(self) -> None:
        err = IntentValidationError("bad intent", raw_response="raw_llm_output")
        assert err.raw_response == "raw_llm_output"
        assert str(err) == "bad intent"

    def test_default_raw_response_empty(self) -> None:
        err = IntentValidationError("bad intent")
        assert err.raw_response == ""

    def test_is_value_error_subclass(self) -> None:
        assert isinstance(IntentValidationError("x"), ValueError)


# ---------------------------------------------------------------------------
# TestValidateIntentResult — happy paths
# ---------------------------------------------------------------------------


class TestValidateIntentResultHappy:

    def test_valid_full_payload(self, perm_file: Path) -> None:
        r = _valid(perm=perm_file)
        assert r.intent == "open_app"
        assert r.target == "chrome"
        assert r.confidence == 0.95
        assert r.raw_response == "<raw>"

    def test_unknown_intent_always_allowed(self, perm_file: Path) -> None:
        r = validate_intent_result(
            {"intent": "unknown", "confidence": 0.0},
            permissions_path=perm_file,
        )
        assert r.intent == "unknown"

    def test_target_none_accepted(self, perm_file: Path) -> None:
        r = _valid({"target": None}, perm=perm_file)
        assert r.target is None

    def test_empty_string_target_coerced_to_none(self, perm_file: Path) -> None:
        r = _valid({"target": ""}, perm=perm_file)
        assert r.target is None

    def test_value_populated(self, perm_file: Path) -> None:
        r = _valid({"intent": "create_file", "value": "hello world"}, perm=perm_file)
        assert r.value == "hello world"

    def test_intent_lowercased(self, perm_file: Path) -> None:
        r = _valid({"intent": "OPEN_APP"}, perm=perm_file)
        assert r.intent == "open_app"

    def test_confidence_integer_accepted(self, perm_file: Path) -> None:
        r = _valid({"confidence": 1}, perm=perm_file)
        assert r.confidence == 1.0

    def test_confidence_string_numeric_accepted(self, perm_file: Path) -> None:
        r = _valid({"confidence": "0.8"}, perm=perm_file)
        assert r.confidence == 0.8


# ---------------------------------------------------------------------------
# TestValidateIntentResult — rejection paths
# ---------------------------------------------------------------------------


class TestValidateIntentResultRejection:

    def test_missing_intent_field(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="missing.*'intent'"):
            validate_intent_result({"confidence": 0.9}, permissions_path=perm_file)

    def test_intent_not_string(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="non-empty string"):
            validate_intent_result(
                {"intent": 42, "confidence": 0.9}, permissions_path=perm_file
            )

    def test_intent_empty_string(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="non-empty string"):
            validate_intent_result(
                {"intent": "  ", "confidence": 0.9}, permissions_path=perm_file
            )

    def test_intent_not_in_allowlist(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="not in the allowed registry"):
            validate_intent_result(
                {"intent": "hack_system", "confidence": 0.9},
                permissions_path=perm_file,
            )

    def test_missing_confidence_field(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="missing.*'confidence'"):
            validate_intent_result({"intent": "open_app"}, permissions_path=perm_file)

    def test_confidence_non_numeric(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="numeric"):
            validate_intent_result(
                {"intent": "open_app", "confidence": "high"},
                permissions_path=perm_file,
            )

    def test_confidence_above_one(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match=r"\[0\.0, 1\.0\]"):
            validate_intent_result(
                {"intent": "open_app", "confidence": 1.5}, permissions_path=perm_file
            )

    def test_confidence_below_zero(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match=r"\[0\.0, 1\.0\]"):
            validate_intent_result(
                {"intent": "open_app", "confidence": -0.1}, permissions_path=perm_file
            )

    def test_target_wrong_type(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="string or null"):
            validate_intent_result(
                {"intent": "open_app", "confidence": 0.9, "target": 123},
                permissions_path=perm_file,
            )

    def test_value_wrong_type(self, perm_file: Path) -> None:
        with pytest.raises(IntentValidationError, match="string or null"):
            validate_intent_result(
                {"intent": "open_app", "confidence": 0.9, "value": ["list"]},
                permissions_path=perm_file,
            )

    def test_raw_response_stored_in_error(self, perm_file: Path) -> None:
        raw = '{"intent": "bad", "confidence": 0.9}'
        try:
            validate_intent_result(
                {"intent": "bad", "confidence": 0.9},
                raw_response=raw,
                permissions_path=perm_file,
            )
        except IntentValidationError as err:
            assert err.raw_response == raw
        else:
            pytest.fail("IntentValidationError was not raised")


# ---------------------------------------------------------------------------
# TestAllowlistBinding
# ---------------------------------------------------------------------------


class TestAllowlistBinding:

    def test_only_permitted_intents_accepted(self, tmp_path: Path) -> None:
        perm = tmp_path / "perm.json"
        perm.write_text(json.dumps({"greet": True}), encoding="utf-8")

        # 'greet' is allowed
        r = validate_intent_result(
            {"intent": "greet", "confidence": 0.8}, permissions_path=perm
        )
        assert r.intent == "greet"

        # 'open_app' is NOT in this custom allowlist
        with pytest.raises(IntentValidationError, match="not in the allowed registry"):
            validate_intent_result(
                {"intent": "open_app", "confidence": 0.8}, permissions_path=perm
            )

    def test_unknown_always_allowed_even_without_permissions_file(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.json"
        r = validate_intent_result(
            {"intent": "unknown", "confidence": 0.0}, permissions_path=missing
        )
        assert r.intent == "unknown"

    def test_malformed_permissions_file_falls_back_to_unknown_only(
        self, tmp_path: Path
    ) -> None:
        perm = tmp_path / "bad.json"
        perm.write_text("NOT JSON", encoding="utf-8")

        # 'unknown' must still work
        r = validate_intent_result(
            {"intent": "unknown", "confidence": 0.0}, permissions_path=perm
        )
        assert r.intent == "unknown"

        # anything else must be rejected
        with pytest.raises(IntentValidationError):
            validate_intent_result(
                {"intent": "open_app", "confidence": 0.9}, permissions_path=perm
            )


# ---------------------------------------------------------------------------
# TestUnknownResult
# ---------------------------------------------------------------------------


class TestUnknownResult:

    def test_returns_unknown_intent(self) -> None:
        r = unknown_result()
        assert r.intent == "unknown"

    def test_confidence_is_zero(self) -> None:
        r = unknown_result()
        assert r.confidence == 0.0

    def test_is_unknown_property(self) -> None:
        assert unknown_result().is_unknown is True

    def test_is_not_actionable(self) -> None:
        assert unknown_result().is_actionable is False

    def test_raw_response_stored(self) -> None:
        r = unknown_result(raw_response="bad json from llm", tier=2)
        assert r.raw_response == "bad json from llm"
        assert r.tier == 2

    def test_default_tier_is_minus_one(self) -> None:
        assert unknown_result().tier == -1
