import asyncio
import logging
from datetime import datetime, timezone, timedelta
from engine.shared.db.session import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from engine.shared.models.connector_model import Connector
from engine.shared.models.credential_model import Credential
from engine.shared.models.drive_document_model import DriveDocument
from engine.shared.integrations.google_drive_client import GoogleDriveClient
from engine.modules.drive_documents.drive_documents_service import DriveDocumentService
from engine.pipelines.ingestion.sync_drive import ingest_drive_file

logger = logging.getLogger(__name__)


async def _sync_drive_for_workspace(
    session, connector: Connector, credential: Credential
):
    try:
        if not credential.auth_data:
            return

        connector.sync_status = "syncing"
        await session.commit()

        client = GoogleDriveClient(auth_data=credential.auth_data)

        # We look for files modified in the last 10 minutes to cover our polling interval
        # In a robust system, we would track the last_sync_time per workspace.
        # For testing, remove the 10-minute threshold so we get all files
        query = "mimeType != 'application/vnd.google-apps.folder'"

        # Add standard filter to exclude unsupported
        query += (
            " and mimeType != 'application/vnd.google-apps.shortcut'"
            " and mimeType != 'application/vnd.google-apps.form'"
            " and mimeType != 'application/vnd.google-apps.site'"
            " and mimeType != 'application/vnd.google-apps.map'"
        )

        files = client.list_files(query=query)
        if not files:
            connector.sync_status = "synced"
            from sqlalchemy import func

            connector.last_synced_at = func.now()
            await session.commit()
            return

        logger.info(
            f"Drive Sync: Found {len(files)} updated files for workspace {connector.organization_id}"
        )

        service = DriveDocumentService(session)
        credential_id = connector.id
        for file in files:
            await ingest_drive_file(
                file,
                connector.organization_id,
                client,
                service,
                credential_id=credential_id,
            )

        # Clean up orphaned documents (files deleted from Drive)
        returned_ids = {f["id"] for f in files}
        stored_result = await session.execute(
            select(DriveDocument.drive_file_id).where(
                DriveDocument.workspace_id == connector.organization_id,
                DriveDocument.status == "indexed",
            )
        )
        stored_ids = {row[0] for row in stored_result.all()}
        orphan_ids = stored_ids - returned_ids
        if orphan_ids:
            logger.info(
                f"[DRIVE_SYNC] Deleted file(s) detected: {len(orphan_ids)} orphan(s) for workspace {connector.organization_id}"
            )
            for orphan_file_id in orphan_ids:
                logger.info(
                    f"[DRIVE_SYNC] Removing vectors for drive_file_id={orphan_file_id}"
                )
                logger.info(
                    f"[DRIVE_SYNC] Removing metadata for drive_file_id={orphan_file_id}"
                )
                await service.delete_by_drive_file_id(
                    orphan_file_id, connector.organization_id
                )
            # Invalidate semantic cache
            from engine.modules.assistant.semantic_cache import SemanticCacheService

            await SemanticCacheService.invalidate_workspace_cache(
                session, connector.organization_id
            )
            logger.info(
                f"[DRIVE_SYNC] Cleanup completed for workspace {connector.organization_id} — semantic cache invalidated"
            )
        else:
            logger.info(
                f"[DRIVE_SYNC] No deleted files detected for workspace {connector.organization_id}"
            )

        if files:
            logger.info(
                f"[DRIVE_SYNC] Processed {len(files)} files, removed {len(orphan_ids)} orphans for workspace {connector.organization_id}"
            )
        else:
            logger.info(
                f"[DRIVE_SYNC] No files returned from Drive — orphans cleaned up for workspace {connector.organization_id}"
            )
            pending_orphans = stored_ids - set()
            if pending_orphans:
                logger.info(
                    f"[DRIVE_SYNC] Removing all stored documents (all files deleted from Drive) for workspace {connector.organization_id}"
                )
                for file_id in pending_orphans:
                    await service.delete_by_drive_file_id(
                        file_id, connector.organization_id
                    )
                from engine.modules.assistant.semantic_cache import SemanticCacheService

                await SemanticCacheService.invalidate_workspace_cache(
                    session, connector.organization_id
                )
        connector.sync_status = "synced"
        from sqlalchemy import func

        connector.last_synced_at = func.now()
        await session.commit()

    except Exception as e:
        logger.error(
            f"Drive Sync failed for workspace {connector.organization_id}: {e}"
        )
        connector.sync_status = "failed"
        await session.commit()


async def run_drive_sync_poll():
    """Background task that polls Google Drive for changes every 5 minutes."""
    while True:
        try:
            logger.info("Starting Google Drive Sync Polling cycle...")
            async with AsyncSessionLocal() as session:
                # Find all enabled google_drive connectors with a valid credential mapped
                result = await session.execute(
                    select(Connector).where(
                        Connector.connector_id == "google_drive",
                        Connector.status == "enabled",
                        Connector.credential_id.isnot(None),
                    )
                )
                connectors = result.scalars().all()

                for connector in connectors:
                    # Fetch the credential
                    cred_res = await session.execute(
                        select(Credential).where(
                            Credential.id == connector.credential_id
                        )
                    )
                    credential = cred_res.scalars().first()

                    if credential:
                        await _sync_drive_for_workspace(session, connector, credential)

        except asyncio.CancelledError:
            logger.info("Google Drive Sync Poller stopped.")
            break
        except Exception as e:
            logger.error(f"Error in Drive Sync Poller loop: {e}")

        # Poll every 5 minutes
        await asyncio.sleep(300)
