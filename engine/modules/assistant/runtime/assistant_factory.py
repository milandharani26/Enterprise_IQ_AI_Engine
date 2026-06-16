"""Assistant factory for creating assistants from configuration."""

import logging
from typing import Any, Dict

from engine.modules.assistant.runtime.simple_reactive import SimpleReactiveType

logger = logging.getLogger(__name__)


class AssistantTypeRegistry:
    _types: Dict[str, type] = {}

    @classmethod
    def register(cls, type_id: str, type_class: type):
        cls._types[type_id] = type_class

    @classmethod
    def get_or_raise(cls, type_id: str) -> type:
        if type_id not in cls._types:
            raise KeyError(f"Assistant type '{type_id}' not registered")
        return cls._types[type_id]


class AssistantFactory:
    @classmethod
    def register_types(cls) -> None:
        AssistantTypeRegistry.register("simple_reactive", SimpleReactiveType)

    @classmethod
    def get_assistant(cls, config: Dict[str, Any]):
        assistant_type = config.get("type", "simple_reactive")
        type_class = AssistantTypeRegistry.get_or_raise(assistant_type)
        return type_class()
