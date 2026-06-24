from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from engine.shared.core.deps import BaseDeps, get_base_deps, get_current_organization_id, get_current_user
from engine.shared.schemas.common import SuccessDataResponse, SuccessListResponse
from engine.modules.database_connector.database_connector_schemas import (
    SchemaTableResponse,
    SyncStatusResponse
)
from engine.modules.database_connector.database_connector_service import DatabaseConnectionService
from engine.modules.database_connector.tasks import schedule_sync_schema

router = APIRouter(prefix="/connectors", tags=["Database Connections"])

@router.post("/{id}/sync")
async def sync_connection(
    id: UUID,
    background_tasks: BackgroundTasks,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Manually trigger a schema or data sync for a connector."""
    db_obj = await DatabaseConnectionService.get_connector(base_deps.db, id, org_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    if db_obj.connector_id == "google_drive":
        # Trigger Google Drive Sync in background
        from engine.shared.workers.drive_sync_worker import _sync_drive_for_workspace
        from engine.shared.models.credential_model import Credential
        from sqlalchemy import select
        
        # Get credential
        cred_res = await base_deps.db.execute(select(Credential).where(Credential.id == db_obj.credential_id))
        credential = cred_res.scalars().first()
        
        if credential:
            # Add to fastAPI background tasks
            async def run_drive_sync_bg():
                from engine.shared.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    # Get fresh objects bound to new session
                    conn_res = await session.execute(select(type(db_obj)).where(type(db_obj).id == db_obj.id))
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
        # It's a Database Connector
        schedule_sync_schema(id, org_id, background_tasks=background_tasks)
        return {"status_code": 202, "message": "Schema sync started in the background"}

@router.get("/{id}/sync-status", response_model=SuccessDataResponse[SyncStatusResponse])
async def get_sync_status(
    id: UUID,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Get the current sync status of a connection."""
    db_obj = await DatabaseConnectionService.get_connector(base_deps.db, id, org_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Database connection not found")
        
    tables = await DatabaseConnectionService.get_schema_tables(base_deps.db, id, org_id)
    
    return SuccessDataResponse(
        status_code=200,
        message="Sync status retrieved",
        data=SyncStatusResponse(
            sync_status=db_obj.sync_status,
            last_synced_at=db_obj.last_synced_at,
            table_count=len(tables)
        )
    )

@router.get("/{id}/tables", response_model=SuccessDataResponse[List[SchemaTableResponse]])
async def get_schema_tables(
    id: UUID,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Get all synced tables and their columns for a connection."""
    tables = await DatabaseConnectionService.get_schema_tables(base_deps.db, id, org_id)
    return SuccessDataResponse(
        status_code=200,
        message="Schema tables retrieved successfully",
        data=tables
    )

