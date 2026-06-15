from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from engine.shared.core.deps import get_db
from engine.modules.organization.organization_schemas import OrganizationCreateSchema, OrganizationResponseSchema
from engine.modules.organization.organization_service import OrganizationService
from uuid import UUID

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"]
)

@router.post("", response_model=OrganizationResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_new_organization(payload: OrganizationCreateSchema, db: AsyncSession = Depends(get_db)):
    """Creates a new enterprise organization tenant account."""
    service = OrganizationService(db)
    return await service.create_organization(payload)

@router.get("/{org_id}", response_model=OrganizationResponseSchema)
async def get_organization(org_id: UUID, db: AsyncSession = Depends(get_db)):
    """Fetches an existing organization profile by its ID."""
    service = OrganizationService(db)
    org = await service.get_organization_by_id(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Organization profile not found"
        )
    return org