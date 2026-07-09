"""Utility module for LLM initialization."""

import logging
import os
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel

from engine.shared.config.settings import get_settings
from engine.shared.llm.provider import LLMProviderFactory
from engine.modules.assistant.tools.exceptions import LLMInitializationError

logger = logging.getLogger(__name__)


from uuid import UUID

def initialize_llm(llm_config: Optional[Dict[str, Any]] = None, org_id: Optional[UUID] = None) -> BaseChatModel:
    if llm_config is None:
        llm_config = {}

    settings = get_settings()
    provider = llm_config.get("provider", settings.default_llm_provider).lower()
    model_id = llm_config.get("model", settings.default_llm_model)
    temperature = llm_config.get("temperature", settings.default_llm_temperature)
    max_tokens = llm_config.get("max_tokens", settings.default_llm_max_tokens)

    api_key = ""
    if org_id:
        from engine.shared.services.credential_resolver import CredentialResolver
        config = CredentialResolver.get_llm_credential_sync(org_id, provider)
        api_key = config["api_key"]

    if not api_key:
        api_key_env_var = f"{provider.upper()}_API_KEY"
        api_key = os.getenv(api_key_env_var, "") or getattr(settings, f"{provider}_api_key", "")

    try:
        provider_instance = LLMProviderFactory.create(
            provider=provider,
            model_id=model_id,
            api_key=api_key,
            config={
                "temperature": temperature,
                "max_tokens": max_tokens,
                "request_timeout": settings.llm_request_timeout_seconds,
                "max_retries": settings.llm_max_retries,
            },
        )
        return provider_instance.get_chat_model()
    except Exception as e:
        raise LLMInitializationError(
            f"Failed to initialize LLM provider '{provider}': {e}",
            original_error=e,
            context={"provider": provider, "model": model_id},
        )
