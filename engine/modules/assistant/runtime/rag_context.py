"""RAG prompt helpers: document inventory and instruction enrichment."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union
from uuid import UUID

from sqlalchemy import func, select

logger = logging.getLogger(__name__)

# Note: knowledge.documents.workspace_id stores the organization_id from the API.

RAG_DOCUMENT_ASSISTANT_PROMPT = """You are a document assistant for this organization.

Rules:
- Answer document questions using rag_search over knowledge.document_chunks.
- Do not invent content — only use search results and the indexed document list below.
- For inventory questions, list document titles from INDEXED DOCUMENTS and summarize via rag_search.
- Cite source titles inline (e.g. *Source: filename.pdf*).
- If search returns nothing, do NOT immediately give up. You MUST try your other available search tools (like drive_search or sql_query) before concluding the information is missing. Only suggest uploading files if ALL relevant search tools fail.
"""

RAG_WORKFLOW_INSTRUCTIONS = """
## DOCUMENT RAG WORKFLOW (required when rag_search is available)

1. Call **rag_search** before answering any question about uploaded files, PDFs, policies, summaries, or document lists.
2. Use the user's question as the search query (rephrase if needed for clarity).
3. For "what documents do you have": list titles from INDEXED DOCUMENTS, then rag_search for summaries.
4. Answer only from search excerpts. Do not use outside knowledge for document facts.
5. Format the answer directly in markdown.
6. If rag_search yields no results, you must proceed to try other search tools before giving up.
"""


def assistant_has_rag_tool(config_dict: Dict[str, Any]) -> bool:
    tools = config_dict.get("tools") or []
    return any(isinstance(t, dict) and t.get("tool_id") == "rag_search" for t in tools)


def _to_uuid(value: Union[UUID, str, None]) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value).strip())
    except (ValueError, AttributeError):
        return None


async def fetch_indexed_document_inventory(
    organization_id: Union[UUID, str, None] = None,
) -> str:
    """
    List indexed rows from knowledge.documents for the system prompt.

    When organization_id is set, results are limited to that organization.
    When omitted, all indexed documents in the database are listed.
    """
    from engine.shared.db.session import AsyncSessionLocal
    from engine.shared.models.document_model import Document

    org_uuid = _to_uuid(organization_id)

    try:
        async with AsyncSessionLocal() as db:
            query = (
                select(Document)
                .where(
                    Document.status == "indexed",
                    Document.deleted_at.is_(None),
                )
                .order_by(Document.title, Document.created_at)
                .limit(20)
            )
            if org_uuid is not None:
                query = query.where(Document.workspace_id == org_uuid)

            result = await db.execute(query)
            docs = result.scalars().all()

            # Count total indexed documents
            count_query = select(func.count()).select_from(Document).where(
                Document.status == "indexed",
                Document.deleted_at.is_(None),
            )
            if org_uuid is not None:
                count_query = count_query.where(Document.workspace_id == org_uuid)
            total_count = await db.scalar(count_query) or len(docs)

        if not docs:
            if org_uuid is not None:
                return (
                    "No indexed documents for this organization. "
                    "Upload files on the Documents page first."
                )
            return "No indexed documents in the database yet."

        lines = [f"Total indexed documents shown (preview): {len(docs)} (total: {total_count})", ""]
        for index, doc in enumerate(docs, start=1):
            title = doc.title or doc.reference_id or "Untitled"
            chunk_count = doc.chunk_count or 0
            lines.append(f"{index}. **{title}** — {chunk_count} chunks (id: {doc.id})")

        if len(docs) == 20:
            lines.append(
                "\n*(Note: Only the first 20 documents are listed here to save context window size. Use the rag_search tool to find information from all documents.)*"
            )

        return "\n".join(lines)

    except Exception as exc:
        logger.warning("Failed to load document inventory: %s", exc)
        return "Could not load indexed document list."


def enrich_config_for_rag(
    config_dict: Dict[str, Any], inventory: str
) -> Dict[str, Any]:
    """Append the live document inventory to the assistant system instruction."""
    cfg = dict(config_dict)
    instruction = (cfg.get("system_instruction") or "").strip()

    if "Answer document questions using rag_search" not in instruction:
        instruction = (
            f"{RAG_DOCUMENT_ASSISTANT_PROMPT.strip()}\n\n{instruction}".strip()
        )

    cfg["system_instruction"] = f"{instruction}\n\n## INDEXED DOCUMENTS\n{inventory}"
    return cfg
