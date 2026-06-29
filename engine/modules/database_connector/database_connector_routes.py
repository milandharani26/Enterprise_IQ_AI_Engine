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

