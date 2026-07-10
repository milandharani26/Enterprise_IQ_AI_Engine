from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from engine.shared.core.deps import BaseDeps, get_base_deps, get_current_organization_id, get_current_user
from engine.shared.schemas.common import SuccessDataResponse, SuccessListResponse
from engine.modules.database_connector.database_connector_schemas import (
    SchemaTableResponse,
    SchemaTableDetailResponse,
    SyncStatusResponse,
    UpdateTableDescriptionRequest,
    UpdateColumnDescriptionRequest,
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

# ---------------------------------------------------------------------------
# Metadata Enrichment Endpoints
# ---------------------------------------------------------------------------

@router.get("/{id}/tables/detailed")
async def get_schema_tables_detailed(
    id: UUID,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """
    Returns full table + column metadata including row IDs and user-description
    override flags. Used by the Metadata Management Dashboard.
    """
    tables = await DatabaseConnectionService.get_schema_tables_detailed(base_deps.db, id, org_id)
    return SuccessDataResponse(
        status_code=200,
        message="Detailed schema metadata retrieved successfully",
        data=tables
    )


@router.patch("/{id}/tables/{table_id}/description")
async def update_table_description(
    id: UUID,
    table_id: UUID,
    body: UpdateTableDescriptionRequest,
    background_tasks: BackgroundTasks,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """
    Manually set or clear a table description.
    - Non-empty string → marks as user-defined (sync-safe).
    - null / empty string → clears override; next sync can repopulate from DB.
    After saving, regenerates schema embeddings in the background.
    """
    # Verify connector belongs to org
    db_obj = await DatabaseConnectionService.get_connector(base_deps.db, id, org_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Connector not found")

    table = await DatabaseConnectionService.update_table_description(
        base_deps.db, table_id, org_id, body.description
    )

    # Re-generate embeddings in the background so LLM retrieval picks up new description
    async def _regen_embeddings():
        from engine.shared.db.session import AsyncSessionLocal
        from engine.modules.database_connector.schema_crawler import SchemaCrawlerService
        async with AsyncSessionLocal() as session:
            crawler = SchemaCrawlerService()
            await crawler._generate_embeddings(session, id, org_id)

    background_tasks.add_task(_regen_embeddings)

    return SuccessDataResponse(
        status_code=200,
        message="Table description updated successfully",
        data={
            "id": str(table.id),
            "table_name": table.table_name,
            "table_description": table.table_description,
            "user_table_description": table.user_table_description,
        }
    )


@router.patch("/{id}/tables/{table_id}/columns/{column_id}/description")
async def update_column_description(
    id: UUID,
    table_id: UUID,
    column_id: UUID,
    body: UpdateColumnDescriptionRequest,
    background_tasks: BackgroundTasks,
    org_id: UUID = Depends(get_current_organization_id),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """
    Manually set or clear a column description.
    - Non-empty string → marks as user-defined (sync-safe).
    - null / empty string → clears override; next sync can repopulate from DB.
    After saving, regenerates schema embeddings in the background.
    """
    # Verify connector belongs to org
    db_obj = await DatabaseConnectionService.get_connector(base_deps.db, id, org_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Connector not found")

    column = await DatabaseConnectionService.update_column_description(
        base_deps.db, column_id, org_id, body.description
    )

    # Re-generate embeddings in the background so LLM retrieval picks up new description
    async def _regen_embeddings():
        from engine.shared.db.session import AsyncSessionLocal
        from engine.modules.database_connector.schema_crawler import SchemaCrawlerService
        async with AsyncSessionLocal() as session:
            crawler = SchemaCrawlerService()
            await crawler._generate_embeddings(session, id, org_id)

    background_tasks.add_task(_regen_embeddings)

    return SuccessDataResponse(
        status_code=200,
        message="Column description updated successfully",
        data={
            "id": str(column.id),
            "column_name": column.column_name,
            "column_description": column.column_description,
            "user_column_description": column.user_column_description,
        }
    )
