from fastapi import APIRouter, Depends, Query, status
from typing import List
from uuid import UUID

from engine.shared.core.deps import get_base_deps, BaseDeps
from engine.modules.assistant.schemas.assistant_schema import (
    AssistantCreate, AssistantUpdate, AssistantResponse, AssistantStatusUpdate
)
from engine.modules.assistant.services.assistant_service import AssistantService

router = APIRouter(prefix="/assistants", tags=["assistants"])

@router.post("", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    assistant_in: AssistantCreate,
    deps: BaseDeps = Depends(get_base_deps)
):
    """Create a new assistant."""
    return await AssistantService.create_assistant(
        db=deps.db,
        obj_in=assistant_in,
        user_id=deps.current_user.id
    )

@router.get("", response_model=List[AssistantResponse])
async def get_assistants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    deps: BaseDeps = Depends(get_base_deps)
):
    """Get list of assistants with pagination."""
    return await AssistantService.get_assistants(
        db=deps.db,
        skip=skip,
        limit=limit
    )

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    deps: BaseDeps = Depends(get_base_deps)
):
    """Get assistant details."""
    return await AssistantService.get_assistant(db=deps.db, assistant_id=assistant_id)

@router.patch("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    assistant_in: AssistantUpdate,
    deps: BaseDeps = Depends(get_base_deps)
):
    """Update assistant details."""
    return await AssistantService.update_assistant(
        db=deps.db,
        assistant_id=assistant_id,
        obj_in=assistant_in,
        user_id=deps.current_user.id
    )

@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    deps: BaseDeps = Depends(get_base_deps)
):
    """Soft delete assistant."""
    await AssistantService.soft_delete_assistant(
        db=deps.db,
        assistant_id=assistant_id,
        user_id=deps.current_user.id
    )

@router.patch("/{assistant_id}/status", response_model=AssistantResponse)
async def update_assistant_status(
    assistant_id: UUID,
    status_in: AssistantStatusUpdate,
    deps: BaseDeps = Depends(get_base_deps)
):
    """Enable/Disable assistant."""
    return await AssistantService.update_status(
        db=deps.db,
        assistant_id=assistant_id,
        obj_in=status_in,
        user_id=deps.current_user.id
    )
