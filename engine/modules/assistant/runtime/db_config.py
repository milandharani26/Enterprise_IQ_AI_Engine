"""Map persisted Assistant rows to runtime config dicts."""

from __future__ import annotations

from typing import Any, Dict

from engine.modules.assistant.assistant_models import Assistant
from engine.modules.assistant.runtime.rag_context import RAG_DOCUMENT_ASSISTANT_PROMPT
from engine.shared.config.settings import get_settings

_TOOL_KEYS = frozenset(
    {"tool_id", "credential_key", "credential_id", "config", "usage_instructions"}
)
_GUARDRAIL_KEYS = frozenset({"type", "instructions", "enforcement", "is_enabled"})


def _normalize_tools(raw: Any) -> list[dict[str, Any]]:
    if not raw or not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for t in raw:
        if not isinstance(t, dict):
            continue
        cleaned = {k: t[k] for k in _TOOL_KEYS if k in t}
        if cleaned.get("tool_id"):
            out.append(cleaned)
    return out


def _normalize_guardrails(raw: Any) -> list[dict[str, Any]]:
    if not raw or not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for g in raw:
        if not isinstance(g, dict):
            continue
        cleaned = {k: g[k] for k in _GUARDRAIL_KEYS if k in g}
        if cleaned.get("type") and cleaned.get("instructions"):
            if "enforcement" not in cleaned:
                cleaned["enforcement"] = "moderate"
            out.append(cleaned)
    return out


def _build_llm_config(tools: list[dict[str, Any]] | None = None) -> Dict[str, Any]:
    settings = get_settings()
    max_tokens = int(settings.default_llm_max_tokens)
    # RAG agents need multiple LLM turns (tool call + answer); 512 is too low.
    if any(t.get("tool_id") == "rag_search" for t in (tools or [])):
        max_tokens = max(max_tokens, 2048)
    return {
        "provider": settings.default_llm_provider,
        "model": settings.default_llm_model,
        "temperature": float(settings.default_llm_temperature),
        "max_tokens": max_tokens,
    }


def assistant_row_to_config_dict(assistant: Assistant) -> Dict[str, Any]:
    tools = _normalize_tools(assistant.tools)
    instruction = (assistant.system_prompt or "").strip()
    if not instruction:
        instruction = (
            RAG_DOCUMENT_ASSISTANT_PROMPT.strip()
            if any(t.get("tool_id") == "rag_search" for t in tools)
            else "You are a helpful assistant."
        )
    cfg: Dict[str, Any] = {
        "assistant_id": str(assistant.assistant_id),
        "name": assistant.assistant_name,
        "assistant_code": assistant.assistant_code,
        "description": assistant.description or "",
        "category": assistant.category,
        "type": assistant.type,
        "status": assistant.status,
        "system_instruction": instruction,
        "llm_config": _build_llm_config(tools),
        "tools": tools,
    }
    gr = _normalize_guardrails(assistant.guardrails)
    if gr:
        cfg["guardrails"] = gr
    return cfg
