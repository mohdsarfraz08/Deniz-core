"""ai/providers/__init__.py — Provider package and factory.

Milestone 10.3e — OS Adapters Module Member

Exposes all concrete LLM providers and the get_provider() factory function.
"""

from __future__ import annotations

from typing import Any, Type

from ai.providers.base_provider import AbstractProvider, ProviderError
from ai.providers.gemini_provider import GeminiProvider
from ai.providers.nebius_provider import NebiusProvider
from ai.providers.ollama_provider import OllamaProvider
from ai.providers.openai_provider import OpenAIProvider

_PROVIDER_REGISTRY: dict[str, Type[AbstractProvider]] = {
    "nebius": NebiusProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def get_provider(provider_name: str, **kwargs: Any) -> AbstractProvider:
    """Factory function returning a configured AbstractProvider instance.

    Args:
        provider_name: Case-insensitive name of the provider
            ('nebius', 'ollama', 'openai', 'gemini').
        **kwargs: Configuration arguments forwarded to the provider constructor
            (e.g., model, timeout_s, host, api_key).

    Returns:
        An instantiated AbstractProvider subclass.

    Raises:
        ValueError: If provider_name is not recognized.
    """
    key = provider_name.strip().lower()
    provider_cls = _PROVIDER_REGISTRY.get(key)
    if provider_cls is None:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown provider {provider_name!r}. Supported providers: {supported}"
        )
    return provider_cls(**kwargs)


__all__ = [
    "AbstractProvider",
    "ProviderError",
    "NebiusProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "get_provider",
]
