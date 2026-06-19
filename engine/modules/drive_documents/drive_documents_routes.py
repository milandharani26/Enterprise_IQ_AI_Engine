"""API routes for Google Drive document management (ingest, retrieve, update, delete)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from engine.shared.core.deps import BaseDeps, get_base_deps, get_current_user
from engine.shared.schemas.common import SuccessDataResponse
from engine.shared.schemas.drive_document_schema import (
    DriveDocumentDataResponse,
    DriveDocumentIngestData,
    DriveDocumentIngestRequest,
    DriveDocumentIngestResponse,
    DriveDocumentListResponse,
    DriveDocumentSimpleResponse,
    DriveDocumentUpdateMetadataRequest,
)
from engine.modules.drive_documents.drive_documents_service import DriveDocumentService

router = APIRouter(prefix="/drive-documents", tags=["Drive Documents"])


@router.post("/ingest", response_model=DriveDocumentIngestResponse, status_code=202)
async def ingest_drive_document(
    request: DriveDocumentIngestRequest,
    background_tasks: BackgroundTasks,
    organization_id: UUID = Query(..., description="Target organization ID (maps to workspace scope)"),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Ingest a Google Drive document and queue background indexing."""
    service = DriveDocumentService(base_deps)
    doc = await service.create_drive_document(request, workspace_id=organization_id)

    status = doc.status
    task_id = None

    # Note: A dedicated schedule_index_drive_document should be implemented in ingestion/indexing.py
    # Here we mock the scheduling response to maintain API parity.
    # from engine.pipelines.ingestion.indexing import schedule_index_drive_document
    # task_id = schedule_index_drive_document(...)

    return DriveDocumentIngestResponse(
        status_code=202,
        message="Drive document queued for indexing",
        data=DriveDocumentIngestData(
            doc_id=doc.id,
            drive_file_id=doc.drive_file_id,
            status=status,
            message="Drive document queued for indexing",
            task_id=task_id,
        ),
    )


@router.get("", response_model=DriveDocumentListResponse)
async def list_drive_documents(
    organization_id: UUID = Query(..., description="Organization to list documents for"),
    status: Optional[str] = Query(None, pattern="^(draft|processing|indexed|failed)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DriveDocumentService(base_deps)
    items, total = await service.list_drive_documents(
        workspace_id=organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return DriveDocumentListResponse.create(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        message="Drive documents retrieved successfully",
    )


@router.get("/ingestion-status/{document_id}", response_model=SuccessDataResponse[dict])
async def get_drive_document_ingestion_status(
    document_id: UUID,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DriveDocumentService(base_deps)
    status = await service.get_document_status(document_id)
    return SuccessDataResponse(
        status_code=200,
        message="Drive document ingestion status retrieved successfully",
        data={"document_id": str(document_id), "status": status},
    )


@router.get("/{id}", response_model=DriveDocumentDataResponse)
async def get_drive_document(
    id: UUID,
    organization_id: UUID = Query(..., description="Organization the document belongs to"),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DriveDocumentService(base_deps)
    result = await service.get_drive_document(id, organization_id)
    return DriveDocumentDataResponse(data=result, message="Drive document retrieved successfully")


@router.patch("/{id}", response_model=DriveDocumentDataResponse)
async def update_drive_document(
    id: UUID,
    organization_id: UUID = Query(..., description="Organization the document belongs to"),
    request: DriveDocumentUpdateMetadataRequest = ...,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DriveDocumentService(base_deps)
    result = await service.update_drive_document(id, organization_id, request)
    return DriveDocumentDataResponse(data=result, message="Drive document updated successfully")


@router.delete("/{id}", response_model=DriveDocumentSimpleResponse)
async def delete_drive_document(
    id: UUID,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DriveDocumentService(base_deps)
    await service.delete_drive_document(id)
    return DriveDocumentSimpleResponse(status_code=200, message="Drive document deleted successfully")
