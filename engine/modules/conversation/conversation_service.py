# modules/conversation/conversation_service.py
import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc
from engine.modules.conversation.conversation_models import Conversation, ConversationMessage, MessageRole
from engine.modules.conversation.conversation_schemas import NewUserMessagePayloadSchema
from engine.modules.organization.organization_models import Organization
from engine.modules.assistant.assistant_models import Assistant
from engine.modules.assistant.runtime.executor import AssistantExecutor
from shared.logging import get_logger, StructuredLogger

class ConversationService:
    def __init__(self, db: AsyncSession, logger: Optional[StructuredLogger] = None):
        self.db = db
        self.logger = logger or get_logger(module="conversation_service")

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

    async def _resolve_assistant(self, agent_id: uuid.UUID, org_id: uuid.UUID) -> Assistant | None:
        if not agent_id:
            return None
        result = await self.db.execute(
            select(Assistant).where(
                Assistant.assistant_id == agent_id,
                Assistant.organization_id == org_id,
                Assistant.deleted_at.is_(None),
                Assistant.status == "enabled",
            )
        )
        return result.scalar_one_or_none()

    async def handle_chat_turn(self, payload: NewUserMessagePayloadSchema, save_to_db: bool = True) -> ConversationMessage:
        """
        Processes a full message loop turn:
        1. Resolve or construct the conversation session
        2. Persist the USER prompt
        3. Execute assistant with RAG tools when configured
        4. Persist the ASSISTANT response
        5. Return the ASSISTANT message
        """
        self.logger.info(
            "Chat turn started",
            extra={"event": "conversation.turn_start", "conversation_id": str(payload.conversation_id), "agent_id": str(payload.agent_id) if payload.agent_id else None},
        )
        org_id = payload.organization_id
        if not org_id and save_to_db:
            org_id = await self._get_or_create_default_org()

        if save_to_db:
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
        
        ai_generated_text = f"Processed engine response for prompt: '{payload.content}'"
        content_blocks = []
        final_org_id = org_id if org_id else uuid.uuid4()

        assistant = None
        if payload.agent_id and org_id:
            assistant = await self._resolve_assistant(payload.agent_id, org_id)

        if not payload.agent_id:
            ai_generated_text = (
                "No assistant selected. Choose an assistant with rag_search enabled in the chat header."
            )
            content_blocks = [
                {"type": "markdown", "data": {"content": ai_generated_text}}
            ]
        elif not assistant:
            ai_generated_text = (
                "Assistant not found for this organization. "
                "Create or enable an assistant with the rag_search tool in Assistants."
            )
            content_blocks = [
                {"type": "markdown", "data": {"content": ai_generated_text}}
            ]
        elif assistant:
            try:
                from engine.pipelines.ingestion.services.embedding_service import EmbeddingService
                from engine.modules.assistant.semantic_cache import SemanticCacheService
                
                embed_svc = EmbeddingService()
                query_embedding = await embed_svc.embed_query(payload.content)
                
                cached_match = await SemanticCacheService.lookup_cache(
                    self.db, 
                    assistant.assistant_id, 
                    query_embedding, 
                    assistant.cache_version
                )
                
                if cached_match:
                    self.logger.info("Semantic cache hit", extra={"event": "conversation.cache_hit", "assistant_id": str(assistant.assistant_id)})
                    ai_generated_text = cached_match.response
                    content_blocks = cached_match.sources or []
                else:
                    self.logger.info("Cache miss — running assistant executor", extra={"event": "conversation.cache_miss", "assistant_id": str(assistant.assistant_id)})
                    executor = AssistantExecutor()
                    ai_generated_text, content_blocks = await executor.execute(
                        session_id=str(payload.conversation_id),
                        conversation_id=str(payload.conversation_id),
                        user_id=str(payload.user_id),
                        assistant_id=str(assistant.assistant_id),
                        query=payload.content,
                        organization_ids=[str(org_id)],
                        assistant=assistant,
                    )
                    
                    # Cache the result
                    await SemanticCacheService.write_cache(
                        self.db,
                        assistant.assistant_id,
                        payload.content,
                        query_embedding,
                        ai_generated_text,
                        content_blocks,
                        None,
                        assistant.cache_version
                    )
            except Exception as e:
                self.logger.error(
                    f"Assistant execution failed: {e}",
                    extra={"event": "conversation.execute_error", "error": str(e)},
                )
                ai_generated_text = (
                    f"I encountered an error while processing your request: {e}"
                )
                content_blocks = [
                    {"type": "markdown", "data": {"content": ai_generated_text}}
                ]

        metadata = {"content_blocks": content_blocks} if content_blocks else None

        assistant_message = ConversationMessage(
            id=uuid.uuid4(),
            conversation_id=payload.conversation_id,
            role=MessageRole.ASSISTANT,
            content=ai_generated_text,
            organization_id=final_org_id,
            metadata_json=metadata,
            created_at=datetime.utcnow()
        )

        if save_to_db:
            self.db.add(assistant_message)
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
