"""
LLM Provider abstraction layer.

Provides a unified interface for all LLM providers (Anthropic, OpenAI, Google, Ollama).
Each provider returns a LangChain ChatModel that supports tool binding.
"""

from abc import ABC, abstractmethod
from typing import Any
from langchain_core.language_models import BaseChatModel
from engine.shared.config import get_settings



class LLMProviderBase(ABC):
    """Base class for LLM providers."""

    def __init__(self, model_id: str, api_key: str = "", config: dict[str, Any] | None = None):
        self.model_id = model_id
        self.api_key = api_key
        self.config = config or {}

    @abstractmethod
    def get_chat_model(self) -> BaseChatModel:
        """Returns a LangChain ChatModel instance with tool calling support."""
        ...

    def get_model_with_tools(self, tools: list) -> BaseChatModel:
        """Returns the chat model with tools bound."""
        model = self.get_chat_model()
        if tools:
            return model.bind_tools(tools)
        return model


class LLMProviderFactory:
    """Factory that creates the right LLM provider based on provider name."""

    _providers: dict[str, type[LLMProviderBase]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a provider class."""
        def wrapper(provider_cls: type[LLMProviderBase]):
            cls._providers[name] = provider_cls
            return provider_cls
        return wrapper

    @classmethod
    def create(
        cls,
        provider: str,
        model_id: str,
        api_key: str = "",
        config: dict[str, Any] | None = None,
    ) -> LLMProviderBase:
        """Create a provider instance."""
        if provider not in cls._providers:
            raise ValueError(
                f"Unknown LLM provider '{provider}'. "
                f"Available: {list(cls._providers.keys())}"
            )
        return cls._providers[provider](model_id=model_id, api_key=api_key, config=config)

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._providers.keys())


def get_llm(
    provider: str | None = None,
    model_id: str | None = None,
    config: dict[str, Any] | None = None,
) -> LLMProviderBase:
    """
    Convenience function to get an LLM provider using role's llm_config
    or falling back to platform defaults.
    """
    settings = get_settings()
    provider = (provider or settings.default_llm_provider).strip().lower()
    model_id = model_id or settings.default_llm_model

    # Resolve API key from settings
    api_key_map = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "google": settings.google_api_key,
        "groq": settings.groq_api_key,
        "ollama": "",  # Ollama doesn't need an API key
    }
    api_key = api_key_map.get(provider, "")

    return LLMProviderFactory.create(
        provider=provider,
        model_id=model_id,
        api_key=api_key,
        config=config,
    )
