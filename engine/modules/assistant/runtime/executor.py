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
from engine.modules.assistant.runtime.sql_context import (
    assistant_has_sql_tool,
    enrich_config_for_sql,
)
from engine.modules.assistant.tools.base_tool import ToolContext
from engine.modules.assistant.tools.exceptions import SecurityGuardrailError

logger = logging.getLogger(__name__)

# Ensure assistant types are registered even if startup hook did not run yet.
AssistantFactory.register_types()


def _fix_markdown_links(text: str) -> str:
    """Fixes broken markdown links where LLMs insert newlines between brackets and parens."""
    if not text or not isinstance(text, str):
        return text
    return re.sub(r"\]\s+\(\s*(https?://)", r"](\1", text)


def _extract_response_text(result: dict) -> str:
    messages = result.get("messages") or []
    if not messages:
        return str(result.get("final_output", "No response generated"))

    # 1. Prefer the last AIMessage with non-empty text content.
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

    # 2. emit_ui_blocks ToolMessage — extract markdown block text.
    for msg in reversed(messages):
        if (
            isinstance(msg, ToolMessage)
            and getattr(msg, "name", "") == "emit_ui_blocks"
        ):
            try:
                parsed = json.loads(msg.content or "")
                for block in parsed.get("blocks") or []:
                    if block.get("type") == "markdown" and block.get("data", {}).get(
                        "content"
                    ):
                        return _fix_markdown_links(block["data"]["content"])
            except (json.JSONDecodeError, TypeError):
                pass
                
    # Also check AIMessage tool_calls in case return_direct stopped execution before ToolMessage was appended
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        for call in tool_calls:
            if call.get("name") == "emit_ui_blocks":
                args = call.get("args") or {}
                blocks = args.get("blocks") or []
                for block in blocks:
                    if block.get("type") == "markdown" and block.get("data", {}).get("content"):
                        return _fix_markdown_links(block["data"]["content"])

    # 3. FIX: Fallback — read sql_query ToolMessage directly.
    #    This fires when the LLM calls sql_query but fails to follow up with
    #    emit_ui_blocks or a non-empty AIMessage, causing "No response generated".
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage) and getattr(msg, "name", "") == "sql_query":
            content = str(getattr(msg, "content", "") or "").strip()
            if content:
                logger.warning(
                    "LLM did not produce a final AIMessage after sql_query — "
                    "returning tool result directly. Check that the agent loops "
                    "back to the LLM after tool execution."
                )
                return _fix_markdown_links(content)

    # 4. Last resort: any non-empty ToolMessage.
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            content = str(getattr(msg, "content", "") or "").strip()
            if content:
                return _fix_markdown_links(content)

    return "No response generated"


def _extract_content_blocks(result: dict, fallback_text: str) -> list:
    messages = result.get("messages") or []

    # 1. emit_ui_blocks ToolMessage.
    for msg in reversed(messages):
        if (
            isinstance(msg, ToolMessage)
            and getattr(msg, "name", "") == "emit_ui_blocks"
        ):
            try:
                parsed = json.loads(msg.content or "")
                blocks = parsed.get("blocks")
                if blocks:
                    for b in blocks:
                        if b.get("type") == "markdown" and "content" in b.get(
                            "data", {}
                        ):
                            b["data"]["content"] = _fix_markdown_links(
                                b["data"]["content"]
                            )
                    return blocks
            except (json.JSONDecodeError, TypeError):
                pass

    # 2. emit_ui_blocks in AIMessage tool_calls args.
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
                        if b.get("type") == "markdown" and "content" in b.get(
                            "data", {}
                        ):
                            b["data"]["content"] = _fix_markdown_links(
                                b["data"]["content"]
                            )
                    return blocks

    # 3. JSON blocks embedded in content string.
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str) and content.strip().startswith("{"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and parsed.get("blocks"):
                    blocks = parsed["blocks"]
                    for b in blocks:
                        if b.get("type") == "markdown" and "content" in b.get(
                            "data", {}
                        ):
                            b["data"]["content"] = _fix_markdown_links(
                                b["data"]["content"]
                            )
                    return blocks
            except json.JSONDecodeError:
                pass

    # 4. FIX: If fallback_text came from sql_query tool result, wrap it in a
    #    markdown block so the UI renders it instead of showing nothing.
    return [
        {
            "type": "markdown",
            "data": {"content": fallback_text or "No response generated."},
        }
    ]


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
        logger.info(f"Executor called for query: {query}")
        organization_id = str(organization_ids[0]) if organization_ids else None
        config_dict = assistant_row_to_config_dict(assistant)

        if assistant_has_rag_tool(config_dict):
            inventory = await fetch_indexed_document_inventory(organization_id)
            config_dict = enrich_config_for_rag(config_dict, inventory)

        if assistant_has_sql_tool(config_dict):
            config_dict = enrich_config_for_sql(config_dict)

        # Extract and format guardrails
        guardrails_list = config_dict.get("guardrails", [])
        guardrails_str = ""
        if guardrails_list:
            guardrails_str = "\n".join(
                [
                    f"- {g.get('type')}: {g.get('instructions')}"
                    for g in guardrails_list
                    if g.get("is_enabled", True)
                ]
            )

        context = ToolContext(
            organization_id=organization_id,
            conversation_id=conversation_id,
            assistant_id=assistant_id,
            user_id=user_id,
            guardrails=guardrails_str,
        )

        if assistant_has_drive_tool(config_dict):
            drive_inventory = await fetch_drive_document_inventory(organization_id)
            config_dict = enrich_config_for_drive(config_dict, drive_inventory)

        assistant_instance = AssistantFactory.get_assistant(config=config_dict)
        agent, _system_instruction, _tools = assistant_instance.build_graph(
            config_dict, ctx=context
        )

        try:
            result = await assistant_instance.invoke(
                agent,
                query,
                session_id,
            )
        except SecurityGuardrailError as e:
            logger.warning("Agent execution short-circuited due to security guardrail.")
            static_msg = str(e)
            return static_msg, [{"type": "markdown", "data": {"content": static_msg}}]
        except Exception as e:
            logger.exception("AGENT INVOCATION FAILED")
            raise

        # Debug: log all messages to help trace issues
        for i, msg in enumerate(result.get("messages", [])):
            logger.debug(
                f"[msg {i}] {type(msg).__name__} name={getattr(msg, 'name', '-')} "
                f"content={str(getattr(msg, 'content', ''))[:200]}"
            )

        response_text = _extract_response_text(result)
        content_blocks = _extract_content_blocks(result, response_text)
        return response_text, content_blocks
