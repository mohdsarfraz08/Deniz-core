"""ai/providers/base_provider.py — Abstract provider contract and exceptions.

Milestone 10.2 — Core Engine Module Member

Defines the base abstraction for all LLM providers in the Phase 10 AI Foundation
Layer. All concrete providers (Nebius, Ollama, OpenAI, Gemini) must inherit from
AbstractProvider and raise ProviderError on failures.
"""

from __future__ import annotations

import abc
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when an LLM provider encounters a network, auth, or execution error.

    Callers should inspect ``recoverable`` to determine whether retry logic or
    fallback to an alternative tier is appropriate:
      - ``recoverable=True``: Network timeouts, 429 rate limits, transient connection drops.
      - ``recoverable=False``: Missing API keys, 401/403 authentication failures,
        invalid model identifiers. Immediate fail-closed is required.

    Attributes:
        message: Human-readable error description.
        provider: Name of the provider raising the error (e.g., "nebius", "ollama").
        recoverable: Whether the failure may succeed on retry or fallback.
        status_code: HTTP status code if applicable.
        raw_response: Raw response body received, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str = "",
        recoverable: bool = True,
        status_code: int | None = None,
        raw_response: str = "",
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.provider: str = provider
        self.recoverable: bool = recoverable
        self.status_code: int | None = status_code
        self.raw_response: str = raw_response

    def __repr__(self) -> str:
        return (
            f"ProviderError({self.message!r}, provider={self.provider!r}, "
            f"recoverable={self.recoverable}, status_code={self.status_code})"
        )


class AbstractProvider(abc.ABC):
    """Abstract Base Class for LLM providers.

    All providers must implement ``classify`` which takes a prompt string and
    returns raw response text. Providers do not perform JSON parsing or
    schema validation — that is the responsibility of ``validate_intent_result``.

    Args:
        model: Model identifier or tag.
        timeout_s: Request timeout in seconds.
    """

    def __init__(self, model: str, timeout_s: float = 30.0, **kwargs: Any) -> None:
        self._model: str = model
        self._timeout_s: float = timeout_s

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier for this provider (e.g., 'nebius', 'ollama')."""

    @property
    def model(self) -> str:
        """Active model name or identifier."""
        return self._model

    @property
    def timeout_s(self) -> float:
        """Configured timeout in seconds."""
        return self._timeout_s

    @abc.abstractmethod
    def classify(self, prompt: str) -> str:
        """Send prompt to LLM and return raw response text.

        Args:
            prompt: Text prompt to send to the provider.

        Returns:
            Raw response text from the model.

        Raises:
            ProviderError: On network failures, timeouts, auth errors, or API rejections.
        """

    def is_available(self) -> bool:
        """Check whether the provider is configured and available for requests.

        Default implementation returns True; subclasses should verify API keys
        or local daemon connectivity.
        """
        return True
