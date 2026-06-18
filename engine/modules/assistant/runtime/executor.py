"""Assistant graph execution orchestrator."""

import asyncio
import json
import logging
import re
from typing import List, Tuple

from langchain_core.messages import AIMessage, ToolMessage

from engine.modules.assistant.assistant_models import Assistant
from engine.modules.assistant.runtime.assistant_factory import AssistantFactory
from engine.modules.assistant.runtime.db_config import assistant_row_to_config_dict
from engine.modules.assistant.runtime.rag_context import (
    assistant_has_rag_tool,
    enrich_config_for_rag,
    fetch_indexed_document_inventory,
)
from engine.modules.assistant.runtime.drive_context import (
    assistant_has_drive_tool,
    enrich_config_for_drive,
    fetch_drive_document_inventory,
)
from engine.modules.assistant.tools.base_tool import ToolContext

logger = logging.getLogger(__name__)

# Ensure assistant types are registered even if startup hook did not run yet.
AssistantFactory.register_types()


def _fix_markdown_links(text: str) -> str:
    """Fixes broken markdown links where LLMs insert newlines between brackets and parens."""
    if not text or not isinstance(text, str):
        return text
    # Match any whitespace (space, newline, etc) between ] and (
    return re.sub(r'\]\s+\(\s*(https?://)', r'](\1', text)


def _extract_response_text(result: dict) -> str:
    messages = result.get("messages") or []
    if not messages:
        return str(result.get("final_output", "No response generated"))

    # Prefer the last AIMessage with non-empty text (final turn may be empty after tool calls).
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            text = "\n".join(p for p in parts if p).strip()
        else:
            text = str(content or "").strip()
        if text:
            return _fix_markdown_links(text)

    # emit_ui_blocks returns JSON in a ToolMessage
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", "") == "emit_ui_blocks":
            try:
                parsed = json.loads(msg.content or "")
                for block in parsed.get("blocks") or []:
                    if block.get("type") == "markdown" and block.get("data", {}).get("content"):
                        return _fix_markdown_links(block["data"]["content"])
            except (json.JSONDecodeError, TypeError):
                pass

    return "No response generated"


def _extract_content_blocks(result: dict, fallback_text: str) -> list:
    messages = result.get("messages") or []

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", "") == "emit_ui_blocks":
            try:
                parsed = json.loads(msg.content or "")
                blocks = parsed.get("blocks")
                if blocks:
                    for b in blocks:
                        if b.get("type") == "markdown" and "content" in b.get("data", {}):
                            b["data"]["content"] = _fix_markdown_links(b["data"]["content"])
                    return blocks
            except (json.JSONDecodeError, TypeError):
                pass

    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        for call in tool_calls:
            if call.get("name") == "emit_ui_blocks":
                args = call.get("args") or {}
                blocks = args.get("blocks")
                if blocks:
                    for b in blocks:
                        if b.get("type") == "markdown" and "content" in b.get("data", {}):
                            b["data"]["content"] = _fix_markdown_links(b["data"]["content"])
                    return blocks

    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content.strip().startswith("{"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and parsed.get("blocks"):
                    blocks = parsed["blocks"]
                    for b in blocks:
                        if b.get("type") == "markdown" and "content" in b.get("data", {}):
                            b["data"]["content"] = _fix_markdown_links(b["data"]["content"])
                    return blocks
            except json.JSONDecodeError:
                pass

    return [{"type": "markdown", "data": {"content": fallback_text or "No response generated."}}]


class AssistantExecutor:
    async def execute(
        self,
        session_id: str,
        conversation_id: str,
        user_id: str,
        assistant_id: str,
        query: str,
        organization_ids: List[str],
        assistant: Assistant,
    ) -> Tuple[str, list]:
        organization_id = str(organization_ids[0]) if organization_ids else None
        context = ToolContext(
            organization_id=organization_id,
            conversation_id=conversation_id,
            assistant_id=assistant_id,
            user_id=user_id,
        )

        config_dict = assistant_row_to_config_dict(assistant)
        if assistant_has_rag_tool(config_dict):
            inventory = await fetch_indexed_document_inventory(organization_id)
            config_dict = enrich_config_for_rag(config_dict, inventory)

        if assistant_has_drive_tool(config_dict):
            drive_inventory = await fetch_drive_document_inventory(organization_id)
            config_dict = enrich_config_for_drive(config_dict, drive_inventory)

        assistant_instance = AssistantFactory.get_assistant(config=config_dict)
        agent, _system_instruction, _tools = assistant_instance.build_graph(
            config_dict, ctx=context
        )

        result = await asyncio.to_thread(
            assistant_instance.invoke, agent, query, session_id
        )
        response_text = _extract_response_text(result)
        content_blocks = _extract_content_blocks(result, response_text)
        return response_text, content_blocks
