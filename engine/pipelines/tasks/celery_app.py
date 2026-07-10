"""Celery app for async document indexing (Redis broker)."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so the top-level `shared` package
# (shared/logging, etc.) is importable by the Celery worker process.
_project_root = str(Path(__file__).resolve().parents[3])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from celery import Celery


def _get_broker_and_backend():
    from engine.shared.config.settings import get_settings

    s = get_settings()
    return s.celery_broker_url, s.celery_result_backend


broker_url, result_backend = _get_broker_and_backend()

celery_app = Celery(
    "engine",
    broker=broker_url,
    backend=result_backend,
    include=[
        "engine.pipelines.ingestion.celery_tasks",
        "engine.modules.database_connector.tasks"
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=3600,
)

from engine.shared.config.settings import get_settings

s = get_settings()
_mapping = {
    "celery_task_time_limit": "task_time_limit",
    "celery_task_soft_time_limit": "task_soft_time_limit",
    "celery_task_max_retries": "task_max_retries",
    "celery_task_default_retry_delay": "task_default_retry_delay",
    "celery_worker_prefetch_multiplier": "worker_prefetch_multiplier",
    "celery_worker_max_tasks_per_child": "worker_max_tasks_per_child",
    "celery_result_expires": "result_expires",
}
for our_key, celery_key in _mapping.items():
    val = getattr(s, our_key, None)
    if val is not None:
        celery_app.conf[celery_key] = val
