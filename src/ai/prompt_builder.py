"""ai/prompt_builder.py — Prompt construction and security boundaries.

Milestone 10.4 — Security Module Member

Constructs LLM prompts bound to the permissions allowlist, enforcing JSON output
schema, and guaranteeing PII scrubbing before any prompt is dispatched to cloud
endpoints (Tier 2 Nebius / Nemotron).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Final

from ai.schema import _load_allowed_intents
from core.action_results import sanitise_for_audit
from core.security.pii_scrubber import scrub_cloud_payload

logger = logging.getLogger(__name__)

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DEFAULT_PERMISSIONS_PATH: Final[Path] = _REPO_ROOT / "config" / "permissions.json"


class PromptBuilder:
    """Builds prompt strings for LLM classification with strict safety gates.

    Enforces:
      1. Dynamic binding to permitted intents loaded from permissions.json.
      2. PII scrubbing via sanitise_for_audit() whenever routing to cloud (is_cloud=True).
      3. Strict JSON output instruction conforming to IntentResult schema.
      4. Bias mitigation and refusal guidelines.

    Args:
        permissions_path: Optional path override for permissions.json.
    """

    def __init__(self, permissions_path: Path | None = None) -> None:
        self._permissions_path = permissions_path or _DEFAULT_PERMISSIONS_PATH
        self._allowed_intents = sorted(_load_allowed_intents(self._permissions_path))

    @property
    def allowed_intents(self) -> list[str]:
        """List of permitted intent strings."""
        return list(self._allowed_intents)

    def reload_permissions(self) -> None:
        """Reload allowed intents from disk."""
        self._allowed_intents = sorted(_load_allowed_intents(self._permissions_path))

    def build_prompt(self, user_input: str, is_cloud: bool = False) -> str:
        """Construct a complete prompt for intent classification.

        Args:
            user_input: Raw user input text.
            is_cloud: When True, applies PII scrubbing (sanitise_for_audit)
                before embedding into the prompt. Mandatory for Tier 2 cloud calls.

        Returns:
            Formatted prompt string ready for LLM consumption.
        """
        # AI Ethics Gate: Multi-pattern aggressive PII scrubbing before cloud dispatch
        safe_input = scrub_cloud_payload(user_input).scrubbed_text if is_cloud else user_input

        allowed_list_str = ", ".join(f'"{intent}"' for intent in self._allowed_intents)

        system_instruction = (
            "You are Deniz Core Intent Classifier, a deterministic, secure system intent parser.\n"
            "Analyze the user's natural language input and classify it into exactly one system intent.\n\n"
            "CRITICAL RULES:\n"
            f"1. You MUST select the 'intent' strictly from this allowed list:\n"
            f"   [{allowed_list_str}]\n"
            "2. If the user input does not clearly match any allowed intent, or is ambiguous, "
            "harmful, malicious, or out-of-scope, return 'unknown'.\n"
            "3. Do NOT infer intent based on demographic, political, or personal signals.\n"
            "4. Respond with ONLY a valid JSON object. No conversational text, no markdown fences (no ```json).\n\n"
            "SCHEMA:\n"
            "{\n"
            '  "intent": "<string from allowed list>",\n'
            '  "target": "<string or null>",\n'
            '  "value": "<string or null>",\n'
            '  "confidence": <float between 0.0 and 1.0>\n'
            "}\n\n"
            "EXAMPLES:\n"
            'Input: "open chrome"\n'
            'Output: {"intent": "open_app", "target": "chrome", "value": null, "confidence": 0.98}\n\n'
            'Input: "launch notepad"\n'
            'Output: {"intent": "open_app", "target": "notepad", "value": null, "confidence": 0.95}\n\n'
            'Input: "create file notes.txt"\n'
            'Output: {"intent": "create_file", "target": "notes.txt", "value": null, "confidence": 0.92}\n\n'
            'Input: "what is the capital of France?"\n'
            'Output: {"intent": "unknown", "target": null, "value": null, "confidence": 0.0}\n\n'
            f'User Input: "{safe_input}"\n'
            "JSON Output:"
        )
        return system_instruction
