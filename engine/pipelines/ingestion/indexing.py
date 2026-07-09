"""Background document indexing: load -> chunk -> embed -> save (pgvector)."""

import asyncio
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
    """
    Background task: set processing -> load -> chunk -> embed -> save chunks -> set indexed.
    
    This function is designed to be resilient:
    - Catches all errors and updates document status to 'failed' with error details
    - Times out long-running operations
    - Tracks progress through logging
    """
    settings = _get_settings()
    service = None
    doc_load_timeout = getattr(settings, "document_load_timeout_seconds", 300)  # 5 min default

    logger.info(
        "[INDEXING] ▶️  START: doc_id=%s, workspace=%s",
        doc_id, workspace_id
    )

    async with AsyncSessionLocal() as db:
        try:
            service = DocumentService(db)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 1. Load and validate document
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            result = await db.execute(
                select(Document).where(
                    Document.id == doc_id,
                    Document.workspace_id == workspace_id,
                    Document.deleted_at.is_(None),
                )
            )
            doc = result.scalars().first()
            if not doc:
                logger.error("[INDEXING] ✗ Document not found: doc_id=%s", doc_id)
                return

            source_url = doc.source_url
            if not source_url:
                error_msg = "No source_url configured on document"
                logger.error("[INDEXING] ✗ %s", error_msg)
                await service.set_processing_status(doc_id, workspace_id, "failed", error=error_msg)
                return

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 2. Mark as processing
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            await service.set_processing_status(doc_id, workspace_id, "processing")
            logger.info("[INDEXING] ⏳ Status set to 'processing'")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 3. Load document with timeout
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                logger.info("[INDEXING] 📥 Loading from: %s (timeout=%ds)", source_url, doc_load_timeout)
                content, loader_metadata = await asyncio.wait_for(
                    service.load_document(source_url),
                    timeout=doc_load_timeout
                )
                content = content or ""
                logger.info("[INDEXING] ✓ Loaded %d chars", len(content))
            except asyncio.TimeoutError:
                error_msg = f"Document loading timed out after {doc_load_timeout}s"
                logger.error("[INDEXING] ✗ %s", error_msg)
                await service.set_processing_status(doc_id, workspace_id, "failed", error=error_msg)
                return

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 4. Chunk document
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
                logger.info("[INDEXING] ✓ No chunks created (empty document); marking indexed")
                await service.set_processing_status(doc_id, workspace_id, "indexed")
                return

            logger.info("[INDEXING] ✓ Created %d chunks", len(chunks_data))

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 5. Embed chunks with error recovery
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            embedding_service = EmbeddingService(org_id=workspace_id)
            chunk_texts = [c.get("text", "") for c in chunks_data]

            try:
                logger.info("[INDEXING] 🧠 Embedding %d chunks...", len(chunk_texts))
                vectors = await embedding_service.embed_chunks(chunk_texts)
                logger.info("[INDEXING] ✓ Embeddings completed: %d vectors", len(vectors))
            except Exception as embed_err:
                error_detail = f"Chunked OK ({len(chunks_data)} chunks) but embedding failed: {str(embed_err)[:500]}"
                logger.error("[INDEXING] ✗ Embedding error: %s", embed_err)
                
                # Save chunks anyway (allows partial progress)
                try:
                    await service.save_chunks(doc_id, workspace_id, chunks_data)
                    logger.warning("[INDEXING] ℹ️ Saved %d chunks without embeddings", len(chunks_data))
                except Exception as save_err:
                    logger.error("[INDEXING] ✗ Failed to save chunks: %s", save_err)
                
                await service.set_processing_status(doc_id, workspace_id, "failed", error=error_detail)
                return

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 6. Attach embeddings to chunks
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            for i, chunk in enumerate(chunks_data):
                if i < len(vectors):
                    chunk["embedding"] = vectors[i]
                    chunk["embedding_model"] = embedding_service.model
                else:
                    logger.warning("[INDEXING] ⚠️ Chunk %d missing embedding vector", i)
                    chunk["embedding"] = None
                    chunk["embedding_model"] = None

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 7. Save to database
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            saved_count = await service.save_chunks(doc_id, workspace_id, chunks_data)
            logger.info("[INDEXING] 💾 Saved %d chunks to pgvector", saved_count)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 8. Mark as complete
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            await service.set_processing_status(doc_id, workspace_id, "indexed")
            logger.info(
                "[INDEXING] ✅ COMPLETE: doc=%s, %d chunks indexed, status=indexed",
                doc_id,
                len(chunks_data),
            )

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 9. Clean up uploaded file from disk (best-effort)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                deleted = await service.cleanup_uploaded_file(doc_id, workspace_id)
                if deleted:
                    logger.info("[INDEXING] 🗑️  Uploaded file cleaned up for doc=%s", doc_id)
            except Exception as cleanup_err:
                logger.warning(
                    "[INDEXING] ⚠️  File cleanup failed for doc=%s: %s (non-fatal)",
                    doc_id, cleanup_err,
                )

        except Exception as e:
            logger.error(
                "[INDEXING] ❌ FAILED for doc=%s\n"
                "Error Type: %s\n"
                "Error: %s\n"
                "Traceback:\n%s",
                doc_id,
                type(e).__name__,
                e,
                traceback.format_exc(),
            )
            if service:
                try:
                    error_msg = f"{type(e).__name__}: {str(e)[:500]}"
                    await service.set_processing_status(doc_id, workspace_id, "failed", error=error_msg)
                    logger.info("[INDEXING] Status updated to 'failed' with error details")
                except Exception as set_err:
                    logger.exception("[INDEXING] Failed to update status to failed: %s", set_err)


def schedule_index_document(
    doc_id: UUID,
    workspace_id: UUID,
    reference_id: str = "",
    background_tasks=None,
) -> str | None:
    """
    Queue indexing via Celery (if enabled) or FastAPI BackgroundTasks.
    
    Strategy (in order of preference):
    1. Celery (USE_CELERY_FOR_INDEXING=true) — production-grade, reliable retry, monitoring
    2. BackgroundTasks (if available) — built-in FastAPI, simple, but lifecycle-dependent
    3. Error if neither available
    
    Returns: Celery task id (str) if Celery is used, else None
    """
    settings = _get_settings()
    ref = reference_id or str(doc_id)
    use_celery = getattr(settings, "use_celery_for_indexing", False)
    enable_async = getattr(settings, "enable_async_indexing", True)

    # ═══════════════════════════════════════════════════════════════════
    # Strategy 1: Celery (Preferred for production)
    # ═══════════════════════════════════════════════════════════════════
    if use_celery:
        try:
            from engine.pipelines.ingestion.celery_tasks import index_document
            result = index_document.delay(str(doc_id), str(workspace_id), ref)
            logger.info(
                "[CELERY] Document indexing queued: doc_id=%s, task_id=%s",
                doc_id, result.id
            )
            return result.id
        except Exception as celery_err:
            logger.error(
                "[CELERY] Failed to queue indexing: %s. Falling back to BackgroundTasks.",
                celery_err
            )
            use_celery = False  # Fall through to BackgroundTasks

    # ═══════════════════════════════════════════════════════════════════
    # Strategy 2: FastAPI BackgroundTasks (Fallback)
    # ═══════════════════════════════════════════════════════════════════
    if background_tasks is not None and enable_async:
        if not use_celery:
            logger.warning(
                "[BACKGROUND_TASKS] Using FastAPI BackgroundTasks (less reliable than Celery). "
                "For production, set USE_CELERY_FOR_INDEXING=true and run celery workers."
            )
        
        # Wrap task execution with error handling
        async def _indexed_task_wrapper():
            try:
                await run_index_document_task(doc_id, workspace_id)
                logger.info(
                    "[BACKGROUND_TASKS] Indexing completed: doc_id=%s, workspace=%s",
                    doc_id, workspace_id
                )
            except Exception as task_err:
                logger.exception(
                    "[BACKGROUND_TASKS] Indexing failed for doc_id=%s: %s",
                    doc_id, task_err
                )
                # Attempt to mark document as failed in DB
                try:
                    from engine.shared.db.session import AsyncSessionLocal
                    async with AsyncSessionLocal() as db:
                        from engine.modules.documents.documents_service import DocumentService
                        svc = DocumentService(db)
                        await svc.set_processing_status(
                            doc_id, workspace_id, "failed",
                            error=f"Background task error: {str(task_err)[:500]}"
                        )
                except Exception as update_err:
                    logger.error(
                        "[BACKGROUND_TASKS] Failed to mark doc as failed: %s",
                        update_err
                    )
                raise
        
        background_tasks.add_task(_indexed_task_wrapper)
        logger.info(
            "[BACKGROUND_TASKS] Document indexing queued: doc_id=%s",
            doc_id
        )
        return None

    # ═══════════════════════════════════════════════════════════════════
    # No valid scheduling strategy available
    # ═══════════════════════════════════════════════════════════════════
    error_msg = (
        "Cannot schedule indexing: "
        f"use_celery={use_celery}, background_tasks={'available' if background_tasks else 'unavailable'}, "
        f"enable_async={enable_async}. "
        "Either provide background_tasks or set USE_CELERY_FOR_INDEXING=true."
    )
    logger.error("[SCHEDULING] %s", error_msg)
    raise RuntimeError(error_msg)
