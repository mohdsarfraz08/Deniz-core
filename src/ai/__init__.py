"""Phase 10 AI Foundation Layer — public API.

Exports the primary interfaces consumed by the Phase 11 Hybrid Router.
Only these symbols are part of the stable public contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai.schema import IntentResult, IntentValidationError, unknown_result, validate_intent_result

if TYPE_CHECKING:
    from ai.classifier import AIClassifier
    from ai.prompt_builder import PromptBuilder
    from ai.router import Sensitivity, TriageDecision, TriageRouter

__all__ = [
    "AIClassifier",
    "IntentResult",
    "IntentValidationError",
    "PromptBuilder",
    "Sensitivity",
    "TriageDecision",
    "TriageRouter",
    "unknown_result",
    "validate_intent_result",
]


def __getattr__(name: str) -> Any:
    if name == "AIClassifier":
        from ai.classifier import AIClassifier

        return AIClassifier
    if name == "PromptBuilder":
        from ai.prompt_builder import PromptBuilder

        return PromptBuilder
    if name in ("Sensitivity", "TriageDecision", "TriageRouter"):
        import ai.router as router

        return getattr(router, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
