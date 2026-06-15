from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from engine.modules.auth.auth_models import User
from engine.modules.service_account.service_account_schema import ServiceAccountCreate, ServiceAccountResponse, ServiceAccountRegenerate
from engine.shared.security.jwt_token import create_service_account_token, get_token_expiration, hash_token
from engine.shared.exceptions.service_exceptions import ExecutionError, EntityNotFoundError

class ServiceAccountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_service_account(self, data: ServiceAccountCreate, org_id: UUID) -> ServiceAccountResponse:
        try:
            # First create the user without a token
            new_user = User(
                user_name=data.name,
                account_type="service_account",
                is_active=True,
                created_by=data.created_by,
                organization_id=org_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.session.add(new_user)
            await self.session.flush() # Flush to get the new user ID without committing
            
            # Generate token with exact expire_at and the user's generated ID
            token = create_service_account_token(
                user_id=str(new_user.id), 
                user_name=data.name, 
                expire_at=data.expire_at, 
                organization_id=str(org_id)
            )
            
            # Update the user with the hashed token
            new_user.service_token = hash_token(token)
            
            await self.session.commit()
            await self.session.refresh(new_user)
            
            return ServiceAccountResponse(
                id=new_user.id,
                name=new_user.user_name,
                expire_at=data.expire_at,
                is_active=new_user.is_active,
                token=token,
                created_by=new_user.created_by
            )
        except Exception as e:
            await self.session.rollback()
            raise ExecutionError(f"Failed to create service account: {str(e)}")

    async def list_service_accounts(self, org_id: UUID) -> List[ServiceAccountResponse]:
        result = await self.session.execute(select(User).where(User.account_type == "service_account", User.organization_id == org_id))
        users = result.scalars().all()
        
        accounts = []
        for user in users:
            # Cannot extract expiration from hashed token, defaulting to current time
            exp = datetime.now(timezone.utc)
            accounts.append(ServiceAccountResponse(
                id=user.id,
                name=user.user_name,
                expire_at=exp,
                is_active=user.is_active,
                token=None, # Do not return hashed token
                created_by=user.created_by
            ))
        return accounts

    async def revoke_service_account(self, account_id: UUID, org_id: UUID) -> bool:
        result = await self.session.execute(select(User).where(User.id == account_id, User.organization_id == org_id))
        user = result.scalars().first()
        if not user or user.account_type != "service_account":
            raise EntityNotFoundError(entity_type="Service Account", identifier=str(account_id))
            
        user.is_active = False
        user.service_token = None
        await self.session.commit()
        return True

    async def regenerate_service_account_token(self, account_id: UUID, data: ServiceAccountRegenerate, org_id: UUID) -> ServiceAccountResponse:
        result = await self.session.execute(select(User).where(User.id == account_id, User.organization_id == org_id))
        user = result.scalars().first()
        if not user or user.account_type != "service_account":
            raise EntityNotFoundError(entity_type="Service Account", identifier=str(account_id))
            
        if data.expire_at:
            new_exp = data.expire_at
        else:
            # Cannot extract expiration from hashed token, defaulting to current time + 1 year
            from datetime import timedelta
            new_exp = datetime.now(timezone.utc) + timedelta(days=365)
            
        new_token = create_service_account_token(
            user_id=str(user.id), 
            user_name=user.user_name, 
            expire_at=new_exp,
            organization_id=str(org_id)
        )
        
        user.service_token = hash_token(new_token)
        await self.session.commit()
        
        return ServiceAccountResponse(
            id=user.id,
            name=user.user_name,
            expire_at=new_exp,
            is_active=user.is_active,
            token=new_token,
            created_by=user.created_by
        )
