"""ai/providers/nebius_provider.py — Nebius Token Factory provider.

Milestone 10.3b — OS Adapters Module Member

Connects to the Nebius Token Factory OpenAI-compatible API serving NVIDIA
Nemotron models (Tier 2 Cloud Specialist). Used for complex reasoning,
agentic workflows, and tool planning.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

from ai.providers.base_provider import AbstractProvider, ProviderError

logger = logging.getLogger(__name__)


class NebiusProvider(AbstractProvider):
    """Nebius Token Factory provider serving NVIDIA Nemotron models.

    Connects to the Nebius AI Studio OpenAI-compatible endpoint.
    Recommended models:
      - nvidia/llama-3.1-nemotron-70b-instruct (balanced, default)
      - nvidia/nemotron-3-nano-30b (fast, agentic)
      - nvidia/nemotron-3-super-120b (maximum reasoning)

    Authentication:
        Set NEBIUS_API_KEY environment variable. Never hardcode credentials.
        Never log or print the key.

    Args:
        model: Nemotron model identifier string.
        timeout_s: HTTP request timeout in seconds.
        api_key: Optional explicit API key; defaults to NEBIUS_API_KEY env var.
        base_url: Base endpoint URL.
    """

    DEFAULT_BASE_URL = "https://api.studio.nebius.com/v1"
    DEFAULT_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        timeout_s: float = 30.0,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, timeout_s=timeout_s, **kwargs)
        self._api_key = api_key or os.environ.get("NEBIUS_API_KEY")
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "nebius"

    @property
    def base_url(self) -> str:
        return self._base_url

    def is_available(self) -> bool:
        """Check if Nebius API key is provisioned."""
        return bool(self._api_key)

    def classify(self, prompt: str) -> str:
        """Send prompt to Nemotron via Nebius Token Factory.

        Returns raw response string (expected to be JSON).

        Args:
            prompt: Text prompt to send to the model.

        Returns:
            Raw response text from Nemotron.

        Raises:
            ProviderError: On missing credentials, auth failure, network drop, or API error.
        """
        if not self._api_key:
            raise ProviderError(
                "NEBIUS_API_KEY environment variable is not set.",
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
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.0,
        }

        try:
            logger.debug(
                "Sending request to Nebius Token Factory (model: %s, endpoint: %s)",
                self.model,
                endpoint,
            )
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_s,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderError(
                f"Nebius request timed out after {self.timeout_s}s",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderError(
                f"Failed to connect to Nebius API at {self._base_url}",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderError(
                f"Nebius HTTP request error: {exc}",
                provider=self.provider_name,
                recoverable=True,
            ) from exc

        if response.status_code != 200:
            recoverable = response.status_code >= 500 or response.status_code == 429
            if response.status_code in (401, 403):
                recoverable = False
            raise ProviderError(
                f"Nebius API returned HTTP status {response.status_code}: {response.text}",
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
                    "Nebius response contains no choices",
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
                f"Failed to parse Nebius response body: {exc}",
                provider=self.provider_name,
                recoverable=False,
                raw_response=response.text,
            ) from exc
