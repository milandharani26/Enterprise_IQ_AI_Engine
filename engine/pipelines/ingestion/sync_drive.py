"""Google Drive Ingestion Pipeline.

This module provides the orchestrator to fetch files from Google Drive,
process them through the existing chunking and embedding pipelines,
and save them into the drive_documents architecture.
"""

import os
import asyncio
import logging
import tempfile
from typing import Optional, List
from uuid import UUID

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.integrations.google_drive_client import GoogleDriveClient
from engine.shared.schemas.drive_document_schema import DriveDocumentIngestRequest
from engine.modules.drive_documents.drive_documents_service import DriveDocumentService
from engine.pipelines.ingestion.loaders.registry import LoaderRegistry
from engine.pipelines.ingestion.services.chunking_service import get_chunking_service
from engine.pipelines.ingestion.services.embedding_service import EmbeddingService
from engine.shared.config.settings import get_settings

logger = logging.getLogger(__name__)


def map_google_mime_type(mime_type: str) -> str:
    """Map Google Workspace mime types to standard export mime types."""
    if not mime_type.startswith('application/vnd.google-apps.'):
        return mime_type

    if "document" in mime_type:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif "spreadsheet" in mime_type:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif "presentation" in mime_type:
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    
    # Default export for other G-Suite apps
    return "application/pdf"


async def ingest_drive_file(
    file_info: dict, 
    workspace_id: UUID,
    drive_client: GoogleDriveClient,
    service: DriveDocumentService,
    credential_id: Optional[UUID] = None,
) -> None:
    """Download, chunk, embed, and save a single drive file."""
    doc_id = None
    try:
        from datetime import datetime
        from sqlalchemy import select, and_
        from engine.shared.models.drive_document_model import DriveDocument
        
        drive_file_id = file_info.get("id")
        title = file_info.get("name", "Untitled")
        mime_type = file_info.get("mimeType", "")
        
        last_modified_str = file_info.get("modifiedTime")
        last_modified_dt = None
        if last_modified_str:
            try:
                # Parse and strip timezone to avoid asyncpg naive/aware mismatch
                parsed = datetime.fromisoformat(last_modified_str.replace('Z', '+00:00'))
                last_modified_dt = parsed.replace(tzinfo=None)
            except:
                pass

        # Check if we can skip processing
        existing = (
            await service.db.execute(
                select(DriveDocument).where(
                    and_(
                        DriveDocument.workspace_id == workspace_id,
                        DriveDocument.drive_file_id == drive_file_id,
                    )
                )
            )
        ).scalars().first()

        if existing and existing.last_modified_in_drive and last_modified_dt:
            if existing.last_modified_in_drive.timestamp() == last_modified_dt.timestamp() and existing.status in ["indexed", "failed"]:
                logger.debug(f"[Drive Sync] Skipping '{title}' - hasn't changed since last sync (Status: {existing.status}).")
                return
            else:
                logger.info(f"[DRIVE_SYNC] Modified file detected: drive_file_id={drive_file_id} title='{title}'")
        else:
            logger.info(f"[DRIVE_SYNC] New file detected: drive_file_id={drive_file_id} title='{title}'")

        # 1. Register Document as Processing
        owners = file_info.get("owners", [])
        owner_email = owners[0].get("emailAddress") if owners else None

        ingest_req = DriveDocumentIngestRequest(
            drive_file_id=drive_file_id,
            title=title,
            mime_type=mime_type,
            web_view_link=file_info.get("webViewLink"),
            web_content_link=file_info.get("webContentLink"),
            owner_email=owner_email,
            file_size_bytes=int(file_info.get("size", 0)) if file_info.get("size") else None,
            last_modified_in_drive=last_modified_dt,
            credential_id=credential_id,
        )
        
        doc = await service.create_drive_document(ingest_req, workspace_id)
        doc_id = doc.id
        await service.set_processing_status(doc_id, workspace_id, "processing")
        logger.info(f"[Drive Sync] Started processing doc {doc_id} (Drive ID: {drive_file_id})")

        # 2. Download from Google Drive
        logger.debug(f"[Drive Sync] Downloading {title}...")
        raw_bytes = await asyncio.to_thread(drive_client.download_file, drive_file_id, mime_type)

        # 3. Find correct loader
        export_mime_type = map_google_mime_type(mime_type)
        try:
            loader = LoaderRegistry.get_loader(export_mime_type)
        except Exception as e:
            logger.warning(f"Unsupported mime_type {export_mime_type} for {title}")
            await service.set_processing_status(doc_id, workspace_id, "failed", error=str(e))
            return

        # 4. Save to temp file and load
        content = ""
        loader_metadata = {}
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        try:
            import pathlib
            file_uri = pathlib.Path(tmp_path).absolute().as_uri()
            content, loader_metadata = await loader.load_from_url(file_uri)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        if not content:
            await service.set_processing_status(doc_id, workspace_id, "failed", error="Extracted content is empty")
            return

        # 5. Chunk Content
        settings = get_settings()
        chunking = get_chunking_service(
            chunk_size_tokens=settings.chunk_size_tokens,
            chunk_overlap_tokens=settings.chunk_overlap_tokens,
            max_chunk_size_tokens=settings.max_chunk_size_tokens,
        )
        chunks_data = chunking.create_chunks_with_llamaindex(content, doc_id, workspace_id, loader_metadata=loader_metadata)

        if not chunks_data:
            await service.set_processing_status(doc_id, workspace_id, "indexed")
            return

        # 6. Embed Chunks
        embedding_service = EmbeddingService()
        chunk_texts = [c.get("text", "") for c in chunks_data]
        try:
            vectors = await embedding_service.embed_chunks(chunk_texts)
        except Exception as embed_err:
            logger.error(f"[Drive Sync] Embedding failed for {doc_id}: {embed_err}")
            await service.save_chunks(doc_id, workspace_id, chunks_data)
            await service.set_processing_status(doc_id, workspace_id, "failed", error=str(embed_err))
            return

        for i, chunk in enumerate(chunks_data):
            if i < len(vectors):
                chunk["embedding"] = vectors[i]
                chunk["embedding_model"] = embedding_service.model
            else:
                chunk["embedding"] = None
                chunk["embedding_model"] = None

        # 7. Save and Mark Complete
        await service.save_chunks(doc_id, workspace_id, chunks_data)
        await service.set_processing_status(doc_id, workspace_id, "indexed")
        logger.info(f"[Drive Sync] DONE - doc {doc_id} indexed ({len(chunks_data)} chunks)")

    except Exception as e:
        logger.error(f"[Drive Sync] FAILED for drive_file_id {file_info.get('id')}: {e}")
        if doc_id:
            try:
                await service.set_processing_status(doc_id, workspace_id, "failed", error=str(e)[:2000])
            except:
                pass


async def sync_drive_files(query: str = None, limit: int = 50) -> int:
    """Fetch files from Drive for all active connectors and orchestrate ingestion pipeline."""
    try:
        from engine.shared.models.connector_model import Connector
        from engine.shared.models.credential_model import Credential
        from engine.shared.models.drive_document_model import DriveDocument
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            # 1. Find all active connectors for google_drive
            result = await db.execute(
                select(Connector, Credential)
                .join(Credential, Connector.credential_id == Credential.id)
                .where(Connector.connector_id == 'google_drive', Connector.status == 'enabled')
            )
            active_connectors = result.all()

            if not active_connectors:
                logger.info("No active Google Drive connectors found.")
                return 0

            service = DriveDocumentService(db)

            # 2. Loop through each active organization/connector
            for connector, credential in active_connectors:
                logger.info(f"Syncing Google Drive for Organization: {connector.organization_id}")
                workspace_id = str(connector.organization_id)

                # Check the shared workspace lock to avoid concurrent syncs
                # (e.g., this OAuth-triggered sync vs. the background poller).
                try:
                    from engine.shared.workers.drive_sync_worker import _syncing_workspaces
                    if workspace_id in _syncing_workspaces:
                        logger.info(
                            f"[sync_drive] Skipping workspace {workspace_id} — already being synced by worker."
                        )
                        continue
                    _syncing_workspaces.add(workspace_id)
                except ImportError:
                    pass

                try:
                    drive_client = GoogleDriveClient(auth_data=credential.auth_data)
                    files = drive_client.list_files(query=query, page_size=limit)

                    # 3. Process files for this organization
                    for f in files:
                        await ingest_drive_file(f, connector.organization_id, drive_client, service, credential_id=connector.id)

                    # 4. Clean up orphaned documents (files deleted from Drive)
                    returned_ids = {f["id"] for f in files}
                    # Check ALL stored drive_file_ids for this workspace (any status).
                    # Previously only "indexed" docs were checked, leaving failed/draft/
                    # processing records from old sync runs as permanent ghost entries.
                    stored_result = await db.execute(
                        select(DriveDocument.drive_file_id).where(
                            DriveDocument.workspace_id == connector.organization_id,
                        )
                    )
                    stored_ids = {row[0] for row in stored_result.all()}
                    orphan_ids = stored_ids - returned_ids
                    if orphan_ids:
                        logger.info(f"[DRIVE_SYNC] Deleted file(s) detected: {len(orphan_ids)} orphan(s) for workspace {connector.organization_id}")
                        for orphan_file_id in orphan_ids:
                            logger.info(f"[DRIVE_SYNC] Removing vectors for drive_file_id={orphan_file_id}")
                            logger.info(f"[DRIVE_SYNC] Removing metadata for drive_file_id={orphan_file_id}")
                            await service.delete_by_drive_file_id(orphan_file_id, connector.organization_id)
                        # Invalidate semantic cache so assistants stop quoting deleted content
                        from engine.modules.assistant.semantic_cache import SemanticCacheService
                        await SemanticCacheService.invalidate_workspace_cache(db, connector.organization_id)
                        logger.info(f"[DRIVE_SYNC] Cleanup completed for workspace {connector.organization_id} — semantic cache invalidated")
                    else:
                        logger.info(f"[DRIVE_SYNC] No deleted files detected for workspace {connector.organization_id}")

                    if not files:
                        logger.info(f"[DRIVE_SYNC] No files returned from Drive — orphans cleaned up for workspace {connector.organization_id}")
                        pending_orphans = stored_ids - set()
                        if pending_orphans:
                            logger.info(f"[DRIVE_SYNC] Removing all stored documents (all files deleted from Drive) for workspace {connector.organization_id}")
                            for file_id in pending_orphans:
                                await service.delete_by_drive_file_id(file_id, connector.organization_id)
                            from engine.modules.assistant.semantic_cache import SemanticCacheService
                            await SemanticCacheService.invalidate_workspace_cache(db, connector.organization_id)
                        continue
                        
                except Exception as e:
                    logger.error(f"Failed to sync for org {connector.organization_id}: {e}")
                finally:
                    # Always release the workspace lock after this sync attempt
                    try:
                        from engine.shared.workers.drive_sync_worker import _syncing_workspaces
                        _syncing_workspaces.discard(workspace_id)
                    except ImportError:
                        pass


            return len(active_connectors)

    except Exception as e:
        logger.error(f"Failed to sync Google Drive files: {e}")
        return 0
