from langchain_groq import ChatGroq
from langchain_core.language_models import BaseChatModel

from .provider import LLMProviderBase, LLMProviderFactory


@LLMProviderFactory.register("groq")
class GroqProvider(LLMProviderBase):

    def get_chat_model(self) -> BaseChatModel:
        return ChatGroq(
            model=self.model_id,
            api_key=self.api_key,
            temperature=self.config.get("temperature", 0.1),
            max_tokens=self.config.get("max_tokens", 4096),
            timeout=self.config.get("request_timeout", 30),
            max_retries=self.config.get("max_retries", 1),
        )
