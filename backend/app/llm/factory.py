"""LLM Factory — provider-agnostic LLM creation."""

from __future__ import annotations

import logging
from typing import Dict, Type

from app.config import get_settings
from app.llm.base import BaseLLMProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)

# Registry of available providers
_PROVIDERS: Dict[str, Type[BaseLLMProvider]] = {
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "claude": ClaudeProvider,
}


class LLMFactory:
    """Create LLM provider instances by name."""

    @staticmethod
    def create(
        provider: str | None = None,
        model: str | None = None,
    ) -> BaseLLMProvider:
        """Create and return an LLM provider instance.

        Parameters
        ----------
        provider : str | None
            Provider name ("openai", "gemini", "claude").
            Falls back to DEFAULT_LLM_PROVIDER from config.
        model : str | None
            Model identifier. Falls back to defaulting within the provider.

        Returns
        -------
        BaseLLMProvider
            Ready-to-use provider instance.
        """
        settings = get_settings()
        provider = provider or settings.default_llm_provider
        provider = provider.lower()

        if provider not in _PROVIDERS:
            available = ", ".join(_PROVIDERS.keys())
            raise ValueError(
                f"Unknown LLM provider '{provider}'. Available: {available}"
            )

        cls = _PROVIDERS[provider]
        instance = cls(model=model)
        logger.info("Created LLM provider: %s (model=%s)", provider, instance.model)
        return instance

    @staticmethod
    def available_providers() -> list[str]:
        """List registered provider names."""
        return list(_PROVIDERS.keys())

    @staticmethod
    def register(name: str, provider_cls: Type[BaseLLMProvider]) -> None:
        """Register a custom provider at runtime."""
        _PROVIDERS[name.lower()] = provider_cls
        logger.info("Registered custom LLM provider: %s", name)
