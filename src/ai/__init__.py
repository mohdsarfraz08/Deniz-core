"""Phase 10 AI Foundation Layer — public API.

Exports the primary interfaces consumed by the Phase 11 Hybrid Router.
Only these symbols are part of the stable public contract.
"""

from ai.schema import IntentResult, IntentValidationError, validate_intent_result

__all__ = [
    "IntentResult",
    "IntentValidationError",
    "validate_intent_result",
]
