"""Google Drive prompt helpers: document inventory and instruction enrichment."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union
from uuid import UUID

from sqlalchemy import select

logger = logging.getLogger(__name__)

DRIVE_DOCUMENT_ASSISTANT_PROMPT = """You are a Google Drive assistant for this organization.

Rules:
- Answer questions about Google Drive documents using drive_search over knowledge.drive_document_chunks.
- Do not invent content — only use search results and the indexed Google Drive document list below.
- For inventory questions, list document titles from INDEXED GOOGLE DRIVE DOCUMENTS and summarize via drive_search.
- Cite source titles inline and include the Drive Link provided in the results.
- CRITICAL FORMATTING RULE: When outputting the Drive Link, you MUST use strict Markdown link formatting: [Document Title](URL). You must NEVER place any spaces or newlines between the closing bracket ']' and the opening parenthesis '('.
- If search returns nothing, do NOT immediately give up. You MUST try your other available search tools (like rag_search or sql_query) before concluding the information is missing. Only suggest syncing files if ALL relevant search tools fail.
"""

DRIVE_WORKFLOW_INSTRUCTIONS = """
## GOOGLE DRIVE WORKFLOW (required when drive_search is available)

1. Call **drive_search** before answering any question about synced Google Drive files, Drive PDFs, or Drive folders.
2. Use the user's question as the search query (rephrase if needed for clarity).
3. For "what drive documents do you have": list titles from INDEXED GOOGLE DRIVE DOCUMENTS, then drive_search for summaries.
4. Answer only from search excerpts. Do not use outside knowledge for drive document facts.
5. CRITICAL: When outputting Google Drive Links, you MUST use strict Markdown format exactly like this: [Title](URL). Do NOT put any spaces, newlines, or line breaks between the closing bracket ']' and the opening parenthesis '('. If you break them apart, the link will fail to render.
6. Format the answer directly in markdown.
7. If drive_search yields no results, you must proceed to try other search tools before giving up.
"""


def assistant_has_drive_tool(config_dict: Dict[str, Any]) -> bool:
    tools = config_dict.get("tools") or []
    return any(
        isinstance(t, dict) and t.get("tool_id") == "drive_search" for t in tools
    )


def _to_uuid(value: Union[UUID, str, None]) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value).strip())
    except (ValueError, AttributeError):
        return None


async def fetch_drive_document_inventory(
    organization_id: Union[UUID, str, None] = None,
) -> str:
    """
    List indexed rows from knowledge.drive_documents for the system prompt.

    When organization_id is set, results are limited to that organization.
    When omitted, all indexed Google Drive documents in the database are listed.
    """
    from engine.shared.db.session import AsyncSessionLocal
    from engine.shared.models.drive_document_model import DriveDocument

    org_uuid = _to_uuid(organization_id)

    try:
        async with AsyncSessionLocal() as db:
            query = (
                select(DriveDocument)
                .where(DriveDocument.status == "indexed")
                .order_by(DriveDocument.title, DriveDocument.created_at)
                .limit(20)
            )
            if org_uuid is not None:
                query = query.where(DriveDocument.workspace_id == org_uuid)

            result = await db.execute(query)
            docs = result.scalars().all()

        if not docs:
            if org_uuid is not None:
                return (
                    "No indexed Google Drive documents for this organization. "
                    "Sync files from Google Drive first."
                )
            return "No indexed Google Drive documents in the database yet."

        lines = [
            f"Total indexed Google Drive documents shown (preview): {len(docs)}",
            "",
        ]
        for index, doc in enumerate(docs, start=1):
            title = doc.title or "Untitled"
            chunk_count = doc.chunk_count or 0
            link = doc.web_view_link or "No Link"
            lines.append(f"{index}. **{title}** — {chunk_count} chunks (link: {link})")

        if len(docs) == 20:
            lines.append(
                "\n*(Note: Only the first 20 drive documents are listed here to save context window size. Use the drive_search tool to find information from all documents.)*"
            )

        return "\n".join(lines)

    except Exception as exc:
        logger.warning("Failed to load Google Drive document inventory: %s", exc)
        return "Could not load indexed Google Drive document list."


def enrich_config_for_drive(
    config_dict: Dict[str, Any], inventory: str
) -> Dict[str, Any]:
    """Append the live Google Drive document inventory to the assistant system instruction."""
    cfg = dict(config_dict)
    instruction = (cfg.get("system_instruction") or "").strip()

    if (
        "Answer questions about Google Drive documents using drive_search"
        not in instruction
    ):
        instruction = (
            f"{DRIVE_DOCUMENT_ASSISTANT_PROMPT.strip()}\n\n{instruction}".strip()
        )

    cfg["system_instruction"] = (
        f"{instruction}\n\n## INDEXED GOOGLE DRIVE DOCUMENTS\n{inventory}"
    )
    return cfg
