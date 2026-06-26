"""
Loads recent conversation messages for SQL memory context.

Only used by sql_query tool to give the LLM context of what was
discussed earlier in the conversation (e.g. "whose details is this?").

Token trimming is simple: we estimate 1 token ≈ 4 characters and walk
backwards through messages (newest first) until the budget is used up.
This keeps the most recent exchanges which are the most relevant.
"""

import logging
import uuid
from typing import List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from engine.shared.db.session import AsyncSessionLocal
from engine.modules.conversation.conversation_models import (
    ConversationMessage,
    MessageRole,
)

# logging.basicConfig(level=logging.INFO)  # add this after the imports
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)  # add this too

# 1 token ≈ 4 characters (rough estimate, good enough for trimming)
_CHARS_PER_TOKEN = 4


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


async def load_recent_conversation_history(
    conversation_id: str,
    max_tokens: int = 3000,
) -> Optional[List[dict]]:
    """
    Fetches recent USER + ASSISTANT messages for the given conversation,
    trimmed to fit within max_tokens.

    Returns a list of dicts like:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

    Ordered oldest → newest so it reads naturally when injected into a prompt.
    Returns None if anything goes wrong (so the tool still works without history).
    """
    try:
        # Convert to UUID object if it's a string
        try:
            conv_uuid = uuid.UUID(str(conversation_id))
        except (ValueError, AttributeError) as e:
            logger.warning(
                "[ConversationHistory] Invalid conversation_id '%s': %s",
                conversation_id,
                e,
            )
            return None

        logger.info(
            "[ConversationHistory] Loading history for conversation %s", conv_uuid
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ConversationMessage)
                .where(ConversationMessage.conversation_id == conv_uuid)
                .where(
                    ConversationMessage.role.in_(
                        [MessageRole.USER, MessageRole.ASSISTANT]
                    )
                )
                .order_by(desc(ConversationMessage.created_at))
                .limit(50)  # fetch up to 50 messages, then trim by tokens below
            )
            messages = result.scalars().all()

        logger.info("[ConversationHistory] Raw messages fetched: %d", len(messages))

        if not messages:
            logger.info(
                "[ConversationHistory] No messages found for conversation %s", conv_uuid
            )
            return None

        # messages are newest-first; trim from newest backwards until budget runs out
        selected = []
        tokens_used = 0

        for msg in messages:  # newest → oldest
            content = (msg.content or "").strip()
            if not content:
                continue
            cost = _estimate_tokens(content)
            if tokens_used + cost > max_tokens:
                break
            selected.append(
                {
                    "role": "user" if msg.role == MessageRole.USER else "assistant",
                    "content": content,
                }
            )
            tokens_used += cost

        if not selected:
            logger.info(
                "[ConversationHistory] All messages exceeded token budget, returning None"
            )
            return None

        # reverse so the list is oldest → newest
        selected.reverse()

        logger.info(
            "[ConversationHistory] Loaded %d messages (~%d tokens) for conversation %s",
            len(selected),
            tokens_used,
            conv_uuid,
        )
        return selected

    except Exception as e:
        # Never crash the tool just because history loading failed
        logger.warning(
            "[ConversationHistory] Failed to load history for conversation %s: %s",
            conversation_id,
            e,
            exc_info=True,
        )
        return None
