import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status

from engine.modules.assistant.assistant_models import Assistant
from engine.modules.assistant.assistant_schemas import AssistantCreate, AssistantUpdate, AssistantStatusUpdate, PreviewPromptRequest, PreviewPromptResponse
from engine.modules.assistant.runtime.assistant_factory import AssistantFactory
import tiktoken

logger = logging.getLogger(__name__)

class AssistantService:
    @staticmethod
    async def create_assistant(db: AsyncSession, obj_in: AssistantCreate, user_id: UUID, org_id: UUID) -> Assistant:
        # Check if assistant_name or assistant_code already exists
        query = select(Assistant).where(
            (Assistant.assistant_name == obj_in.assistant_name) | 
            (Assistant.assistant_code == obj_in.assistant_code),
            Assistant.organization_id == org_id
        )
        result = await db.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assistant with this name or code already exists in your organization."
            )
        
        db_obj = Assistant(
            **obj_in.model_dump(),
            created_by=user_id,
            organization_id=org_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get_assistant(db: AsyncSession, assistant_id: UUID, org_id: UUID) -> Assistant:
        query = select(Assistant).where(
            Assistant.assistant_id == assistant_id,
            Assistant.organization_id == org_id,
            Assistant.deleted_at.is_(None)
        )
        result = await db.execute(query)
        assistant = result.scalars().first()
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found or access denied"
            )
        return assistant

    @staticmethod
    async def get_assistants(db: AsyncSession, skip: int = 0, limit: int = 100, org_id: UUID = None):
        query = select(Assistant).where(
            Assistant.organization_id == org_id,
            Assistant.deleted_at.is_(None)
        ).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_assistant(
        db: AsyncSession, assistant_id: UUID, obj_in: AssistantCreate, user_id: UUID, org_id: UUID
    ) -> Assistant:
        assistant = await AssistantService.get_assistant(db, assistant_id, org_id)
        
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(assistant, field, value)
            
        assistant.updated_at = datetime.utcnow()
        assistant.updated_by = user_id
        assistant.cache_version = (assistant.cache_version or 1) + 1

        await db.commit()
        await db.refresh(assistant)

        logger.info(
            f"Assistant {assistant_id} updated — cache invalidated "
            f"(new version: {assistant.cache_version})"
        )
        return assistant

    @staticmethod
    async def soft_delete_assistant(db: AsyncSession, assistant_id: UUID, user_id: UUID, org_id: UUID) -> Assistant:
        assistant = await AssistantService.get_assistant(db, assistant_id, org_id)
        
        assistant.deleted_at = datetime.utcnow()
        assistant.deleted_by = user_id
        assistant.updated_at = datetime.utcnow()
        assistant.updated_by = user_id
        
        await db.commit()
        return assistant

    @staticmethod
    async def update_status(
        db: AsyncSession, assistant_id: UUID, obj_in: AssistantStatusUpdate, user_id: UUID, org_id: UUID
    ) -> Assistant:
        assistant = await AssistantService.get_assistant(db, assistant_id, org_id)
        
        assistant.status = obj_in.status
        assistant.updated_at = datetime.utcnow()
        assistant.updated_by = user_id
        assistant.cache_version = (assistant.cache_version or 1) + 1

        await db.commit()
        await db.refresh(assistant)

        logger.info(
            f"Assistant {assistant_id} status changed to '{obj_in.status}' — "
            f"cache invalidated (new version: {assistant.cache_version})"
        )
        return assistant

    @staticmethod
    async def preview_prompt(obj_in: PreviewPromptRequest) -> PreviewPromptResponse:
        try:
            AssistantFactory.register_types()
            config_dict = obj_in.model_dump()
            assistant_instance = AssistantFactory.get_assistant(config_dict)
            
            # Use the internal _get_tools to retrieve configured base tools
            required_tools = assistant_instance._get_tools(config_dict.get("tools") or [])
            
            # Get the compiled system instruction
            system_instruction = assistant_instance.get_system_instruction(config_dict, required_tools)
            
            # Count tokens using tiktoken (cl100k_base is standard for GPT-4/3.5)
            import asyncio
            def _count_tokens(text: str) -> int:
                try:
                    encoding = tiktoken.get_encoding("cl100k_base")
                    return len(encoding.encode(text))
                except Exception:
                    return 0

            token_count = await asyncio.to_thread(_count_tokens, system_instruction)
                
            return PreviewPromptResponse(
                compiled_prompt=system_instruction,
                estimated_tokens=token_count,
                status="valid",
                warnings=[]
            )
        except Exception as e:
            return PreviewPromptResponse(
                compiled_prompt="",
                estimated_tokens=0,
                status="error",
                warnings=[str(e)]
            )
