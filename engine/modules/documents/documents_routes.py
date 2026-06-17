"""API routes for document management (ingest, retrieve, update, delete, search)."""

from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile

from engine.shared.config.settings import get_settings
from engine.shared.core.deps import BaseDeps, get_base_deps, get_current_user
from engine.shared.schemas.common import SuccessDataResponse
from engine.shared.schemas.document_schema import (
    DocumentDataResponse,
    DocumentIngestData,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentSearchChunk,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSimpleResponse,
    DocumentUpdateMetadataRequest,
)
from engine.modules.documents.documents_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024

@router.post("/upload", response_model=DocumentIngestResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    organization_id: UUID = Form(...),
    title: Optional[str] = Form(default=None),
    reference_id: Optional[UUID] = Form(default=None),
    background_tasks: BackgroundTasks = ...,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """
    Cpanel direct file upload: persist file and queue background indexing.
    """
    filename = (file.filename or title or "upload").strip()
    doc_title = (title or filename).strip()
    if not doc_title:
        raise HTTPException(status_code=400, detail="title or file filename is required")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    settings = get_settings()
    max_bytes = getattr(settings, "max_document_size_mb", 50) * 1024 * 1024
    if len(raw) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {max_bytes // (1024 * 1024)} MB",
        )

    doc_ref = reference_id or uuid4()
    service = DocumentService(base_deps)
    prepared = await service.prepare_uploaded_document(
        reference_id=doc_ref,
        workspace_id=organization_id,
        title=doc_title,
        file_bytes=raw,
        filename=filename,
        mime_type=file.content_type,
        metadata={"upload_source": "cpanel"},
    )

    from engine.pipelines.ingestion.indexing import schedule_index_document

    task_id = schedule_index_document(
        prepared["doc_id"],
        organization_id,
        reference_id=str(prepared["reference_id"]),
        background_tasks=background_tasks,
    )

    return DocumentIngestResponse(
        status_code=202,
        message="Document queued for indexing",
        data=DocumentIngestData(
            doc_id=prepared["doc_id"],
            reference_id=prepared["reference_id"],
            status="processing",
            message="Document queued for indexing",
            chunk_count=0,
            processing_error=None,
            task_id=task_id,
        ),
    )


@router.post("/ingest", response_model=DocumentIngestResponse, status_code=202)
async def ingest_document(
    request: DocumentIngestRequest,
    background_tasks: BackgroundTasks,
    organization_id: UUID = Query(..., description="Target organization ID (maps to workspace scope)"),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Ingest a document from S3/GCS/HTTP and queue background indexing."""
    service = DocumentService(base_deps)
    doc = await service.create_document(request, workspace_id=organization_id)

    status = doc.status
    task_id = None

    from engine.pipelines.ingestion.indexing import schedule_index_document

    task_id = schedule_index_document(
        doc.id,
        organization_id,
        reference_id=str(doc.reference_id),
        background_tasks=background_tasks,
    )

    return DocumentIngestResponse(
        status_code=202,
        message="Document queued for indexing",
        data=DocumentIngestData(
            doc_id=doc.id,
            reference_id=doc.reference_id,
            status=status,
            message="Document queued for indexing",
            task_id=task_id,
        ),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    organization_id: UUID = Query(..., description="Organization to list documents for"),
    status: Optional[str] = Query(None, pattern="^(draft|processing|indexed|failed)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DocumentService(base_deps)
    items, total = await service.list_documents(
        workspace_id=organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse.create(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        message="Documents retrieved successfully",
    )


@router.get("/ingestion-status/{document_id}", response_model=SuccessDataResponse[dict])
async def get_document_ingestion_status(
    document_id: UUID,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DocumentService(base_deps)
    status = await service.get_document_status(document_id)
    return SuccessDataResponse(
        status_code=200,
        message="Document ingestion status retrieved successfully",
        data={"document_id": str(document_id), "status": status},
    )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    """Standalone semantic search for debugging without LLM."""
    from engine.modules.assistant.tools.implementations.rag_search import RAGSearchTool

    tool = RAGSearchTool()
    organization_id = (
        str(request.organization_ids[0]) if request.organization_ids else None
    )
    chunks = await tool._search_async(
        query=request.query,
        organization_id=organization_id,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
    )
    results = [
        DocumentSearchChunk(
            text=c["text"],
            title=c["title"],
            reference_id=c["reference_id"],
            similarity=c.get("similarity"),
            vector_score=c.get("vector_score"),
            text_score=c.get("text_score"),
        )
        for c in chunks
    ]
    return DocumentSearchResponse(
        status_code=200,
        message="Document search completed",
        data=results,
    )


@router.get("/{id}", response_model=DocumentDataResponse)
async def get_document(
    id: UUID,
    organization_id: UUID = Query(..., description="Organization the document belongs to"),
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DocumentService(base_deps)
    result = await service.get_document(id, organization_id)
    return DocumentDataResponse(data=result, message="Document retrieved successfully")


@router.patch("/{id}", response_model=DocumentDataResponse)
async def update_document(
    id: UUID,
    organization_id: UUID = Query(..., description="Organization the document belongs to"),
    request: DocumentUpdateMetadataRequest = ...,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DocumentService(base_deps)
    result = await service.update_document(id, organization_id, request)
    return DocumentDataResponse(data=result, message="Document updated successfully")


@router.delete("/{id}", response_model=DocumentSimpleResponse)
async def delete_document(
    id: UUID,
    base_deps: BaseDeps = Depends(get_base_deps),
    current_user=Depends(get_current_user),
):
    service = DocumentService(base_deps)
    await service.delete_document(id)
    return DocumentSimpleResponse(status_code=200, message="Document deleted successfully")
