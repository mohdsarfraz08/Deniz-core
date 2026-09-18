"""ai/classifier.py — Orchestrating AI Intent Classifier.

Milestone 10.6 — Core Engine Module Member

Coordinates TriageRouter, PromptBuilder, concrete providers, and schema validation.
Implements retry logic, tier dispatch, and strict fail-closed safety.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Final

from ai.prompt_builder import PromptBuilder
from ai.providers import AbstractProvider, ProviderError, get_provider
from ai.router import Sensitivity, TriageDecision, TriageRouter
from ai.schema import IntentResult, IntentValidationError, unknown_result, validate_intent_result
from core.action_results import sanitise_for_audit

logger = logging.getLogger(__name__)

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH: Final[Path] = _REPO_ROOT / "config" / "ai_config.json"
_DEFAULT_PERMISSIONS_PATH: Final[Path] = _REPO_ROOT / "config" / "permissions.json"


def _extract_json_payload(raw_text: str) -> dict:
    """Extract and parse JSON dictionary from raw LLM output text.

    Handles optional markdown code fences (```json ... ```) or surrounding whitespace.

    Args:
        raw_text: Raw response string from the provider.

    Returns:
        Parsed dictionary.

    Raises:
        IntentValidationError: If text cannot be parsed into a JSON dictionary.
    """
    cleaned = raw_text.strip()
    if not cleaned:
        raise IntentValidationError("Provider returned empty response", raw_response=raw_text)

    # 1. Direct parse attempt
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 2. Extract from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        try:
            data = json.loads(fence_match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    # 3. Find outer braces
    brace_start = cleaned.find("{")
    brace_end = cleaned.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        candidate = cleaned[brace_start : brace_end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise IntentValidationError(
        f"Failed to parse valid JSON dictionary from LLM response: {raw_text[:100]!r}",
        raw_response=raw_text,
    )


class AIClassifier:
    """Orchestrates triage routing, provider dispatch, retry, and schema validation.

    Guarantees:
      - Fail-closed: Never crashes on provider or parsing failures; returns
        ``IntentResult(intent='unknown', confidence=0.0)``.
      - AI Ethics Gate: Sensitive file/path inputs never touch cloud endpoints.
      - PII Scrubbing: User input sent to cloud endpoints is scrubbed via sanitise_for_audit.
      - Allowlist Binding: Intent names must be approved in permissions.json.
    """

    def __init__(
        self,
        config_path: Path | None = None,
        permissions_path: Path | None = None,
        tier1_provider: AbstractProvider | None = None,
        tier2_provider: AbstractProvider | None = None,
        router: TriageRouter | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._config_path = config_path or _DEFAULT_CONFIG_PATH
        self._permissions_path = permissions_path or _DEFAULT_PERMISSIONS_PATH

        self._router = router or TriageRouter()
        self._prompt_builder = prompt_builder or PromptBuilder(self._permissions_path)

        # Load config or defaults
        self._config = self._load_config()

        # Injected or lazily initialized providers
        self._tier1_provider = tier1_provider
        self._tier2_provider = tier2_provider

    def _load_config(self) -> dict[str, Any]:
        """Load ai_config.json if present, otherwise return safe defaults."""
        if self._config_path.is_file():
            try:
                return json.loads(self._config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Could not parse %s (%s); using defaults", self._config_path, exc)

        return {
            "tier1": {"provider": "ollama", "model": "llama3.2", "timeout_s": 10.0, "max_retries": 1},
            "tier2": {
                "provider": "nebius",
                "model": "nvidia/llama-3.1-nemotron-70b-instruct",
                "timeout_s": 30.0,
                "max_retries": 1,
            },
        }

    def get_tier1_provider(self) -> AbstractProvider:
        """Return or lazily construct the Tier 1 provider."""
        if self._tier1_provider is None:
            tier1_cfg = self._config.get("tier1", {})
            p_name = tier1_cfg.get("provider", "ollama")
            model = tier1_cfg.get("model", "llama3.2")
            timeout_s = float(tier1_cfg.get("timeout_s", 10.0))
            self._tier1_provider = get_provider(p_name, model=model, timeout_s=timeout_s)
        return self._tier1_provider

    def get_tier2_provider(self) -> AbstractProvider:
        """Return or lazily construct the Tier 2 provider."""
        if self._tier2_provider is None:
            tier2_cfg = self._config.get("tier2", {})
            p_name = tier2_cfg.get("provider", "nebius")
            model = tier2_cfg.get("model", "nvidia/llama-3.1-nemotron-70b-instruct")
            timeout_s = float(tier2_cfg.get("timeout_s", 30.0))
            self._tier2_provider = get_provider(p_name, model=model, timeout_s=timeout_s)
        return self._tier2_provider

    def classify(self, user_input: str) -> IntentResult:
        """Classify user input into a validated IntentResult.

        Workflow:
          1. Empty check -> unknown.
          2. TriageRouter routes to Tier 0, 1, or 2.
          3. Tier 0 -> return unknown (delegated to deterministic parser).
          4. Tier 1/2 -> build prompt, dispatch to provider with retry, validate JSON.
          5. Fail-closed fallback to unknown_result on any error.

        Args:
            user_input: Raw user prompt text.

        Returns:
            Validated IntentResult instance.
        """
        trimmed = user_input.strip()
        if not trimmed:
            return unknown_result(raw_response="empty input", tier=0)

        decision: TriageDecision = self._router.route(trimmed)
        logger.debug(
            "Triage decision: tier=%d, sensitivity=%s, reason=%s",
            decision.tier,
            decision.sensitivity.value,
            decision.reason,
        )

        if decision.tier == 0:
            # Tier 0 is reserved for deterministic CommandParser (zero latency)
            return unknown_result(raw_response="Tier 0 deterministic match", tier=0)

        target_tier = decision.tier

        # AI Ethics Gate: If classified sensitive, force Tier 1 local edge even if tier 2 was suggested
        if decision.sensitivity == Sensitivity.SENSITIVE:
            target_tier = 1

        if target_tier == 1:
            return self._dispatch_tier1(trimmed)
        else:
            return self._dispatch_tier2(trimmed)

    def _dispatch_tier1(self, user_input: str) -> IntentResult:
        """Dispatch input to Tier 1 local edge engine (Ollama)."""
        prompt = self._prompt_builder.build_prompt(user_input, is_cloud=False)
        tier1_cfg = self._config.get("tier1", {})
        max_retries = int(tier1_cfg.get("max_retries", 1))

        provider = self.get_tier1_provider()
        return self._invoke_with_retry(
            provider=provider,
            prompt=prompt,
            target_tier=1,
            max_retries=max_retries,
        )

    def _dispatch_tier2(self, user_input: str) -> IntentResult:
        """Dispatch input to Tier 2 Cloud Specialist (Nebius / Nemotron)."""
        # AI Ethics Gate: Enforce PII scrubbing before sending prompt to cloud
        prompt = self._prompt_builder.build_prompt(user_input, is_cloud=True)
        tier2_cfg = self._config.get("tier2", {})
        max_retries = int(tier2_cfg.get("max_retries", 1))

        provider = self.get_tier2_provider()
        return self._invoke_with_retry(
            provider=provider,
            prompt=prompt,
            target_tier=2,
            max_retries=max_retries,
        )

    def _invoke_with_retry(
        self,
        provider: AbstractProvider,
        prompt: str,
        target_tier: int,
        max_retries: int,
    ) -> IntentResult:
        """Invoke provider with retry logic, schema validation, and fail-closed catch-all."""
        last_raw = ""
        attempts = 0

        while attempts <= max_retries:
            attempts += 1
            try:
                raw_response = provider.classify(prompt)
                last_raw = raw_response

                data = _extract_json_payload(raw_response)
                result = validate_intent_result(
                    data,
                    raw_response=raw_response,
                    permissions_path=self._permissions_path,
                )
                result.tier = target_tier
                logger.info(
                    "AI classification success: intent=%s, confidence=%.2f, tier=%d",
                    result.intent,
                    result.confidence,
                    result.tier,
                )
                return result

            except ProviderError as err:
                last_raw = err.raw_response or str(err)
                logger.warning(
                    "ProviderError in tier %d (attempt %d/%d, recoverable=%s): %s",
                    target_tier,
                    attempts,
                    max_retries + 1,
                    err.recoverable,
                    err.message,
                )
                if not err.recoverable:
                    break

            except IntentValidationError as err:
                last_raw = err.raw_response
                logger.warning(
                    "IntentValidationError in tier %d (attempt %d/%d): %s",
                    target_tier,
                    attempts,
                    max_retries + 1,
                    err,
                )

            except Exception as exc:
                logger.error("Unexpected error in AI classification tier %d: %s", target_tier, exc)
                break

        # Fail-closed sentinel
        logger.warning(
            "AI classification failed closed for tier %d after %d attempts",
            target_tier,
            attempts,
        )
        return unknown_result(raw_response=last_raw, tier=target_tier)
