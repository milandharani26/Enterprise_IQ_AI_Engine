from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from .provider import LLMProviderBase, LLMProviderFactory


@LLMProviderFactory.register("google")
class GoogleProvider(LLMProviderBase):

    def get_chat_model(self) -> BaseChatModel:
        return ChatGoogleGenerativeAI(
            model=self.model_id,
            google_api_key=self.api_key,
            temperature=self.config.get("temperature", 0.1),
            max_output_tokens=self.config.get("max_tokens", 4096),
        )
