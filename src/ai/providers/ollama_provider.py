"""ai/providers/ollama_provider.py — Local edge provider via Ollama.

Milestone 10.3a — OS Adapters Module Member

Connects to a local Ollama instance running on localhost (Tier 1).
Data never leaves the device. Ideal for fast basic commands and sensitive
operations (file manipulation, local paths).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from ai.providers.base_provider import AbstractProvider, ProviderError

logger = logging.getLogger(__name__)


class OllamaProvider(AbstractProvider):
    """Tier 1 Local Edge Engine provider communicating with Ollama.

    Args:
        model: Ollama model tag (default: 'llama3.2').
        host: Base URL of local Ollama daemon (default: 'http://127.0.0.1:11434').
        timeout_s: HTTP request timeout in seconds (default: 10.0).
    """

    DEFAULT_HOST = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        host: str = DEFAULT_HOST,
        timeout_s: float = 10.0,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, timeout_s=timeout_s, **kwargs)
        self._host = host.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def host(self) -> str:
        return self._host

    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable."""
        try:
            resp = requests.get(f"{self._host}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def classify(self, prompt: str) -> str:
        """Send prompt to local Ollama daemon and return raw text.

        Enforces json formatting mode in Ollama request payload.

        Args:
            prompt: Text prompt to classify.

        Returns:
            Raw response text from model.

        Raises:
            ProviderError: If Ollama is unreachable, times out, or returns an error.
        """
        endpoint = f"{self._host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }

        try:
            logger.debug("Dispatching request to Ollama at %s (model: %s)", endpoint, self.model)
            response = requests.post(
                endpoint,
                json=payload,
                timeout=self.timeout_s,
            )
        except requests.exceptions.Timeout as exc:
            raise ProviderError(
                f"Ollama request timed out after {self.timeout_s}s",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderError(
                f"Failed to connect to Ollama daemon at {self._host}. Is Ollama running?",
                provider=self.provider_name,
                recoverable=True,
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderError(
                f"Ollama HTTP request failed: {exc}",
                provider=self.provider_name,
                recoverable=True,
            ) from exc

        if response.status_code != 200:
            recoverable = response.status_code >= 500 or response.status_code == 429
            raise ProviderError(
                f"Ollama returned HTTP status {response.status_code}: {response.text}",
                provider=self.provider_name,
                recoverable=recoverable,
                status_code=response.status_code,
                raw_response=response.text,
            )

        try:
            data = response.json()
            raw_text = data.get("response", "")
            if not isinstance(raw_text, str):
                raw_text = json.dumps(raw_text)
            return raw_text.strip()
        except Exception as exc:
            raise ProviderError(
                f"Failed to parse Ollama response body as JSON: {exc}",
                provider=self.provider_name,
                recoverable=False,
                raw_response=response.text,
            ) from exc
