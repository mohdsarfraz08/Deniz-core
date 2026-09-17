"""ai/schema.py — IntentResult contract and schema validator.

Milestone 10.1 — Core Engine Module Member

This module defines the single authoritative data contract exchanged between
the AI layer and the rest of the system.  Every LLM provider in Phase 10
ultimately returns an IntentResult; the Phase 11 Hybrid Router accepts nothing
else.

Design constraints
------------------
- The allowed intent names are loaded **at runtime** from
  ``config/permissions.json``.  The AI cannot return an intent that does not
  exist in the permission registry — this is the primary safety boundary.
- ``validate_intent_result`` raises ``IntentValidationError`` (not a raw
  ValueError or KeyError) so callers can catch AI-layer validation failures
  independently of other exception types.
- No network I/O, no LLM calls, no side-effects occur in this module.

Phase 11 note
-------------
The Phase 11 Hybrid Router receives an ``IntentResult`` from the AI layer and
converts it to a ``core.parser.Intent`` before dispatching to the
``IntentEngine``.  This conversion is Phase 11 scope; this module provides
only the schema contract.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DEFAULT_PERMISSIONS_PATH: Final[Path] = _REPO_ROOT / "config" / "permissions.json"

# 'unknown' is always a valid intent — it is the fail-closed sentinel value.
_ALWAYS_ALLOWED: Final[frozenset[str]] = frozenset({"unknown"})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class IntentValidationError(ValueError):
    """Raised when the LLM response cannot be validated against the IntentResult schema.

    Callers should catch this exception independently of generic ``ValueError``
    to distinguish AI-layer schema failures from other value errors.

    Args:
        message: Human-readable description of the validation failure.
        raw_response: The raw LLM output string that failed validation.
            Stored for audit logging; never written to user-facing output.
    """

    def __init__(self, message: str, raw_response: str = "") -> None:
        super().__init__(message)
        self.raw_response: str = raw_response


# ---------------------------------------------------------------------------
# IntentResult
# ---------------------------------------------------------------------------


@dataclass
class IntentResult:
    """The validated, structured output of the AI classification pipeline.

    Every provider in the Phase 10 AI layer ultimately produces an
    ``IntentResult``.  All fields are fully type-annotated.  Instances are
    constructed exclusively by ``validate_intent_result``; callers must not
    build them directly from raw LLM output.

    Attributes:
        intent: The classified intent name.  Must exist in
            ``config/permissions.json`` or be ``"unknown"``.
        target: Primary target of the intent (e.g. app name, file path).
            ``None`` when the intent requires no target.
        value: Secondary payload (e.g. file content for ``write_file``).
            ``None`` when not applicable.
        confidence: Provider-reported or estimated confidence score in the
            range ``[0.0, 1.0]``.  A score of ``0.0`` indicates a fail-closed
            fallback result; no model produced this value.
        raw_response: The full, unmodified LLM output string retained for
            audit trail and debug purposes.  **Never expose this to the user.**
        tier: The routing tier that produced this result.
            ``0`` = deterministic parser (Phase 11), ``1`` = Ollama local,
            ``2`` = Nebius/Nemotron cloud.  Default ``-1`` indicates the field
            has not been set by the router yet (schema layer is tier-agnostic).
    """

    intent: str
    target: str | None = None
    value: str | None = None
    confidence: float = 0.0
    raw_response: str = field(default="", repr=False)
    tier: int = -1

    def __post_init__(self) -> None:
        """Enforce basic invariants after construction.

        Raises:
            ValueError: If ``confidence`` is outside ``[0.0, 1.0]``.
        """
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"IntentResult.confidence must be in [0.0, 1.0]; got {self.confidence!r}"
            )

    @property
    def is_unknown(self) -> bool:
        """Return ``True`` when the intent is the fail-closed sentinel ``'unknown'``."""
        return self.intent == "unknown"

    @property
    def is_actionable(self) -> bool:
        """Return ``True`` when the intent can be dispatched to the execution layer."""
        return not self.is_unknown and self.confidence > 0.0


# ---------------------------------------------------------------------------
# Allowed intent registry
# ---------------------------------------------------------------------------


def _load_allowed_intents(permissions_path: Path | None = None) -> frozenset[str]:
    """Load the set of permitted intent names from ``config/permissions.json``.

    The returned set always includes ``"unknown"`` regardless of the file
    contents so the fail-closed sentinel is never rejected by the validator.

    Args:
        permissions_path: Optional override for the permissions file path.
            Defaults to ``config/permissions.json`` in the repo root.

    Returns:
        A ``frozenset`` of permitted intent name strings.
    """
    target = permissions_path or _DEFAULT_PERMISSIONS_PATH
    try:
        raw = target.read_text(encoding="utf-8")
        data: dict[str, bool] = json.loads(raw)
        intents = frozenset(data.keys()) | _ALWAYS_ALLOWED
        logger.debug("Loaded %d allowed intents from %s", len(intents), target)
        return intents
    except FileNotFoundError:
        logger.warning(
            "permissions.json not found at %s; only 'unknown' will be allowed.", target
        )
        return _ALWAYS_ALLOWED
    except (json.JSONDecodeError, AttributeError) as exc:
        logger.warning(
            "Failed to parse permissions.json (%s); only 'unknown' will be allowed.", exc
        )
        return _ALWAYS_ALLOWED


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def validate_intent_result(
    data: dict,
    *,
    raw_response: str = "",
    permissions_path: Path | None = None,
) -> IntentResult:
    """Validate a parsed LLM JSON response and return a typed ``IntentResult``.

    This is the **only** sanctioned way to construct an ``IntentResult`` from
    LLM output.  It enforces:

    1. Required fields are present (``intent``, ``confidence``).
    2. ``intent`` is a non-empty string.
    3. ``intent`` exists in ``config/permissions.json`` or is ``"unknown"``.
    4. ``confidence`` is a float in ``[0.0, 1.0]``.
    5. ``target`` and ``value``, when present, are strings or ``None``.

    Args:
        data: A ``dict`` parsed from the raw LLM JSON response.
        raw_response: The original LLM output string, stored verbatim in
            ``IntentResult.raw_response`` for audit purposes.
        permissions_path: Optional override path for ``permissions.json``.
            Primarily used in tests to inject a custom allowlist.

    Returns:
        A validated ``IntentResult`` instance.

    Raises:
        IntentValidationError: If any validation rule is violated.

    Examples:
        >>> result = validate_intent_result(
        ...     {"intent": "open_app", "target": "chrome",
        ...      "value": None, "confidence": 0.95},
        ...     raw_response='{"intent":"open_app",...}',
        ... )
        >>> result.intent
        'open_app'
        >>> result.confidence
        0.95

        >>> validate_intent_result({"intent": "hack_system", "confidence": 0.9})
        Traceback (most recent call last):
            ...
        ai.schema.IntentValidationError: Intent 'hack_system' is not in the allowed registry.
    """
    allowed = _load_allowed_intents(permissions_path)

    # --- 1. Required field: intent ---
    if "intent" not in data:
        raise IntentValidationError(
            "LLM response missing required field 'intent'.", raw_response=raw_response
        )

    intent = data["intent"]
    if not isinstance(intent, str) or not intent.strip():
        raise IntentValidationError(
            f"'intent' must be a non-empty string; got {intent!r}.",
            raw_response=raw_response,
        )
    intent = intent.strip().lower()

    # --- 2. Intent allowlist check ---
    if intent not in allowed:
        raise IntentValidationError(
            f"Intent {intent!r} is not in the allowed registry.",
            raw_response=raw_response,
        )

    # --- 3. Required field: confidence ---
    if "confidence" not in data:
        raise IntentValidationError(
            "LLM response missing required field 'confidence'.", raw_response=raw_response
        )

    confidence_raw = data["confidence"]
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        raise IntentValidationError(
            f"'confidence' must be numeric; got {confidence_raw!r}.",
            raw_response=raw_response,
        )

    if not (0.0 <= confidence <= 1.0):
        raise IntentValidationError(
            f"'confidence' must be in [0.0, 1.0]; got {confidence!r}.",
            raw_response=raw_response,
        )

    # --- 4. Optional fields: target, value ---
    target = data.get("target")
    if target is not None and not isinstance(target, str):
        raise IntentValidationError(
            f"'target' must be a string or null; got {type(target).__name__!r}.",
            raw_response=raw_response,
        )

    value = data.get("value")
    if value is not None and not isinstance(value, str):
        raise IntentValidationError(
            f"'value' must be a string or null; got {type(value).__name__!r}.",
            raw_response=raw_response,
        )

    return IntentResult(
        intent=intent,
        target=target or None,
        value=value or None,
        confidence=confidence,
        raw_response=raw_response,
    )


# ---------------------------------------------------------------------------
# Fail-closed factory
# ---------------------------------------------------------------------------


def unknown_result(raw_response: str = "", tier: int = -1) -> IntentResult:
    """Return the canonical fail-closed ``IntentResult``.

    Used by the ``AIClassifier`` whenever a provider fails, returns malformed
    JSON, or the validator rejects the LLM output.  A confidence of ``0.0``
    signals to the Phase 11 Hybrid Router that this result was not produced
    by a model.

    Args:
        raw_response: The raw LLM output that triggered the fallback.
        tier: The tier that failed (for audit logging).

    Returns:
        ``IntentResult(intent='unknown', confidence=0.0)``.
    """
    return IntentResult(
        intent="unknown",
        confidence=0.0,
        raw_response=raw_response,
        tier=tier,
    )
