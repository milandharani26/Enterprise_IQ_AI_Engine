from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from .provider import LLMProviderBase, LLMProviderFactory


@LLMProviderFactory.register("openai")
class OpenAIProvider(LLMProviderBase):

    def get_chat_model(self) -> BaseChatModel:
        return ChatOpenAI(
            model=self.model_id,
            api_key=self.api_key,
            temperature=self.config.get("temperature", 0.1),
            max_tokens=self.config.get("max_tokens", 4096),
        )
