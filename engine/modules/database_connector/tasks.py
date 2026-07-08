from uuid import UUID

from engine.pipelines.tasks.celery_app import celery_app

from shared.logging import get_logger
logger = get_logger("database_tasks")

@celery_app.task(bind=True, max_retries=3)
def sync_schema_task(self, connection_id: str, organization_id: str):
    """
    Background task to crawl the database schema and generate embeddings.
    """
    import asyncio
    from engine.shared.db.session import AsyncSessionLocal
    from engine.modules.database_connector.schema_crawler import SchemaCrawlerService
    
    async def run_sync():
        async with AsyncSessionLocal() as db:
            crawler = SchemaCrawlerService()
            await crawler.sync_database_schema(db, UUID(connection_id), UUID(organization_id))

    try:
        asyncio.run(run_sync())
        return {"status": "success", "connection_id": connection_id}
    except Exception as exc:
        logger.error(f"Error syncing schema for connection {connection_id}: {exc}")
        self.retry(exc=exc, countdown=60)


async def run_sync_schema_task(connection_id: UUID, organization_id: UUID) -> None:
    """
    Standard async runner for schema syncing, bypassing Celery.
    """
    from engine.shared.db.session import AsyncSessionLocal
    from engine.modules.database_connector.schema_crawler import SchemaCrawlerService
    
    logger.info(f"[DB_CONNECTOR] Starting schema sync for connection {connection_id}")
    async with AsyncSessionLocal() as db:
        try:
            crawler = SchemaCrawlerService()
            await crawler.sync_database_schema(db, connection_id, organization_id)
            logger.info(f"[DB_CONNECTOR] Schema sync completed for connection {connection_id}")
        except Exception as e:
            logger.error(f"[DB_CONNECTOR] Schema sync failed for connection {connection_id}: {e}")


def schedule_sync_schema(
    connection_id: UUID,
    organization_id: UUID,
    background_tasks = None,
) -> str | None:
    """
    Queue schema sync via Celery (if enabled) or FastAPI BackgroundTasks.
    """
    from engine.shared.config.settings import get_settings
    settings = get_settings()

    if getattr(settings, "use_celery_for_indexing", False):
        logger.info(f"[DB_CONNECTOR] Queuing schema sync via Celery for connection {connection_id}")
        result = sync_schema_task.delay(str(connection_id), str(organization_id))
        return result.id

    if background_tasks is not None:
        logger.info(f"[DB_CONNECTOR] Queuing schema sync via FastAPI BackgroundTasks for connection {connection_id}")
        background_tasks.add_task(run_sync_schema_task, connection_id, organization_id)
        return None

    # Fallback if neither Celery nor BackgroundTasks is provided (e.g. CLI or direct service call)
    logger.info(f"[DB_CONNECTOR] Running schema sync on event loop for connection {connection_id}")
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_sync_schema_task(connection_id, organization_id))
    except RuntimeError:
        asyncio.run(run_sync_schema_task(connection_id, organization_id))
    return None

