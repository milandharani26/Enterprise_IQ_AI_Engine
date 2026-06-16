"""Celery task: document indexing (load -> chunk -> embed -> pgvector)."""

import asyncio
import logging
from uuid import UUID

from engine.pipelines.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_WORKER_EVENT_LOOP: asyncio.AbstractEventLoop | None = None


def _run_async_in_worker(coro):
    """Run async coroutines on a stable per-process event loop."""
    global _WORKER_EVENT_LOOP
    if _WORKER_EVENT_LOOP is None or _WORKER_EVENT_LOOP.is_closed():
        _WORKER_EVENT_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_WORKER_EVENT_LOOP)
    return _WORKER_EVENT_LOOP.run_until_complete(coro)


def _index_document_impl(self, doc_id: str, workspace_id: str, reference_id: str = ""):
    from engine.pipelines.ingestion.indexing import run_index_document_task

    logger.info(
        "[Task %s] Starting indexing doc_id=%s workspace=%s",
        self.request.id,
        doc_id,
        workspace_id,
    )
    try:
        _run_async_in_worker(
            run_index_document_task(UUID(doc_id), UUID(workspace_id))
        )
        return {"status": "indexed", "doc_id": doc_id, "reference_id": reference_id}
    except Exception as exc:
        logger.exception("[Task %s] Indexing failed: %s", self.request.id, exc)
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(countdown=countdown, exc=exc) from exc
        return {
            "status": "failed",
            "doc_id": doc_id,
            "error": str(exc),
            "message": f"Indexing failed after {self.max_retries} retries",
        }


@celery_app.task(bind=True, max_retries=3, name="engine.ingestion.celery_tasks.index_document")
def index_document(self, doc_id: str, workspace_id: str, reference_id: str = ""):
    return _index_document_impl(self, doc_id, workspace_id, reference_id)


@celery_app.task(bind=True, max_retries=3, name="ingestion.celery_tasks.index_document")
def index_document_legacy(self, doc_id: str, workspace_id: str, reference_id: str = ""):
    return _index_document_impl(self, doc_id, workspace_id, reference_id)
