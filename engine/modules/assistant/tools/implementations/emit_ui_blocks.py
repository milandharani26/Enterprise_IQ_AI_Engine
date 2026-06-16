"""UI blocks formatting tool for response rendering."""

import json
import logging
from typing import List, Optional

from pydantic import BaseModel

from engine.modules.assistant.schemas.output_schema import UIBlock
from engine.modules.assistant.tools.base_tool import BaseTool, ToolContext, ToolCategory, ToolProperties

logger = logging.getLogger(__name__)


class EmitUIBlocksToolInput(BaseModel):
    blocks: Optional[List[UIBlock]] = None


class EmitUIBlocksTool(BaseTool):
    name = "emit_ui_blocks"
    properties = ToolProperties(
        description=(
            "Final response formatter. REQUIRED on every turn. "
            "Emit one or more UI blocks (markdown, table, chart) to render the assistant response."
        ),
        category=ToolCategory.PRESENTATION,
        input_schema=EmitUIBlocksToolInput,
        default_instructions=(
            "Call emit_ui_blocks exactly once per response with structured blocks. "
            "Use markdown blocks for text answers."
        ),
    )

    def get_instruction(self) -> str:
        return (
            self._usage_instructions
            or self.properties.default_instructions
            or self.properties.description
        )

    def _run(self, blocks: Optional[List[UIBlock]] = None, ctx: Optional[ToolContext] = None) -> str:
        try:
            block_dicts = [block.model_dump() for block in (blocks or [])]
            return json.dumps({"blocks": block_dicts})
        except Exception as e:
            logger.error("[EmitUIBlocksTool] Error: %s", e)
            return json.dumps({"error": f"UI blocks failed: {str(e)}"})
