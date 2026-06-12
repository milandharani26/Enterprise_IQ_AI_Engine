from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from uuid import UUID
from datetime import datetime, timezone
from fastapi import HTTPException, status

from engine.modules.assistant.assistant_models import Assistant
from engine.modules.assistant.assistant_schemas import AssistantCreate, AssistantUpdate, AssistantStatusUpdate

class AssistantService:
    @staticmethod
    async def create_assistant(db: AsyncSession, obj_in: AssistantCreate, user_id: UUID) -> Assistant:
        # Check if assistant_name or assistant_code already exists
        query = select(Assistant).where(
            (Assistant.assistant_name == obj_in.assistant_name) | 
            (Assistant.assistant_code == obj_in.assistant_code)
        )
        result = await db.execute(query)
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assistant with this name or code already exists."
            )
        
        db_obj = Assistant(
            **obj_in.model_dump(),
            created_by=user_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get_assistant(db: AsyncSession, assistant_id: UUID) -> Assistant:
        query = select(Assistant).where(
            Assistant.assistant_id == assistant_id,
            Assistant.deleted_at.is_(None)
        )
        result = await db.execute(query)
        assistant = result.scalars().first()
        if not assistant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assistant not found"
            )
        return assistant

    @staticmethod
    async def get_assistants(db: AsyncSession, skip: int = 0, limit: int = 100):
        query = select(Assistant).where(
            Assistant.deleted_at.is_(None)
        ).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_assistant(
        db: AsyncSession, assistant_id: UUID, obj_in: AssistantCreate, user_id: UUID
    ) -> Assistant:
        assistant = await AssistantService.get_assistant(db, assistant_id)
        
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(assistant, field, value)
            
        assistant.updated_at = datetime.utcnow()
        assistant.updated_by = user_id
        
        await db.commit()
        await db.refresh(assistant)
        return assistant

    @staticmethod
    async def soft_delete_assistant(db: AsyncSession, assistant_id: UUID, user_id: UUID) -> Assistant:
        assistant = await AssistantService.get_assistant(db, assistant_id)
        
        assistant.deleted_at = datetime.utcnow()
        assistant.deleted_by = user_id
        assistant.updated_at = datetime.utcnow()
        assistant.updated_by = user_id
        
        await db.commit()
        return assistant

    @staticmethod
    async def update_status(
        db: AsyncSession, assistant_id: UUID, obj_in: AssistantStatusUpdate, user_id: UUID
    ) -> Assistant:
        assistant = await AssistantService.get_assistant(db, assistant_id)
        
        assistant.status = obj_in.status
        assistant.updated_at = datetime.utcnow()
        assistant.updated_by = user_id
        
        await db.commit()
        await db.refresh(assistant)
        return assistant
