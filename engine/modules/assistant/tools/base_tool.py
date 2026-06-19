from enum import Enum
from typing import Any, Dict, List, Optional, Type

from langchain_community.tools import StructuredTool
from pydantic import BaseModel

from engine.shared.config import get_settings


class ToolCategory(str, Enum):
    BUSINESS = "business"
    PRESENTATION = "presentation"


class ToolContext(BaseModel):
    """Runtime context passed to assistant tools during chat."""
    organization_id: Optional[str] = None
    conversation_id: str
    assistant_id: str
    user_id: str
    has_attachments: bool = False
    created_by: Optional[str] = None
    attachment_ids: Optional[List[str]] = None
    guardrails: Optional[str] = None


class ToolProperties(BaseModel):
    description: str
    default_instructions: Optional[str] = None
    category: ToolCategory
    connectors: Optional[Dict[str, Any]] = {}
    input_schema: Type[BaseModel]
    required_connectors: Optional[List[str]] = None
    required_permissions: Optional[List[str]] = None
    risk_level: str = "low"


class BaseTool:
    settings = get_settings()
    name: str = ""
    properties: ToolProperties = None  # type: ignore

    def __init__(
        self,
        config: Dict[str, Any] = None,
        credential_id: Optional[str] = None,
        usage_instructions: Optional[str] = None,
    ):
        self._config = config or {}
        self._credential_id = credential_id
        self._usage_instructions = usage_instructions

    def get_instruction(self) -> str:
        return (
            self._usage_instructions
            or self.properties.default_instructions
            or self.properties.description
        )

    def _run(self, ctx: ToolContext, **kwargs) -> Any:
        raise NotImplementedError

    async def _arun(self, ctx: ToolContext, **kwargs) -> Any:
        raise NotImplementedError

    def as_langchain_tool(self, ctx: ToolContext) -> StructuredTool:
        def run(**kwargs):
            result = self._run(ctx=ctx, **kwargs)
            return result if isinstance(result, str) else str(result)

        async def arun(**kwargs):
            result = await self._arun(ctx=ctx, **kwargs)
            return result if isinstance(result, str) else str(result)

        return StructuredTool.from_function(
            name=self.name,
            description=self.properties.description,
            func=run,
            coroutine=arun,
            args_schema=self.properties.input_schema,
        )
