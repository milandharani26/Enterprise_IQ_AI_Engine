from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel

from engine.shared.config import get_settings
from .provider import LLMProviderBase, LLMProviderFactory


@LLMProviderFactory.register("ollama")
class OllamaProvider(LLMProviderBase):

    def get_chat_model(self) -> BaseChatModel:
        settings = get_settings()
        return ChatOllama(
            model=self.model_id,
            base_url=self.config.get("base_url", settings.ollama_base_url),
            temperature=self.config.get("temperature", 0.1),
            num_predict=self.config.get("max_tokens", 4096),
        )
