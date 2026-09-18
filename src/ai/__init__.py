"""Phase 10 AI Foundation Layer — public API.

Exports the primary interfaces consumed by the Phase 11 Hybrid Router.
Only these symbols are part of the stable public contract.
"""

from ai.classifier import AIClassifier
from ai.prompt_builder import PromptBuilder
from ai.router import Sensitivity, TriageDecision, TriageRouter
from ai.schema import IntentResult, IntentValidationError, unknown_result, validate_intent_result

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
