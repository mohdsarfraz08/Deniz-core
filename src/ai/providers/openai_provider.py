"""ai/providers/openai_provider.py — OpenAI cloud fallback provider.

Milestone 10.3c — OS Adapters Module Member

Connects to the OpenAI REST API for cloud classification fallback.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from ai.providers.base_provider import AbstractProvider, ProviderError

logger = logging.getLogger(__name__)


class OpenAIProvider(AbstractProvider):
    """OpenAI cloud fallback provider.

    Authentication:
        Set OPENAI_API_KEY environment variable. Never log or commit the key.

    Args:
        model: OpenAI model identifier (default: 'gpt-4o-mini').
        timeout_s: HTTP request timeout in seconds.
        api_key: Optional explicit API key; defaults to OPENAI_API_KEY env var.
        base_url: Base endpoint URL (default: 'https://api.openai.com/v1').
    """

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        timeout_s: float = 30.0,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, timeout_s=timeout_s, **kwargs)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_available(self) -> bool:
        """Check if OpenAI API key is provisioned."""
        return bool(self._api_key)

    def classify(self, prompt: str) -> str:
        """Send prompt to OpenAI chat completions API.

        Args:
            prompt: Text prompt to classify.

        Returns:
            Raw response text from the model.

        Raises:
            ProviderError: On missing key, network error, or API rejection.
        """
        if not self._api_key:
            raise ProviderError(
                "OPENAI_API_KEY environment variable is not set.",
                provider=self.provider_name,
                recoverable=False,
            )

        endpoint = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_s,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderError(
                f"OpenAI request timed out after {self.timeout_s}s",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderError(
                f"Failed to connect to OpenAI API at {self._base_url}",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderError(
                f"OpenAI HTTP request error: {exc}",
                provider=self.provider_name,
                recoverable=True,
            ) from exc

        if response.status_code != 200:
            recoverable = response.status_code >= 500 or response.status_code == 429
            if response.status_code in (401, 403):
                recoverable = False
            raise ProviderError(
                f"OpenAI API returned HTTP status {response.status_code}: {response.text}",
                provider=self.provider_name,
                recoverable=recoverable,
                status_code=response.status_code,
                raw_response=response.text,
            )

        try:
            body = response.json()
            choices = body.get("choices", [])
            if not choices:
                raise ProviderError(
                    "OpenAI response contains no choices",
                    provider=self.provider_name,
                    recoverable=False,
                    raw_response=response.text,
                )
            content = choices[0].get("message", {}).get("content", "")
            return content.strip()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Failed to parse OpenAI response body: {exc}",
                provider=self.provider_name,
                recoverable=False,
                raw_response=response.text,
            ) from exc
