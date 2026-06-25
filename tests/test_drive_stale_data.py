"""Test: Prove deleted Google Drive files can still be retrieved after sync."""

import logging
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from engine.modules.assistant.tools.implementations.drive_search import DriveSearchTool


###############################################################################
# PROOF: Deleted Drive files remain retrievable
#
# Root cause: The sync pipeline (sync_drive.py) is additive-only. It calls
# Google Drive files.list() with 'trashed = false' (default), so deleted/
# trashed files are never returned. No code compares the returned file set
# against stored drive_file_ids to detect deletions. Orphaned DriveDocument
# rows retain status='indexed', and DriveDocumentChunk rows retain their
# embeddings. The search tool (drive_search.py) queries WHERE status='indexed'
# and returns the stale data.
###############################################################################


@pytest.fixture
def org_id():
    return uuid4()


class TestSearchReturnsDeletedFileChunks:
    """
    Prove DriveSearchTool returns chunks from deleted files.

    The SQL query in drive_search.py:
      JOIN knowledge.drive_documents d ON d.id = dc.drive_document_id
      WHERE d.status = 'indexed'

    It does NOT:
    - Check if the Drive file still exists
    - Filter by any 'deleted_at' or 'is_active' column
    - Verify the file is still accessible via Drive API
    """

    @pytest.mark.asyncio
    async def test_vector_search_returns_orphaned_chunks(self, org_id):
        """Simulate a DB that still has rows for a deleted Drive file."""

        # Direct test: verify the SQL query embedded in drive_search.py
        # does not filter out deleted files
        tool = DriveSearchTool()
        tool._initialized = True
        tool._db_url = "postgresql://localhost:5432/testdb"

        # Verify the SQL WHERE clause only checks status='indexed'
        # by inspecting the _vector_search source
        source = inspect.getsource(tool._vector_search)
        assert "status = 'indexed'" in source
        # No trashed/deleted check exists
        assert "trashed" not in source
        assert "deleted" not in source.lower()

    @pytest.mark.asyncio
    async def test_keyword_search_has_same_issue(self, org_id):
        """Keyword fallback also has no deleted-file check."""
        tool = DriveSearchTool()
        tool._initialized = True
        tool._db_url = "postgresql://localhost:5432/testdb"

        source = inspect.getsource(tool._keyword_search)
        assert "status = 'indexed'" in source
        assert "trashed" not in source
        assert "deleted" not in source.lower()

    @pytest.mark.asyncio
    async def test_formatted_results_include_deleted_file_data(self):
        """_format_results has no filtering by file liveness."""
        tool = DriveSearchTool()
        chunks = [
            {"title": "Deleted_File.pdf", "reference_id": "link", "similarity": 0.9,
             "text": "Confidential data from a deleted file."},
        ]
        result = tool._format_results("test query", chunks)
        assert "Deleted_File.pdf" in result
        assert "Confidential data" in result
        # No message about file being deleted or unavailable


class TestSyncPipelineHasNoDeletionLogic:
    """
    Prove neither sync_drive.py nor drive_sync_worker.py can detect deletions.

    ingest_drive_file() in sync_drive.py:
    - Checks if existing doc exists with same drive_file_id
    - If exists AND last_modified matches -> skips (returns early)
    - Otherwise -> creates/updates doc, saves chunks
    - It NEVER calls delete_drive_document() or any deletion logic.

    drive_sync_worker.py:
    - Calls client.list_files(query=query) which defaults to 'trashed = false'
    - Never uses Google Drive Changes API (changes().list())
    - Never compares returned file IDs with stored drive_file_ids
    """

    def test_ingest_drive_file_source_has_no_delete_call(self):
        """Prove by source inspection: ingest_drive_file has no deletion."""
        from engine.pipelines.ingestion import sync_drive as sync_mod
        source = inspect.getsource(sync_mod.ingest_drive_file)
        # The function creates/updates but never calls any delete method
        assert ".delete(" not in source, (
            "ingest_drive_file should not have any delete call"
        )
        assert "delete_drive_document" not in source
        assert "set_processing_status" in source  # sanity check

    def test_sync_drive_files_now_has_delete_call_for_orphans(self):
        """sync_drive_files now calls delete_by_drive_file_id for orphan cleanup."""
        from engine.pipelines.ingestion import sync_drive as sync_mod
        source = inspect.getsource(sync_mod.sync_drive_files)
        assert "delete_by_drive_file_id" in source
        # Old ingest-only path had zero delete logic; fix adds intentional cleanup

    def test_worker_now_has_delete_call_for_orphans(self):
        """Worker now calls delete_by_drive_file_id to clean up orphaned docs."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        assert "delete_by_drive_file_id" in source
        # Old ingest-only path had zero delete logic; fix adds intentional cleanup

    def test_worker_now_detects_orphans_by_drive_file_id(self):
        """Worker cross-references returned IDs vs stored IDs to detect deletions."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        # The fix adds orphan detection by comparing stored vs returned drive_file_ids
        assert "select(DriveDocument.drive_file_id)" in source
        assert "stored_ids - returned_ids" in source
        assert "delete_by_drive_file_id" in source

    def test_google_drive_client_has_no_changes_api(self):
        """Google Drive Changes API (changes().list()) is never used."""
        from engine.shared.integrations.google_drive_client import GoogleDriveClient
        filepath = inspect.getfile(GoogleDriveClient)
        with open(filepath, 'r') as f:
            source = f.read()
        assert "changes()" not in source
        assert "startPageToken" not in source

    def test_worker_never_inspects_trashed_files(self):
        """Worker's query is additive-only; trashed files are invisible."""
        from engine.shared.workers import drive_sync_worker as worker
        source = inspect.getsource(worker._sync_drive_for_workspace)
        # The drive API defaults to not returning trashed files;
        # the worker never asks for them and never cross-checks.
        assert "trashed" not in source


class TestDeletionOnlyViaCredentialCascade:
    """
    The ONLY deletion path for DriveDocuments is credential deletion.

    credentials.py: delete_credential → bulk-deletes ALL DriveDocument rows
    for the organization. Individual file deletion is never handled.
    """

    def test_credential_deletes_all_docs_for_org(self):
        """Credentials.py deletes ALL docs for the org — not selective."""
        from engine.api.v1.endpoints import credentials as cred_mod
        source = inspect.getsource(cred_mod.delete_credential)
        # Bulk delete of ALL DriveDocuments for the org
        assert "sql_delete(DriveDocument)" in source
        # No individual file deletion
        assert "drive_file_id" not in source

    def test_no_individual_file_deletion_api(self):
        """The only DELETE /drive-documents/{id} is manual — not automated."""
        from engine.modules.drive_documents import drive_documents_routes as routes
        source = inspect.getsource(routes.delete_drive_document)
        assert "await service.delete_drive_document(id)" in source
        # This endpoint is called manually via API, not by the sync pipeline
