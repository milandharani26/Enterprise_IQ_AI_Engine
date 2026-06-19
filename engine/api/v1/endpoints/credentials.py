import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.credential_model import Credential
from engine.shared.schemas.credential_schema import CredentialCreate, CredentialUpdate, CredentialResponse, CredentialTestRequest, CredentialTestResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/test", response_model=CredentialTestResponse)
async def test_credential(test_req: CredentialTestRequest):
    try:
        if test_req.provider == 'Google':
            from engine.shared.integrations.google_drive_client import GoogleDriveClient
            client = GoogleDriveClient(auth_data=test_req.auth_data)
            # Try to list 1 file to verify token works
            client.list_files(page_size=1)
            return CredentialTestResponse(success=True, message="Connection to Google Drive successful!")
        
        elif test_req.provider in ['PostgreSQL', 'MySQL']:
            auth_data = test_req.auth_data
            host = auth_data.get('host')
            port = auth_data.get('port')
            username = auth_data.get('username')
            password = auth_data.get('password')
            database = auth_data.get('database')
            
            if not all([host, port, username, password, database]):
                return CredentialTestResponse(success=False, message="Missing required database configuration.")
                
            if test_req.provider == 'PostgreSQL':
                db_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
            else:
                db_url = f"mysql+aiomysql://{username}:{password}@{host}:{port}/{database}"
                
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            try:
                engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                return CredentialTestResponse(success=True, message=f"Connection to {test_req.provider} successful!")
            except Exception as e:
                return CredentialTestResponse(success=False, message=f"Failed to connect: {str(e)}")
            
        else:
            return CredentialTestResponse(success=False, message=f"Provider '{test_req.provider}' is not supported for testing.")
            
    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        return CredentialTestResponse(success=False, message=str(e))

@router.post("/", response_model=CredentialResponse)
async def create_credential(
    cred_in: CredentialCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_cred = Credential(
            organization_id=cred_in.organization_id,
            name=cred_in.name,
            provider=cred_in.provider,
            status=cred_in.status,
            auth_data=cred_in.auth_data
        )
        db.add(new_cred)
        await db.commit()
        await db.refresh(new_cred)
        return new_cred
    except Exception as e:
        logger.error(f"Failed to create credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to create credential")


@router.get("/organization/{organization_id}", response_model=List[CredentialResponse])
async def list_credentials_by_org(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Credential).where(Credential.organization_id == organization_id)
        )
        creds = result.scalars().all()
        return creds
    except Exception as e:
        logger.error(f"Failed to fetch credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch credentials")


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Credential).where(Credential.id == credential_id)
        )
        cred = result.scalars().first()
        if not cred:
            raise HTTPException(status_code=404, detail="Credential not found")
        
        await db.delete(cred)
        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete credential: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete credential")
