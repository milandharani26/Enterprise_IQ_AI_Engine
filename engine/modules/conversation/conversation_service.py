# modules/conversation/conversation_service.py
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from engine.modules.conversation.conversation_models import Conversation, ConversationMessage, MessageRole
from engine.modules.conversation.conversation_schemas import NewUserMessagePayloadSchema


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def handle_chat_turn(self, payload: NewUserMessagePayloadSchema) -> ConversationMessage:
        """
        Processes a full message loop turn:
        1. Dynamically creates the conversation session if it doesn't exist.
        2. Logs the USER prompt string.
        3. Invokes the AI processing model core logic.
        4. Logs the ASSISTANT generated feedback response.
        """
        # Step 1: Resolve or construct the conversation session
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == payload.conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                id=payload.conversation_id,
                user_id=payload.user_id,
                agent_id=payload.agent_id,
                organization_id=payload.organization_id,
                title=payload.content[:30] if len(payload.content) > 30 else payload.content
            )
            self.db.add(conversation)
            await self.db.flush()  # Flushes session state so keys bind correctly

        # Step 2: Persist the User's Message
        user_message = ConversationMessage(
            id=uuid.uuid4(),
            conversation_id=payload.conversation_id,
            role=MessageRole.USER,
            content=payload.content,
            organization_id=payload.organization_id
        )
        self.db.add(user_message)

        # Step 3: Call your generative engine processing pipelines
        # (Placeholder for your Gemini API / model invocations)
        ai_generated_text = f"Processed engine response for prompt: '{payload.content}'"

        # Step 4: Persist the Assistant's Response
        assistant_message = ConversationMessage(
            id=uuid.uuid4(),
            conversation_id=payload.conversation_id,
            role=MessageRole.ASSISTANT,
            content=ai_generated_text,
            organization_id=payload.organization_id
        )
        self.db.add(assistant_message)

        # Commit transactional mutations to PostgreSQL safely
        await self.db.commit()
        await self.db.refresh(assistant_message)

        return assistant_message

    async def get_conversation_history(self, conversation_id: uuid.UUID) -> List[ConversationMessage]:
        """Retrieves the complete ordered chat logs for a specific conversation room."""
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(asc(ConversationMessage.created_at))
        )
        return result.scalars().all()