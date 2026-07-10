import asyncio
import logging
from datetime import datetime, timezone, timedelta
from engine.shared.db.session import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from engine.shared.models.connector_model import Connector
from engine.shared.models.credential_model import Credential
from engine.shared.integrations.google_drive_client import GoogleDriveClient
from engine.modules.drive_documents.drive_documents_service import DriveDocumentService
from engine.pipelines.ingestion.sync_drive import ingest_drive_file

logger = logging.getLogger(__name__)

async def _sync_drive_for_workspace(session, connector: Connector, credential: Credential):
    try:
        if not credential.auth_data:
            return
            
        connector.sync_status = "syncing"
        await session.commit()
            
        client = GoogleDriveClient(auth_data=credential.auth_data)
        
        # We look for files modified in the last 10 minutes to cover our polling interval
        # For robust deletion detection, we fetch all valid files
        query = "trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        
        # Add standard filter to exclude unsupported
        query += (
            " and mimeType != 'application/vnd.google-apps.shortcut'"
            " and mimeType != 'application/vnd.google-apps.form'"
            " and mimeType != 'application/vnd.google-apps.site'"
            " and mimeType != 'application/vnd.google-apps.map'"
        )

        files = client.list_files(query=query, fetch_all=True)
        if not files:
            connector.sync_status = "synced"
            from sqlalchemy import func
            connector.last_synced_at = func.now()
            await session.commit()
            return

        logger.info(f"Drive Sync: Found {len(files)} updated files for workspace {connector.organization_id}")
        
        service = DriveDocumentService(session)
        current_drive_ids = set()
        for file in files:
            file_id = file.get("id")
            if file_id:
                current_drive_ids.add(file_id)
            await ingest_drive_file(file, connector.organization_id, client, service)
            
        # Detect and delete orphaned files (deleted in Drive)
        from engine.shared.models.drive_document_model import DriveDocument
        db_docs_result = await session.execute(
            select(DriveDocument.drive_file_id)
            .where(DriveDocument.workspace_id == connector.organization_id)
        )
        db_drive_ids = {row[0] for row in db_docs_result.all() if row[0]}
        
        deleted_drive_ids = db_drive_ids - current_drive_ids
        if deleted_drive_ids:
            logger.info(f"Drive Sync: Deleting {len(deleted_drive_ids)} orphaned files for workspace {connector.organization_id}")
            await service.delete_by_drive_file_ids(connector.organization_id, list(deleted_drive_ids))
            
            # Invalidate semantic cache if applicable
            try:
                from engine.modules.assistant.semantic_cache import SemanticCacheService
                await SemanticCacheService.invalidate_workspace_cache(session, connector.organization_id)
            except ImportError:
                pass
            
        connector.sync_status = "synced"
        from sqlalchemy import func
        connector.last_synced_at = func.now()
        await session.commit()
            
    except Exception as e:
        logger.error(f"Drive Sync failed for workspace {connector.organization_id}: {e}")
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
                    select(Connector)
                    .where(Connector.connector_id == 'google_drive', Connector.credential_id.isnot(None))
                )
                connectors = result.scalars().all()
                
                for connector in connectors:
                    # Fetch the credential
                    cred_res = await session.execute(
                        select(Credential).where(
                            Credential.id == connector.credential_id,
                            Credential.status == "Active"
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
