from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from engine.shared.db.session import AsyncSessionLocal
from engine.modules.service_account.schemas.service_account_schema import ServiceAccountCreate, ServiceAccountResponse, ServiceAccountRegenerate
from engine.modules.service_account.services.service_account_service import ServiceAccountService
from engine.shared.schemas.common import ErrorResponse

router = APIRouter(tags=["Service Accounts"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_service_account_service(session: AsyncSession = Depends(get_db)) -> ServiceAccountService:
    return ServiceAccountService(session=session)

@router.post("/", response_model=ServiceAccountResponse, status_code=status.HTTP_201_CREATED, responses={400: {"model": ErrorResponse}})
async def create_new_service_account(data: ServiceAccountCreate, service: ServiceAccountService = Depends(get_service_account_service)):
    """
    Create a new service account with the specified expiration time.
    Returns the created account and a newly generated JWT token.
    """
    return await service.create_service_account(data=data)

@router.get("/", response_model=List[ServiceAccountResponse])
async def list_all_service_accounts(service: ServiceAccountService = Depends(get_service_account_service)):
    """
    List all active and inactive service accounts.
    """
    return await service.list_service_accounts()

@router.post("/{account_id}/revoke", status_code=status.HTTP_200_OK, responses={404: {"model": ErrorResponse}})
async def revoke_account_access(account_id: UUID, service: ServiceAccountService = Depends(get_service_account_service)):
    """
    Revokes the service account access by deleting its token and setting it to inactive.
    """
    await service.revoke_service_account(account_id=account_id)
    return {"success": True, "message": "Service account revoked successfully"}

@router.post("/{account_id}/regenerate", response_model=ServiceAccountResponse, responses={404: {"model": ErrorResponse}})
async def regenerate_account_token(account_id: UUID, data: ServiceAccountRegenerate, service: ServiceAccountService = Depends(get_service_account_service)):
    """
    Regenerates the token for the service account. Updates expiration time if provided, otherwise re-uses old time.
    """
    return await service.regenerate_service_account_token(account_id=account_id, data=data)
