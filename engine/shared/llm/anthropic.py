from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

from .provider import LLMProviderBase, LLMProviderFactory


@LLMProviderFactory.register("anthropic")
class AnthropicProvider(LLMProviderBase):

    def get_chat_model(self) -> BaseChatModel:
        return ChatAnthropic(
            model=self.model_id,
            anthropic_api_key=self.api_key,
            temperature=self.config.get("temperature", 0.1),
            max_tokens=self.config.get("max_tokens", 4096),
        )
