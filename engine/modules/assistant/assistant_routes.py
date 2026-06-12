from engine.shared.core.middleware import require_admin
from fastapi import APIRouter, Depends, Query, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from engine.shared.core.deps import get_db
from engine.modules.auth.auth_models import User
from engine.modules.assistant.assistant_schemas import (
    AssistantCreate, AssistantUpdate, AssistantResponse, AssistantStatusUpdate
)
from engine.modules.assistant.assistant_service import AssistantService

router = APIRouter(prefix="/assistants", tags=["assistants"])

@router.post("", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    assistant_in: AssistantCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new assistant."""
    return await AssistantService.create_assistant(
        db=db,
        obj_in=assistant_in,
        user_id=current_user.id
    )

@router.get("", response_model=List[AssistantResponse])
async def get_assistants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get list of assistants with pagination."""
    return await AssistantService.get_assistants(
        db=db,
        skip=skip,
        limit=limit
    )

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get assistant details."""
    return await AssistantService.get_assistant(db=db, assistant_id=assistant_id)

@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    assistant_in: AssistantCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update assistant details."""
    return await AssistantService.update_assistant(
        db=db,
        assistant_id=assistant_id,
        obj_in=assistant_in,
        user_id=current_user.id
    )

@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete assistant."""
    await AssistantService.soft_delete_assistant(
        db=db,
        assistant_id=assistant_id,
        user_id=current_user.id
    )

@router.patch("/{assistant_id}/status", response_model=AssistantResponse)
async def update_assistant_status(
    assistant_id: UUID,
    status_in: AssistantStatusUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Enable/Disable assistant."""
    return await AssistantService.update_status(
        db=db,
        assistant_id=assistant_id,
        obj_in=status_in,
        user_id=current_user.id
    )
