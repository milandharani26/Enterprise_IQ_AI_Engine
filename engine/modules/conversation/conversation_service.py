# modules/conversation/conversation_service.py
import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from engine.modules.conversation.conversation_models import Conversation, ConversationMessage, MessageRole
from engine.modules.conversation.conversation_schemas import NewUserMessagePayloadSchema
from engine.modules.organization.organization_models import Organization

class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create_default_org(self) -> uuid.UUID:
        """Helper to find the first organization or create a default one if NestJS doesn't send one."""
        result = await self.db.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()
        if org:
            return org.id
            
        # Create a default organization if none exists
        default_org = Organization(
            id=uuid.uuid4(),
            name="Default Organization",
            email="admin@example.com"
        )
        self.db.add(default_org)
        await self.db.flush()
        return default_org.id

    async def handle_chat_turn(self, payload: NewUserMessagePayloadSchema, save_to_db: bool = True) -> ConversationMessage:
        """
        Processes a full message loop turn for the Admin Backend:
        1. Resolve or construct the conversation session
        2. Persist the USER prompt in the Admin DB.
        3. Generate the AI response locally.
        4. Persist the ASSISTANT generated feedback response in the Admin DB.
        5. Return the ASSISTANT message (which NestJS will wait for).
        """
        # Determine the organization ID
        org_id = payload.organization_id
        if not org_id and save_to_db:
            org_id = await self._get_or_create_default_org()

        if save_to_db:
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
                    organization_id=org_id,
                    title=payload.content[:30] if len(payload.content) > 30 else payload.content
                )
                self.db.add(conversation)
                await self.db.flush()

            # Step 2: Persist the User's Message locally in Admin DB
            user_message = ConversationMessage(
                id=uuid.uuid4(),
                conversation_id=payload.conversation_id,
                role=MessageRole.USER,
                content=payload.content,
                organization_id=org_id
            )
            self.db.add(user_message)
            await self.db.flush()

        from datetime import datetime
        
        # Step 3: Generate the AI response locally
        # TODO: Replace with your actual LLM logic (e.g. OpenAI, Anthropic, Gemini calls)
        ai_generated_text = f"Processed engine response for prompt: '{payload.content}'"

        # Provide defaults for Pydantic schema validation if not saving to DB
        final_org_id = org_id if org_id else uuid.uuid4()

        assistant_message = ConversationMessage(
            id=uuid.uuid4(),
            conversation_id=payload.conversation_id,
            role=MessageRole.ASSISTANT,
            content=ai_generated_text,
            organization_id=final_org_id,
            created_at=datetime.utcnow()
        )

        if save_to_db:
            # Step 4: Persist the Assistant's Response locally in Admin DB
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

    async def get_all_conversations(self, user_id: uuid.UUID, organization_id: uuid.UUID = None) -> List[Conversation]:
        """Retrieves all conversation sessions for a user within an organization."""
        from sqlalchemy import desc
        
        query = select(Conversation).where(Conversation.user_id == user_id)
        if organization_id:
            query = query.where(Conversation.organization_id == organization_id)
            
        query = query.order_by(desc(Conversation.created_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()