# modules/organization/organization_service.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from engine.modules.organization.organization_models import Organization
from engine.modules.organization.organization_schemas import OrganizationCreateSchema

class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_organization(self, payload: OrganizationCreateSchema) -> Organization:
        """Creates a new enterprise organization tenant."""
        org_id = payload.id if payload.id else uuid.uuid4()
        
        db_org = Organization(
            id=org_id,
            name=payload.name,
            email=payload.email
        )
        self.db.add(db_org)
        await self.db.commit()
        await self.db.refresh(db_org)
        return db_org

    async def get_organization_by_id(self, org_id: uuid.UUID) -> Organization:
        """Retrieves an organization by its primary ID."""
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def get_all_organizations(self) -> list[Organization]:
        """Retrieves all organizations."""
        result = await self.db.execute(select(Organization))
        return result.scalars().all()