from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from engine.shared.core.deps import BaseDeps, get_base_deps, get_current_organization_id, get_current_user
from engine.shared.schemas.common import SuccessDataResponse, SuccessListResponse
from engine.modules.database_connector.schemas import (
    DatabaseConnectionCreate,
    DatabaseConnectionUpdate,
    DatabaseConnectionResponse,
    DatabaseConnectionTestRequest,
    DatabaseConnectionTestResponse,
    SchemaTableResponse,
    SyncStatusResponse
)
from engine.modules.database_connector.service import DatabaseConnectionService
from engine.modules.database_connector.tasks import schedule_sync_schema

router = APIRouter(prefix="/database-connections", tags=["Database Connections"])

@router.post("", response_model=SuccessDataResponse[DatabaseConnectionResponse], status_code=201)
async def create_connection(
    request: DatabaseConnectionCreate,
    background_tasks: BackgroundTasks,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Create a new database connection and trigger background sync."""
    db_obj = await DatabaseConnectionService.create_connection(base_deps.db, request, org_id, background_tasks=background_tasks)
    return SuccessDataResponse(
        status_code=201,
        message="Database connection created successfully. Schema sync started.",
        data=db_obj
    )

@router.get("", response_model=SuccessListResponse[DatabaseConnectionResponse])
async def list_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """List all active database connections for the organization."""
    items, total = await DatabaseConnectionService.list_connections(base_deps.db, org_id, skip, limit)
    return SuccessListResponse.create(
        items=items,
        total=total,
        offset=skip,
        limit=limit,
        message="Database connections retrieved successfully"
    )

@router.get("/{id}", response_model=SuccessDataResponse[DatabaseConnectionResponse])
async def get_connection(
    id: UUID,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Get details of a specific database connection."""
    db_obj = await DatabaseConnectionService.get_connection(base_deps.db, id, org_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Database connection not found")
    return SuccessDataResponse(
        status_code=200,
        message="Database connection retrieved successfully",
        data=db_obj
    )

@router.put("/{id}", response_model=SuccessDataResponse[DatabaseConnectionResponse])
async def update_connection(
    id: UUID,
    request: DatabaseConnectionUpdate,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Update a database connection."""
    db_obj = await DatabaseConnectionService.update_connection(base_deps.db, id, request, org_id)
    return SuccessDataResponse(
        status_code=200,
        message="Database connection updated successfully",
        data=db_obj
    )

@router.delete("/{id}")
async def delete_connection(
    id: UUID,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Soft delete a database connection."""
    await DatabaseConnectionService.delete_connection(base_deps.db, id, org_id)
    return {"status_code": 200, "message": "Database connection deleted successfully"}

@router.post("/{id}/sync")
async def sync_connection(
    id: UUID,
    background_tasks: BackgroundTasks,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Manually trigger a schema sync for a database connection."""
    db_obj = await DatabaseConnectionService.get_connection(base_deps.db, id, org_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Database connection not found")
        
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
    db_obj = await DatabaseConnectionService.get_connection(base_deps.db, id, org_id)
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

@router.post("/test", response_model=DatabaseConnectionTestResponse)
async def test_connection(
    request: DatabaseConnectionTestRequest,
    current_user=Depends(get_current_user),
):
    """Test a database connection without saving it."""
    # We will implement the actual connection testing logic later in Component 6/11
    # For now, return a placeholder success to unblock frontend
    return DatabaseConnectionTestResponse(
        success=True,
        message="Connection successful (placeholder)"
    )
