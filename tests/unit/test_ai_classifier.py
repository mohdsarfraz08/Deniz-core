"""tests/unit/test_ai_classifier.py — Test suite for AI Layer modules.

Milestone 10.9 — Comprehensive tests for:
  - BaseProvider & ProviderError
  - OllamaProvider (Tier 1 local edge)
  - NebiusProvider (Tier 2 cloud specialist via Token Factory)
  - OpenAIProvider & GeminiProvider (cloud fallbacks)
  - Provider factory (get_provider)
  - PromptBuilder (PII scrubbing, allowlist binding, JSON schema instructions)
  - TriageRouter (3-tier dispatch, sensitivity boundaries)
  - AIClassifier (orchestration, retry, fail-closed, data governance)

All tests are 100% mocked — zero network requests, zero live API keys needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from ai.classifier import AIClassifier, _extract_json_payload
from ai.prompt_builder import PromptBuilder
from ai.providers import (
    AbstractProvider,
    GeminiProvider,
    NebiusProvider,
    OllamaProvider,
    OpenAIProvider,
    ProviderError,
    get_provider,
)
from ai.router import Sensitivity, TriageDecision, TriageRouter
from ai.schema import IntentResult, IntentValidationError, unknown_result


# ===========================================================================
# 1. Base Provider & ProviderError Tests
# ===========================================================================


class TestBaseProvider:

    def test_provider_error_attributes(self) -> None:
        err = ProviderError(
            "Connection dropped",
            provider="nebius",
            recoverable=True,
            status_code=503,
            raw_response="Service Unavailable",
        )
        assert err.message == "Connection dropped"
        assert err.provider == "nebius"
        assert err.recoverable is True
        assert err.status_code == 503
        assert err.raw_response == "Service Unavailable"
        assert "ProviderError('Connection dropped'" in repr(err)

    def test_abstract_provider_instantiation_fails_without_abstract_methods(self) -> None:
        class IncompleteProvider(AbstractProvider):
            pass

        with pytest.raises(TypeError):
            IncompleteProvider(model="test")  # type: ignore[abstract]


# ===========================================================================
# 2. OllamaProvider Tests (Tier 1)
# ===========================================================================


class TestOllamaProvider:

    def test_init_defaults(self) -> None:
        provider = OllamaProvider()
        assert provider.provider_name == "ollama"
        assert provider.model == "llama3.2"
        assert provider.host == "http://127.0.0.1:11434"
        assert provider.timeout_s == 10.0

    @patch("requests.get")
    def test_is_available_true(self, mock_get: MagicMock) -> None:
        mock_get.return_value.status_code = 200
        provider = OllamaProvider()
        assert provider.is_available() is True
        mock_get.assert_called_once_with("http://127.0.0.1:11434/api/tags", timeout=2.0)

    @patch("requests.get")
    def test_is_available_false_on_exception(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.exceptions.ConnectionError("refused")
        provider = OllamaProvider()
        assert provider.is_available() is False

    @patch("requests.post")
    def test_classify_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": '{"intent": "open_app", "target": "chrome", "confidence": 0.95}'
        }
        provider = OllamaProvider()
        res = provider.classify("launch chrome")
        assert res == '{"intent": "open_app", "target": "chrome", "confidence": 0.95}'
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["format"] == "json"
        assert kwargs["json"]["model"] == "llama3.2"

    @patch("requests.post")
    def test_classify_timeout_raises_recoverable_provider_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout("timed out")
        provider = OllamaProvider(timeout_s=5.0)
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("launch chrome")
        assert exc_info.value.recoverable is True
        assert exc_info.value.provider == "ollama"

    @patch("requests.post")
    def test_classify_connection_error_raises_recoverable_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError("offline")
        provider = OllamaProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("launch chrome")
        assert exc_info.value.recoverable is True
        assert "Is Ollama running?" in exc_info.value.message

    @patch("requests.post")
    def test_classify_http_500_raises_recoverable_error(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"
        provider = OllamaProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("test")
        assert exc_info.value.recoverable is True
        assert exc_info.value.status_code == 500


# ===========================================================================
# 3. NebiusProvider Tests (Tier 2 Cloud Specialist)
# ===========================================================================


class TestNebiusProvider:

    def test_missing_api_key_raises_non_recoverable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
        provider = NebiusProvider(api_key=None)
        assert provider.is_available() is False
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("write a plan")
        assert exc_info.value.recoverable is False
        assert "NEBIUS_API_KEY environment variable is not set" in exc_info.value.message

    def test_is_available_true_with_key(self) -> None:
        provider = NebiusProvider(api_key="mock-key-123")
        assert provider.is_available() is True
        assert provider.provider_name == "nebius"

    @patch("requests.post")
    def test_classify_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"intent": "open_app", "target": "chrome", "confidence": 0.98}'
                    }
                }
            ]
        }
        provider = NebiusProvider(api_key="mock-key-123")
        res = provider.classify("open chrome")
        assert "open_app" in res
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer mock-key-123"

    @patch("requests.post")
    def test_classify_401_auth_error_is_non_recoverable(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 401
        mock_post.return_value.text = "Unauthorized"
        provider = NebiusProvider(api_key="invalid-key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("test")
        assert exc_info.value.recoverable is False
        assert exc_info.value.status_code == 401

    @patch("requests.post")
    def test_classify_429_rate_limit_is_recoverable(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 429
        mock_post.return_value.text = "Rate limited"
        provider = NebiusProvider(api_key="mock-key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("test")
        assert exc_info.value.recoverable is True


# ===========================================================================
# 4. OpenAIProvider & GeminiProvider Tests
# ===========================================================================


class TestCloudFallbackProviders:

    def test_openai_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        provider = OpenAIProvider(api_key=None)
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("test")
        assert exc_info.value.recoverable is False

    @patch("requests.post")
    def test_openai_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": '{"intent": "greet", "confidence": 1.0}'}}]
        }
        provider = OpenAIProvider(api_key="sk-mock")
        res = provider.classify("hi")
        assert "greet" in res

    def test_gemini_missing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        provider = GeminiProvider(api_key=None)
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("test")
        assert exc_info.value.recoverable is False

    @patch("requests.post")
    def test_gemini_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": '{"intent": "greet", "confidence": 1.0}'}]}}
            ]
        }
        provider = GeminiProvider(api_key="gem-mock")
        res = provider.classify("hello")
        assert "greet" in res


# ===========================================================================
# 5. Provider Factory Tests
# ===========================================================================


class TestProviderFactory:

    def test_get_all_known_providers(self) -> None:
        assert isinstance(get_provider("nebius", api_key="k"), NebiusProvider)
        assert isinstance(get_provider("ollama"), OllamaProvider)
        assert isinstance(get_provider("openai", api_key="k"), OpenAIProvider)
        assert isinstance(get_provider("gemini", api_key="k"), GeminiProvider)

    def test_get_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown provider 'claude'"):
            get_provider("claude")


# ===========================================================================
# 6. PromptBuilder Tests (Security & PII Scrubbing)
# ===========================================================================


class TestPromptBuilder:

    def test_allowed_intents_loaded_from_permissions(self, tmp_path: Path) -> None:
        perm_file = tmp_path / "permissions.json"
        perm_file.write_text(json.dumps({"open_app": True, "close_app": True}), encoding="utf-8")
        builder = PromptBuilder(permissions_path=perm_file)
        assert "open_app" in builder.allowed_intents
        assert "close_app" in builder.allowed_intents
        assert "unknown" in builder.allowed_intents

    def test_cloud_prompt_scrubs_pii(self) -> None:
        builder = PromptBuilder()
        # Input with user directory
        raw_input = r"delete file C:\Users\alice\Documents\secret.txt"
        cloud_prompt = builder.build_prompt(raw_input, is_cloud=True)

        # The username 'alice' should be redacted by sanitise_for_audit
        assert "alice" not in cloud_prompt
        assert "<USER_DIR>" in cloud_prompt or "~" in cloud_prompt or "secret.txt" in cloud_prompt

    def test_local_prompt_preserves_local_path(self) -> None:
        builder = PromptBuilder()
        raw_input = r"delete file C:\Users\alice\Documents\secret.txt"
        local_prompt = builder.build_prompt(raw_input, is_cloud=False)
        assert r"C:\Users\alice\Documents\secret.txt" in local_prompt

    def test_prompt_includes_json_schema_and_refusal_rules(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build_prompt("open edge")
        assert "SCHEMA:" in prompt
        assert '"intent"' in prompt
        assert '"confidence"' in prompt
        assert "Do NOT infer intent based on demographic" in prompt


# ===========================================================================
# 7. TriageRouter Tests (3-Tier & Sensitivity Gates)
# ===========================================================================


class TestTriageRouter:

    def setup_method(self) -> None:
        self.router = TriageRouter()

    def test_empty_input_routes_to_tier0(self) -> None:
        decision = self.router.route("   ")
        assert decision.tier == 0

    def test_exact_known_command_routes_to_tier0(self) -> None:
        for cmd in ["open chrome", "close edge", "check cpu", "what time is it", "hello"]:
            decision = self.router.route(cmd)
            assert decision.tier == 0
            assert decision.sensitivity == Sensitivity.SAFE

    def test_file_operations_route_to_tier1_sensitive(self) -> None:
        sensitive_inputs = [
            "create file report.txt",
            "delete file secret.docx",
            "write notes.md",
            "copy file a to b",
            "list directory in C:/Windows",
            "erase the logs",
            "remove folder temp",
        ]
        for inp in sensitive_inputs:
            decision = self.router.route(inp)
            assert decision.tier == 1, f"Failed on input: {inp}"
            assert decision.sensitivity == Sensitivity.SENSITIVE, f"Failed on input: {inp}"

    def test_complex_reasoning_routes_to_tier2(self) -> None:
        complex_inputs = [
            "plan a multi-step sequence to scrape the web and summarize",
            "analyze the system logs and generate a diagnostic script",
            "architect a workflow to refactor our code base",
        ]
        for inp in complex_inputs:
            decision = self.router.route(inp)
            assert decision.tier == 2, f"Failed on input: {inp}"
            assert decision.sensitivity == Sensitivity.SAFE

    def test_natural_language_basic_routes_to_tier1(self) -> None:
        decision = self.router.route("please start up my browser")
        assert decision.tier == 1
        assert decision.sensitivity == Sensitivity.SAFE


# ===========================================================================
# 8. JSON Extraction Helper Tests
# ===========================================================================


class TestJsonExtraction:

    def test_clean_json(self) -> None:
        raw = '{"intent": "open_app", "confidence": 0.95}'
        assert _extract_json_payload(raw) == {"intent": "open_app", "confidence": 0.95}

    def test_markdown_fence_extraction(self) -> None:
        raw = "```json\n{\n  \"intent\": \"open_app\",\n  \"confidence\": 0.95\n}\n```"
        assert _extract_json_payload(raw) == {"intent": "open_app", "confidence": 0.95}

    def test_surrounding_conversational_text(self) -> None:
        raw = "Sure! Here is the classification result:\n{\"intent\": \"greet\", \"confidence\": 1.0}\nHope this helps!"
        assert _extract_json_payload(raw) == {"intent": "greet", "confidence": 1.0}

    def test_invalid_json_raises_validation_error(self) -> None:
        with pytest.raises(IntentValidationError):
            _extract_json_payload("I cannot classify this")


# ===========================================================================
# 9. AIClassifier Tests (Orchestration, Retries, Fail-Closed)
# ===========================================================================


class MockProvider(AbstractProvider):

    def __init__(self, name: str, responses: list[str | Exception]) -> None:
        super().__init__(model="mock-model")
        self._name = name
        self._responses = list(responses)
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._name

    def classify(self, prompt: str) -> str:
        self.call_count += 1
        if not self._responses:
            raise ProviderError("No responses left in mock", provider=self._name)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class TestAIClassifier:

    def test_tier0_exact_match_returns_tier0_sentinel(self) -> None:
        classifier = AIClassifier()
        res = classifier.classify("open chrome")
        assert res.tier == 0
        assert res.intent == "unknown"

    def test_empty_input_returns_tier0_unknown(self) -> None:
        classifier = AIClassifier()
        res = classifier.classify("")
        assert res.intent == "unknown"
        assert res.confidence == 0.0

    def test_tier1_dispatch_success(self) -> None:
        mock_ollama = MockProvider(
            "ollama",
            ['{"intent": "open_app", "target": "edge", "confidence": 0.94}'],
        )
        classifier = AIClassifier(tier1_provider=mock_ollama)
        res = classifier.classify("launch edge for me please")
        assert res.intent == "open_app"
        assert res.target == "edge"
        assert res.confidence == 0.94
        assert res.tier == 1
        assert mock_ollama.call_count == 1

    def test_tier2_dispatch_success_with_pii_scrubbing(self) -> None:
        mock_nebius = MockProvider(
            "nebius",
            ['{"intent": "unknown", "confidence": 0.0}'],
        )
        classifier = AIClassifier(tier2_provider=mock_nebius)
        res = classifier.classify("plan a workflow to analyze system architecture")
        assert res.tier == 2
        assert mock_nebius.call_count == 1

    def test_sensitive_input_never_sent_to_tier2(self) -> None:
        mock_ollama = MockProvider(
            "ollama",
            ['{"intent": "delete_file", "target": "secret.txt", "confidence": 0.9}'],
        )
        mock_nebius = MockProvider("nebius", [])

        classifier = AIClassifier(tier1_provider=mock_ollama, tier2_provider=mock_nebius)
        # Even with complex planning keywords, a sensitive file/path triggers the AI Ethics gate
        res = classifier.classify("plan to delete file C:/Users/alice/Documents/secret.txt")
        assert res.tier == 1
        assert mock_ollama.call_count == 1
        assert mock_nebius.call_count == 0  # Nebius MUST NOT have been called!

    def test_recoverable_error_retries_and_succeeds(self) -> None:
        mock_ollama = MockProvider(
            "ollama",
            [
                ProviderError("Timeout", recoverable=True),
                '{"intent": "greet", "confidence": 0.95}',
            ],
        )
        classifier = AIClassifier(tier1_provider=mock_ollama)
        res = classifier.classify("good morning")
        assert res.intent == "greet"
        assert res.confidence == 0.95
        assert mock_ollama.call_count == 2

    def test_non_recoverable_error_fails_closed_without_retry(self) -> None:
        mock_ollama = MockProvider(
            "ollama",
            [ProviderError("Missing Key", recoverable=False)],
        )
        classifier = AIClassifier(tier1_provider=mock_ollama)
        res = classifier.classify("good morning")
        assert res.intent == "unknown"
        assert res.confidence == 0.0
        assert mock_ollama.call_count == 1  # Did not retry

    def test_invalid_json_fails_closed_after_retries(self) -> None:
        mock_ollama = MockProvider(
            "ollama",
            ["Not json at all", "Still not json"],
        )
        classifier = AIClassifier(tier1_provider=mock_ollama)
        res = classifier.classify("launch something")
        assert res.intent == "unknown"
        assert res.confidence == 0.0
        assert mock_ollama.call_count == 2

    def test_lazy_provider_initialization_from_config(self, tmp_path: Path) -> None:
        config_file = tmp_path / "ai_config.json"
        config_file.write_text(
            json.dumps(
                {
                    "tier1": {"provider": "ollama", "model": "test-ollama", "timeout_s": 5.0},
                    "tier2": {
                        "provider": "nebius",
                        "model": "test-nebius",
                        "timeout_s": 15.0,
                    },
                }
            ),
            encoding="utf-8",
        )
        classifier = AIClassifier(config_path=config_file)
        p1 = classifier.get_tier1_provider()
        assert isinstance(p1, OllamaProvider)
        assert p1.model == "test-ollama"
        assert p1.timeout_s == 5.0

        p2 = classifier.get_tier2_provider()
        assert isinstance(p2, NebiusProvider)
        assert p2.model == "test-nebius"
        assert p2.timeout_s == 15.0


# ===========================================================================
# 10. Provider Network & Error Edge Cases
# ===========================================================================


class TestProviderEdgeCases:

    @patch("requests.post")
    def test_nebius_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        provider = NebiusProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is True

    @patch("requests.post")
    def test_nebius_connection_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError("conn")
        provider = NebiusProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is True

    @patch("requests.post")
    def test_nebius_empty_choices(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"choices": []}
        provider = NebiusProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert "no choices" in exc_info.value.message

    @patch("requests.post")
    def test_openai_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        provider = OpenAIProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is True

    @patch("requests.post")
    def test_openai_connection_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError("conn")
        provider = OpenAIProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is True

    @patch("requests.post")
    def test_openai_empty_choices(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"choices": []}
        provider = OpenAIProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert "no choices" in exc_info.value.message

    @patch("requests.post")
    def test_gemini_timeout(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.Timeout("timeout")
        provider = GeminiProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is True

    @patch("requests.post")
    def test_gemini_connection_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.exceptions.ConnectionError("conn")
        provider = GeminiProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is True

    @patch("requests.post")
    def test_gemini_empty_candidates(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"candidates": []}
        provider = GeminiProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert "no candidates" in exc_info.value.message

    @patch("requests.post")
    def test_gemini_empty_parts(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "candidates": [{"content": {"parts": []}}]
        }
        provider = GeminiProvider(api_key="key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert "no parts" in exc_info.value.message

    @patch("requests.post")
    def test_gemini_http_400_invalid_key_non_recoverable(self, mock_post: MagicMock) -> None:
        mock_post.return_value.status_code = 400
        mock_post.return_value.text = "API_KEY_INVALID"
        provider = GeminiProvider(api_key="bad-key")
        with pytest.raises(ProviderError) as exc_info:
            provider.classify("hi")
        assert exc_info.value.recoverable is False


# ===========================================================================
# 11. AI Package __getattr__ Dynamic Exports Tests
# ===========================================================================


class TestAiPackageExports:

    def test_dynamic_exports(self) -> None:
        import ai

        assert ai.AIClassifier is not None
        assert ai.PromptBuilder is not None
        assert ai.TriageRouter is not None
        assert ai.Sensitivity is not None
        assert ai.TriageDecision is not None

    def test_unknown_export_raises_attribute_error(self) -> None:
        import ai

        with pytest.raises(AttributeError, match="has no attribute 'NonExistent'"):
            _ = ai.NonExistent
