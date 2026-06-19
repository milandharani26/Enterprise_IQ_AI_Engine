import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
