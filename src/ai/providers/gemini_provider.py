"""ai/providers/gemini_provider.py — Google Gemini cloud fallback provider.

Milestone 10.3d — OS Adapters Module Member

Connects to the Google Gemini REST API (generateContent) for cloud classification.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from ai.providers.base_provider import AbstractProvider, ProviderError

logger = logging.getLogger(__name__)


class GeminiProvider(AbstractProvider):
    """Google Gemini cloud fallback provider.

    Authentication:
        Set GEMINI_API_KEY environment variable. Never log or commit the key.

    Args:
        model: Gemini model identifier (default: 'gemini-1.5-flash').
        timeout_s: HTTP request timeout in seconds.
        api_key: Optional explicit API key; defaults to GEMINI_API_KEY env var.
    """

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        timeout_s: float = 30.0,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, timeout_s=timeout_s, **kwargs)
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        """Check if Gemini API key is provisioned."""
        return bool(self._api_key)

    def classify(self, prompt: str) -> str:
        """Send prompt to Gemini generateContent endpoint.

        Args:
            prompt: Text prompt to classify.

        Returns:
            Raw response text from Gemini.

        Raises:
            ProviderError: On missing key, network error, or API rejection.
        """
        if not self._api_key:
            raise ProviderError(
                "GEMINI_API_KEY environment variable is not set.",
                provider=self.provider_name,
                recoverable=False,
            )

        endpoint = f"{self._base_url}/models/{self.model}:generateContent?key={self._api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
            },
        }

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout_s,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderError(
                f"Gemini request timed out after {self.timeout_s}s",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderError(
                "Failed to connect to Google Gemini API",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderError(
                f"Gemini HTTP request error: {exc}",
                provider=self.provider_name,
                recoverable=True,
            ) from exc

        if response.status_code != 200:
            recoverable = response.status_code >= 500 or response.status_code == 429
            if response.status_code in (400, 401, 403):
                # 400 with invalid API key or 401/403
                recoverable = False
            raise ProviderError(
                f"Gemini API returned HTTP status {response.status_code}: {response.text}",
                provider=self.provider_name,
                recoverable=recoverable,
                status_code=response.status_code,
                raw_response=response.text,
            )

        try:
            body = response.json()
            candidates = body.get("candidates", [])
            if not candidates:
                raise ProviderError(
                    "Gemini response contains no candidates",
                    provider=self.provider_name,
                    recoverable=False,
                    raw_response=response.text,
                )
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ProviderError(
                    "Gemini candidate contains no parts",
                    provider=self.provider_name,
                    recoverable=False,
                    raw_response=response.text,
                )
            text = parts[0].get("text", "")
            return text.strip()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Failed to parse Gemini response body: {exc}",
                provider=self.provider_name,
                recoverable=False,
                raw_response=response.text,
            ) from exc
