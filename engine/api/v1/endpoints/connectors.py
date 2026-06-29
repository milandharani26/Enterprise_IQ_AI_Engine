import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from engine.shared.core.deps import get_current_organization_id
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.connector_model import Connector
from engine.shared.schemas.connector_schema import ConnectorCreate, ConnectorUpdate, ConnectorResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/", response_model=ConnectorResponse)
async def create_connector(
    conn_in: ConnectorCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_conn = Connector(
            organization_id=conn_in.organization_id,
            connector_id=conn_in.connector_id,
            name=conn_in.name,
            provider=conn_in.provider,
            status=conn_in.status,
            credential_id=conn_in.credential_id
        )
        db.add(new_conn)
        await db.commit()
        await db.refresh(new_conn)
        return new_conn
    except Exception as e:
        logger.error(f"Failed to create connector: {e}")
        raise HTTPException(status_code=500, detail="Failed to create connector")


@router.get("/organization/{organization_id}", response_model=List[ConnectorResponse])
async def list_connectors_by_org(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Connector).where(Connector.organization_id == organization_id)
        )
        connectors = result.scalars().all()
        return connectors
    except Exception as e:
        logger.error(f"Failed to fetch connectors: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch connectors")


@router.patch("/{id}", response_model=ConnectorResponse)
async def update_connector(
    id: UUID,
    conn_in: ConnectorUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(
            select(Connector).where(Connector.id == id)
        )
        connector = result.scalars().first()
        if not connector:
            raise HTTPException(status_code=404, detail="Connector not found")
        
        if conn_in.name is not None:
            connector.name = conn_in.name
        if conn_in.status is not None:
            connector.status = conn_in.status
        if conn_in.credential_id is not None:
            connector.credential_id = conn_in.credential_id
        
        await db.commit()
        await db.refresh(connector)
        return connector
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update connector: {e}")
        raise HTTPException(status_code=500, detail="Failed to update connector")


@router.post("/{id}/sync")
async def sync_connector(
    id: UUID,
    background_tasks: BackgroundTasks,
    org_id: UUID = Depends(get_current_organization_id),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger a sync for a connector."""
    result = await db.execute(select(Connector).where(Connector.id == id, Connector.organization_id == org_id))
    db_obj = result.scalars().first()
    
    if not db_obj:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    db_obj.sync_status = "syncing"
    await db.commit()
    await db.refresh(db_obj)
        
    if db_obj.connector_id == "google_drive":
        from engine.shared.workers.drive_sync_worker import _sync_drive_for_workspace
        from engine.shared.models.credential_model import Credential
        
        cred_res = await db.execute(select(Credential).where(Credential.id == db_obj.credential_id))
        credential = cred_res.scalars().first()
        
        if credential:
            async def run_drive_sync_bg():
                from engine.shared.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    conn_res = await session.execute(select(Connector).where(Connector.id == db_obj.id))
                    fresh_conn = conn_res.scalars().first()
                    cred_res2 = await session.execute(select(Credential).where(Credential.id == credential.id))
                    fresh_cred = cred_res2.scalars().first()
                    if fresh_conn and fresh_cred:
                        await _sync_drive_for_workspace(session, fresh_conn, fresh_cred)
                        
            background_tasks.add_task(run_drive_sync_bg)
            return {"status_code": 202, "message": "Google Drive sync started in the background"}
        else:
            raise HTTPException(status_code=400, detail="Credential not mapped for this connector")
            
    else:
        from engine.modules.database_connector.tasks import schedule_sync_schema
        schedule_sync_schema(id, org_id, background_tasks=background_tasks)
        return {"status_code": 202, "message": f"{db_obj.name} schema sync started in the background"}
