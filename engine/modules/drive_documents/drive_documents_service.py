"""Service layer for Google Drive document management."""

import logging
from typing import Union, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, asc, delete
from sqlalchemy.orm.attributes import flag_modified

from engine.shared.core.deps import BaseDeps
from engine.shared.exceptions.exceptions import (
    DocumentNotFoundError,
    InvalidChunkError,
    InvalidDocumentStatusError,
)
from engine.shared.models.drive_document_model import DriveDocument, DriveDocumentChunk
from engine.shared.schemas.drive_document_schema import (
    DriveDocumentIngestRequest,
    DriveDocumentResponse,
    DriveDocumentUpdateMetadataRequest,
)

logger = logging.getLogger(__name__)


class DriveDocumentService:
    """Business logic for Drive document management operations."""

    def __init__(self, base_deps: Union[BaseDeps, AsyncSession]):
        if isinstance(base_deps, AsyncSession):
            self.db = base_deps
        else:
            self.db = base_deps.db

    async def create_drive_document(
        self,
        request: DriveDocumentIngestRequest,
        workspace_id: UUID,
    ) -> DriveDocument:
        """Create or update a Drive document ingestion record."""
        existing = (
            (
                await self.db.execute(
                    select(DriveDocument).where(
                        and_(
                            DriveDocument.workspace_id == workspace_id,
                            DriveDocument.drive_file_id == request.drive_file_id,
                        )
                    )
                )
            )
            .scalars()
            .first()
        )

        if existing:
            existing.title = request.title
            existing.web_view_link = request.web_view_link
            existing.web_content_link = request.web_content_link
            existing.mime_type = request.mime_type
            existing.owner_email = request.owner_email
            existing.drive_folder_id = request.drive_folder_id
            existing.file_size_bytes = request.file_size_bytes
            existing.metadata_ = request.metadata
            existing.last_modified_in_drive = request.last_modified_in_drive
            existing.version += 1

            existing.status = "draft"
            existing.processing_error = None
            existing.processing_started_at = None
            existing.processing_completed_at = None
            existing.chunk_count = 0

            await self.db.execute(
                delete(DriveDocumentChunk).where(
                    DriveDocumentChunk.drive_document_id == existing.id
                )
            )

            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        document = DriveDocument(
            workspace_id=workspace_id,
            drive_file_id=request.drive_file_id,
            title=request.title,
            web_view_link=request.web_view_link,
            web_content_link=request.web_content_link,
            mime_type=request.mime_type,
            owner_email=request.owner_email,
            drive_folder_id=request.drive_folder_id,
            file_size_bytes=request.file_size_bytes,
            metadata_=request.metadata,
            last_modified_in_drive=request.last_modified_in_drive,
            status="draft",
            version=1,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def get_drive_document(
        self, document_id: UUID, workspace_id: UUID
    ) -> DriveDocumentResponse:
        doc = await self._get_document_safe(document_id, workspace_id)
        return self._to_response(doc)

    async def get_document_status(self, document_id: UUID) -> str:
        doc = (
            (
                await self.db.execute(
                    select(DriveDocument).where(DriveDocument.id == document_id)
                )
            )
            .scalars()
            .first()
        )
        if not doc:
            raise DocumentNotFoundError()
        return doc.status

    async def list_drive_documents(
        self,
        workspace_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        sort: str = "-created_at",
    ) -> Tuple[List[DriveDocumentResponse], int]:
        filters = [DriveDocument.workspace_id == workspace_id]
        if status:
            filters.append(DriveDocument.status == status)

        descending = sort.startswith("-")
        field_name = sort.lstrip("-")
        col = getattr(DriveDocument, field_name, DriveDocument.created_at)
        order_col = desc(col) if descending else asc(col)

        # Single query with window function for total count (eliminates extra DB round trip)
        count_col = func.count(DriveDocument.id).over().label("_total")
        stmt = (
            select(DriveDocument, count_col)
            .where(and_(*filters))
            .order_by(order_col)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        raw_rows = result.all()

        if not raw_rows:
            return [], 0

        total = raw_rows[0]._total
        rows = [row[0] for row in raw_rows]

        return [self._to_response(d) for d in rows], total

    async def update_drive_document(
        self,
        document_id: UUID,
        workspace_id: UUID,
        request: DriveDocumentUpdateMetadataRequest,
    ) -> DriveDocumentResponse:
        doc = await self._get_document_safe(document_id, workspace_id)

        if request.status is not None:
            if request.status not in ["draft", "processing", "indexed", "failed"]:
                raise InvalidDocumentStatusError()
            doc.status = request.status
            if request.status == "processing":
                doc.processing_started_at = func.now()
            elif request.status in ("indexed", "failed"):
                doc.processing_completed_at = func.now()

        if request.processing_error is not None:
            doc.processing_error = request.processing_error

        if request.chunk_count is not None:
            if request.chunk_count < 0:
                raise InvalidChunkError()
            doc.chunk_count = request.chunk_count

        if request.version is not None:
            doc.version = request.version

        if request.metadata is not None:
            current = (doc.metadata_ or {}).copy()
            current.update(request.metadata)
            doc.metadata_ = current
            flag_modified(doc, "metadata_")

        await self.db.commit()
        await self.db.refresh(doc)
        return self._to_response(doc)

    async def delete_drive_document(self, document_id: UUID) -> None:
        result = await self.db.execute(
            delete(DriveDocument).where(DriveDocument.id == document_id)
        )
        if result.rowcount == 0:
            await self.db.rollback()
            raise DocumentNotFoundError()
        await self.db.commit()

    async def delete_by_drive_file_ids(
        self, workspace_id: UUID, drive_file_ids: List[str]
    ) -> int:
        if not drive_file_ids:
            return 0

        result = await self.db.execute(
            delete(DriveDocument).where(
                and_(
                    DriveDocument.workspace_id == workspace_id,
                    DriveDocument.drive_file_id.in_(drive_file_ids),
                )
            )
        )

        await self.db.commit()
        return result.rowcount

    async def set_processing_status(
        self,
        document_id: UUID,
        workspace_id: UUID,
        status: str,
        error: Optional[str] = None,
    ) -> DriveDocumentResponse:
        if status not in ["draft", "processing", "indexed", "failed"]:
            raise InvalidDocumentStatusError()

        doc = await self._get_document_safe(document_id, workspace_id)
        doc.status = status
        if status == "processing":
            doc.processing_started_at = func.now()
        elif status in ("indexed", "failed"):
            doc.processing_completed_at = func.now()
        if error:
            doc.processing_error = error

        await self.db.commit()
        await self.db.refresh(doc)
        return self._to_response(doc)

    async def save_chunks(
        self,
        document_id: UUID,
        workspace_id: UUID,
        chunks_data: List[dict],
    ) -> int:
        if not chunks_data:
            raise InvalidChunkError()

        doc = await self._get_document_safe(document_id, workspace_id)

        await self.db.execute(
            delete(DriveDocumentChunk).where(
                DriveDocumentChunk.drive_document_id == document_id
            )
        )

        for i, data in enumerate(chunks_data):
            text_val = data.get("text")
            if not text_val:
                raise InvalidChunkError()

            if isinstance(text_val, str):
                text_val = text_val.replace("\x00", "")
            else:
                text_val = str(text_val).replace("\x00", "")

            self.db.add(
                DriveDocumentChunk(
                    drive_document_id=document_id,
                    workspace_id=workspace_id,
                    sequence_number=data.get("sequence_number", i),
                    text=text_val,
                    token_count=data.get("token_count"),
                    embedding=data.get("embedding"),
                    embedding_model=data.get("embedding_model"),
                    embedding_metadata=data.get("embedding_metadata"),
                )
            )

        doc.chunk_count = len(chunks_data)
        await self.db.commit()
        return len(chunks_data)

    async def _get_document_safe(
        self, document_id: UUID, workspace_id: UUID
    ) -> DriveDocument:
        doc = (
            (
                await self.db.execute(
                    select(DriveDocument).where(
                        and_(
                            DriveDocument.id == document_id,
                            DriveDocument.workspace_id == workspace_id,
                        )
                    )
                )
            )
            .scalars()
            .first()
        )

        if not doc:
            raise DocumentNotFoundError()
        return doc

    def _to_response(self, doc: DriveDocument) -> DriveDocumentResponse:
        return DriveDocumentResponse(
            id=doc.id,
            workspace_id=doc.workspace_id,
            drive_file_id=doc.drive_file_id,
            drive_folder_id=doc.drive_folder_id,
            owner_email=doc.owner_email,
            title=doc.title,
            web_view_link=doc.web_view_link,
            web_content_link=doc.web_content_link,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status,
            processing_error=doc.processing_error,
            processing_started_at=doc.processing_started_at,
            processing_completed_at=doc.processing_completed_at,
            chunk_count=doc.chunk_count,
            version=doc.version,
            last_modified_in_drive=doc.last_modified_in_drive,
            metadata=doc.metadata_,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
