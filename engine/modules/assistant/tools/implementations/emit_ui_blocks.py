"""UI blocks formatting tool for response rendering."""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from engine.modules.assistant.schemas.output_schema import UIBlock
from engine.modules.assistant.tools.base_tool import (
    BaseTool,
    ToolContext,
    ToolCategory,
    ToolProperties,
)

logger = logging.getLogger(__name__)


class EmitUIBlocksToolInput(BaseModel):
    blocks: Optional[List[UIBlock]] = None


class EmitUIBlocksTool(BaseTool):
    name = "emit_ui_blocks"
    return_direct = True
    properties = ToolProperties(
        description=(
            "Final response formatter. REQUIRED on every turn. "
            "Emit one or more UI blocks (markdown, table, chart) to render the assistant response."
        ),
        category=ToolCategory.PRESENTATION,
        input_schema=EmitUIBlocksToolInput,
        default_instructions=(
            "Call emit_ui_blocks exactly once per response with structured blocks. "
            "Use markdown blocks for text answers. "
            "Use table blocks for lists or multi-column data — provide columns as a list of strings "
            "and rows as a list of lists."
        ),
    )

    def get_instruction(self) -> str:
        return (
            self._usage_instructions
            or self.properties.default_instructions
            or self.properties.description
        )

    def _run(
        self,
        blocks: Optional[List[Union[UIBlock, Dict[str, Any]]]] = None,
        ctx: Optional[ToolContext] = None,
    ) -> str:
        try:
            block_dicts = []
            for block in blocks or []:
                # FIX: LLM sometimes passes raw dicts instead of UIBlock instances.
                # model_dump() only exists on Pydantic models — handle both cases.
                if isinstance(block, dict):
                    block_dicts.append(block)
                elif hasattr(block, "model_dump"):
                    block_dicts.append(block.model_dump())
                else:
                    # Last resort: try to serialise whatever we got
                    block_dicts.append(dict(block))
            return json.dumps({"blocks": block_dicts})
        except Exception as e:
            logger.error("[EmitUIBlocksTool] Error: %s", e)
            return json.dumps({"error": f"UI blocks failed: {str(e)}"})

    async def _arun(
        self,
        blocks: Optional[List[Union[UIBlock, Dict[str, Any]]]] = None,
        ctx: Optional[ToolContext] = None,
    ) -> str:
        # FIX: provide async version directly so we avoid asyncio.to_thread overhead
        # and the ctx kwarg mismatch risk in the base class fallback.
        return self._run(blocks=blocks, ctx=ctx)
