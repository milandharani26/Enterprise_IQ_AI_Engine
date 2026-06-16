"""Background document indexing: load -> chunk -> embed -> save (pgvector)."""

import logging
import traceback
from uuid import UUID

from sqlalchemy import select

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.document_model import Document
from engine.modules.documents.documents_service import DocumentService

logger = logging.getLogger(__name__)


def _get_settings():
    from engine.shared.config.settings import get_settings
    return get_settings()


async def run_index_document_task(doc_id: UUID, workspace_id: UUID) -> None:
    """Background task: set processing -> load -> chunk -> embed -> save chunks -> set indexed."""
    settings = _get_settings()
    service = None

    logger.info("[INDEXING] Starting index task for doc_id=%s workspace=%s", doc_id, workspace_id)

    async with AsyncSessionLocal() as db:
        try:
            service = DocumentService(db)

            result = await db.execute(
                select(Document).where(
                    Document.id == doc_id,
                    Document.workspace_id == workspace_id,
                    Document.deleted_at.is_(None),
                )
            )
            doc = result.scalars().first()
            if not doc:
                logger.error("[INDEXING] Document %s not found", doc_id)
                return

            source_url = doc.source_url
            if not source_url:
                await service.set_processing_status(
                    doc_id, workspace_id, "failed", error="No source_url on document"
                )
                return

            await service.set_processing_status(doc_id, workspace_id, "processing")

            content, loader_metadata = await service.load_document(source_url)
            content = content or ""

            from engine.pipelines.ingestion.services.chunking_service import get_chunking_service
            from engine.pipelines.ingestion.services.embedding_service import EmbeddingService

            chunking = get_chunking_service(
                chunk_size_tokens=settings.chunk_size_tokens,
                chunk_overlap_tokens=settings.chunk_overlap_tokens,
                max_chunk_size_tokens=settings.max_chunk_size_tokens,
            )
            chunks_data = chunking.create_chunks_with_llamaindex(
                content, doc_id, workspace_id, loader_metadata=loader_metadata
            )

            if not chunks_data:
                await service.set_processing_status(doc_id, workspace_id, "indexed")
                return

            embedding_service = EmbeddingService()
            chunk_texts = [c.get("text", "") for c in chunks_data]

            try:
                vectors = await embedding_service.embed_chunks(chunk_texts)
            except Exception as embed_err:
                logger.error("[INDEXING] Embedding failed: %s\n%s", embed_err, traceback.format_exc())
                await service.save_chunks(doc_id, workspace_id, chunks_data)
                await service.set_processing_status(
                    doc_id,
                    workspace_id,
                    "failed",
                    error=f"Chunked OK ({len(chunks_data)} chunks) but embedding failed: {embed_err}",
                )
                return

            for i, chunk in enumerate(chunks_data):
                if i < len(vectors):
                    chunk["embedding"] = vectors[i]
                    chunk["embedding_model"] = embedding_service.model
                else:
                    chunk["embedding"] = None
                    chunk["embedding_model"] = None

            await service.save_chunks(doc_id, workspace_id, chunks_data)
            await service.set_processing_status(doc_id, workspace_id, "indexed")
            logger.info(
                "[INDEXING] DONE — doc=%s, %d chunks indexed",
                doc_id,
                len(chunks_data),
            )

        except Exception as e:
            logger.error(
                "[INDEXING] FAILED for doc=%s\nError: %s\nTraceback:\n%s",
                doc_id,
                e,
                traceback.format_exc(),
            )
            if service:
                try:
                    await service.set_processing_status(
                        doc_id, workspace_id, "failed", error=str(e)[:2000]
                    )
                except Exception as set_err:
                    logger.exception("Failed to set status to failed: %s", set_err)


def schedule_index_document(
    doc_id: UUID,
    workspace_id: UUID,
    reference_id: str = "",
    background_tasks=None,
) -> str | None:
    """
    Queue indexing via Celery (if enabled) or FastAPI BackgroundTasks.
    Returns Celery task id when Celery is used, else None.
    """
    settings = _get_settings()
    ref = reference_id or str(doc_id)

    if getattr(settings, "use_celery_for_indexing", False):
        from engine.pipelines.ingestion.celery_tasks import index_document

        result = index_document.delay(str(doc_id), str(workspace_id), ref)
        return result.id

    if background_tasks is not None and getattr(settings, "enable_async_indexing", True):
        background_tasks.add_task(run_index_document_task, doc_id, workspace_id)
        return None

    raise RuntimeError("background_tasks required when Celery indexing is disabled")
