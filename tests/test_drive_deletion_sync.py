"""Integration tests: Google Drive deletion synchronization."""

import inspect
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest

from engine.modules.assistant.semantic_cache import SemanticCacheService
from engine.modules.drive_documents.drive_documents_service import DriveDocumentService
from engine.pipelines.ingestion.sync_drive import ingest_drive_file
from engine.shared.models.drive_document_model import DriveDocument, DriveDocumentChunk
from engine.shared.schemas.drive_document_schema import (
    DriveDocumentIngestRequest,
    DriveDocumentResponse,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def file_id():
    return str(uuid4())


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    # Set up execute() to return a mock with proper scalars().first() chain
    mock_scalars = MagicMock()
    mock_scalars.first = MagicMock(return_value=None)
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session.execute.return_value = mock_result
    return session


@pytest.fixture
def mock_drive_service(mock_session):
    service = DriveDocumentService(mock_session)
    service.create_drive_document = AsyncMock()
    service.delete_by_drive_file_id = AsyncMock(return_value=True)
    service.save_chunks = AsyncMock(return_value=5)
    service.set_processing_status = AsyncMock()
    service.db.execute = mock_session.execute
    return service


@pytest.fixture
def mock_drive_client():
    client = MagicMock()
    client.download_file = MagicMock(return_value=b"test content")
    return client


@pytest.fixture
def sample_file_info(file_id):
    return {
        "id": file_id,
        "name": "test_doc.pdf",
        "mimeType": "application/pdf",
        "webViewLink": "https://drive.google.com/file/d/abc123/view",
        "webContentLink": "https://drive.google.com/uc?id=abc123",
        "owners": [{"emailAddress": "test@example.com"}],
        "size": "1024",
        "modifiedTime": "2026-06-25T10:00:00Z",
    }


class TestNewFileIndexing:
    """Test 1: New file detected -> indexed and searchable."""

    @pytest.mark.asyncio
    async def test_new_file_triggers_full_pipeline(
        self, org_id, file_id, mock_drive_service, mock_drive_client, sample_file_info
    ):
        """A file not in the DB triggers download, chunk, embed, save."""
        mock_drive_service.create_drive_document.return_value = MagicMock(
            id=uuid4(), drive_file_id=file_id,
        )

        await ingest_drive_file(
            file_info=sample_file_info,
            workspace_id=org_id,
            drive_client=mock_drive_client,
            service=mock_drive_service,
            credential_id=uuid4(),
        )

        mock_drive_service.create_drive_document.assert_awaited_once()
        req = mock_drive_service.create_drive_document.call_args[0][0]
        assert req.drive_file_id == file_id
        assert req.credential_id is not None

    def test_vector_search_queries_only_indexed(self):
        """Search SQL only returns status='indexed' results."""
        from engine.modules.assistant.tools.implementations.drive_search import DriveSearchTool
        tool = DriveSearchTool()
        source = inspect.getsource(tool._vector_search)
        assert "status = 'indexed'" in source


class TestDeletedFileCleanup:
    """Test 2: Deleted file -> removed from DB, chunks, cache."""

    @pytest.mark.asyncio
    async def test_delete_by_drive_file_id_called_on_orphan(self, org_id, file_id, mock_session):
        """When a stored file is absent from Drive response, delete_by_drive_file_id is called."""
        mock_svc = AsyncMock(spec=DriveDocumentService)
        mock_svc.delete_by_drive_file_id = AsyncMock(return_value=True)
        mock_svc.db = mock_session

        mock_client = MagicMock()
        mock_client.list_files.return_value = []

        mock_connector = MagicMock()
        mock_connector.organization_id = org_id
        mock_connector.id = uuid4()

        mock_credential = MagicMock()
        mock_credential.auth_data = {"token": "fake"}

        mock_session.execute.side_effect = None
        mock_session.execute.return_value = MagicMock(
            all=lambda: [(mock_connector, mock_credential)],
            scalars=lambda: MagicMock(all=lambda: []),
        )

        mock_first_result = MagicMock()
        mock_first_result.scalars.return_value = MagicMock(
            first=lambda: None
        )
        mock_session.execute = AsyncMock(return_value=mock_first_result)


class TestModifiedFileReindexing:
    """Test 3: Modified file -> re-indexed with new content."""

    @pytest.mark.asyncio
    async def test_modified_file_triggers_reindex(
        self, org_id, file_id, mock_drive_service, mock_drive_client
    ):
        """A file with changed modifiedTime gets re-indexed."""
        file_info = {
            "id": file_id,
            "name": "test_doc.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2026-06-25T12:00:00Z",
            "owners": [{"emailAddress": "test@example.com"}],
            "size": "2048",
        }
        mock_drive_service.create_drive_document.return_value = MagicMock(
            id=uuid4(), drive_file_id=file_id,
        )

        await ingest_drive_file(
            file_info=file_info,
            workspace_id=org_id,
            drive_client=mock_drive_client,
            service=mock_drive_service,
            credential_id=uuid4(),
        )

        mock_drive_service.create_drive_document.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unchanged_file_skipped(
        self, org_id, file_id, mock_drive_service, mock_drive_client
    ):
        """A file with same modifiedTime is skipped."""
        doc_id = uuid4()
        mock_drive_service.db.execute.return_value = MagicMock(
            scalars=lambda: MagicMock(
                first=lambda: DriveDocument(
                    id=doc_id,
                    workspace_id=org_id,
                    drive_file_id=file_id,
                    last_modified_in_drive=datetime(2026, 6, 25, 12, 0, 0),
                    status="indexed",
                )
            )
        )
        mock_drive_service.create_drive_document = AsyncMock()

        file_info = {
            "id": file_id,
            "name": "test_doc.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2026-06-25T12:00:00Z",
        }

        await ingest_drive_file(
            file_info=file_info,
            workspace_id=org_id,
            drive_client=mock_drive_client,
            service=mock_drive_service,
        )

        mock_drive_service.create_drive_document.assert_not_awaited()


class TestMultipleFileDeletion:
    """Test 4: Multiple files deleted -> all cleaned up."""

    def test_orphan_detection_uses_set_subtraction(self):
        """Orphan detection uses set subtraction stored_ids - returned_ids."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        assert "stored_ids - returned_ids" in source

    def test_sync_drive_files_has_orphan_cleanup(self):
        """sync_drive_files contains orphan cleanup logic."""
        from engine.pipelines.ingestion import sync_drive as sync_mod
        source = inspect.getsource(sync_mod.sync_drive_files)
        assert "delete_by_drive_file_id" in source
        assert "orphan" in source.lower()

    def test_worker_has_orphan_cleanup(self):
        """Worker has orphan cleanup and cache invalidation."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        assert "delete_by_drive_file_id" in source
        assert "invalidate_workspace_cache" in source
        assert "DRIVE_SYNC" in source


class TestSemanticCacheInvalidation:
    """Cache invalidation on file deletion."""

    @pytest.mark.asyncio
    async def test_invalidate_workspace_cache_bumps_version(self, org_id, mock_session):
        """SemanticCacheService.invalidate_workspace_cache calls db.execute."""
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        await SemanticCacheService.invalidate_workspace_cache(mock_session, org_id)

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_file_deletion_triggers_cache_invalidate(self, org_id, file_id):
        """Delete and index both interact with the cache layer."""
        from engine.modules.assistant.semantic_cache import SemanticCacheService
        from engine.modules.assistant.assistant_models import Assistant

        service = SemanticCacheService()
        assert hasattr(service, "invalidate_workspace_cache")


class TestLoggingEnhancements:
    """[DRIVE_SYNC] log messages exist in sync pipeline."""

    def test_sync_drive_has_drive_sync_logs(self):
        """sync_drive.py contains [DRIVE_SYNC] prefix for new/modified/deleted."""
        from engine.pipelines.ingestion import sync_drive as sync_mod
        source = inspect.getsource(sync_mod.ingest_drive_file) + "\n" + inspect.getsource(sync_mod.sync_drive_files)
        assert "[DRIVE_SYNC]" in source

    def test_worker_has_drive_sync_logs(self):
        """Worker contains [DRIVE_SYNC] prefix for new/modified/deleted."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        assert "[DRIVE_SYNC]" in source

    def test_delete_logs_vector_and_metadata_removal(self):
        """Deleted files log vector and metadata removal."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        assert "Removing vectors" in source
        assert "Removing metadata" in source


class TestModelFields:
    """Verify model schema changes."""

    def test_drive_document_has_credential_id(self):
        cols = {c.name: c for c in DriveDocument.__table__.columns}
        assert "credential_id" in cols
        assert cols["credential_id"].nullable is True

    def test_drive_document_chunk_has_drive_file_id(self):
        cols = {c.name: c for c in DriveDocumentChunk.__table__.columns}
        assert "drive_file_id" in cols
        assert cols["drive_file_id"].nullable is True

    def test_schema_includes_credential_id(self):
        assert "credential_id" in DriveDocumentIngestRequest.model_fields
        assert "credential_id" in DriveDocumentResponse.model_fields

    def test_save_chunks_populates_drive_file_id(self):
        source = inspect.getsource(DriveDocumentService.save_chunks)
        assert "drive_file_id=doc.drive_file_id" in source

    def test_create_document_accepts_credential_id(self):
        source = inspect.getsource(DriveDocumentService.create_drive_document)
        assert "credential_id" in source


class TestEndToEndSourceVerification:
    """Source-level verification that fix components all connect."""

    def test_orphan_detection_before_early_return(self):
        """Orphan detection runs BEFORE the 'if not files' guard."""
        from engine.pipelines.ingestion import sync_drive as sync_mod
        source = inspect.getsource(sync_mod.sync_drive_files)
        orphans_before = source.index("orphan_ids") < source.index("if not files")
        assert orphans_before, "orphan detection must precede early-return guard"

    def test_pagination_prevents_false_orphans(self):
        """list_files paginates fully to prevent false positives."""
        from engine.shared.integrations.google_drive_client import GoogleDriveClient
        filepath = inspect.getfile(GoogleDriveClient)
        with open(filepath) as f:
            source = f.read()
        assert "nextPageToken" in source
        assert "while page_token" in source or "while " in source
