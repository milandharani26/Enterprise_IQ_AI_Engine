from typing import Dict, List, Type

from engine.modules.assistant.tools.base_tool import BaseTool
from engine.modules.assistant.tools.implementations.emit_ui_blocks import EmitUIBlocksTool
from engine.modules.assistant.tools.implementations.rag_search import RAGSearchTool
from engine.modules.assistant.tools.implementations.sql_query import SqlQueryTool


class ToolRegistryNew:
    _registry: Dict[str, Type[BaseTool]] = {}

    @classmethod
    def register_tool(cls, tool_cls: Type[BaseTool]):
        instance = tool_cls()
        cls._registry[instance.name] = tool_cls

    @classmethod
    def get_tool(cls, name: str) -> Type[BaseTool]:
        if name not in cls._registry:
            raise ValueError(f"Tool not found: {name}")
        return cls._registry[name]

    @classmethod
    def get_tools(cls, names: List[str]) -> List[Type[BaseTool]]:
        return [cls.get_tool(name) for name in names if name in cls._registry]

    @classmethod
    def get_available_tools(cls) -> List[Type[BaseTool]]:
        return list(cls._registry.values())


ToolRegistryNew.register_tool(EmitUIBlocksTool)
ToolRegistryNew.register_tool(RAGSearchTool)
ToolRegistryNew.register_tool(SqlQueryTool)
