"""Celery task: document indexing (load -> chunk -> embed -> pgvector)."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so the top-level `shared` package
# (shared/logging, etc.) is importable by the Celery worker process.
_project_root = str(Path(__file__).resolve().parents[3])
print(f"DEBUG: _project_root is: {_project_root}")
print(f"DEBUG: sys.path is: {sys.path}")
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
    print("DEBUG: Inserted _project_root into sys.path")
print(f"DEBUG: sys.path after insertion is: {sys.path}")

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
    import sys
    from pathlib import Path
    _project_root = str(Path(__file__).resolve().parents[3])
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

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
