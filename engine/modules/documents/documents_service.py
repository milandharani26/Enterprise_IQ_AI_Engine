"""Service layer for document management (ingestion and lifecycle)."""

import mimetypes
import logging
import os
import tempfile
from pathlib import Path
from typing import Union, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, asc, delete
from sqlalchemy.orm.attributes import flag_modified

from engine.shared.core.deps import BaseDeps
from engine.shared.exceptions.exceptions import DocumentNotFoundError, InvalidChunkError, InvalidDocumentStatusError
from engine.shared.models.document_model import Document, DocumentChunk
from engine.shared.schemas.document_schema import (
    DocumentIngestRequest,
    DocumentResponse,
    DocumentUpdateMetadataRequest,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Business logic for document management operations."""

    def __init__(self, base_deps: Union[BaseDeps, AsyncSession]):
        """Initialize the service with either BaseDeps or a direct AsyncSession.
        This maintains backward compatibility for routes that may still pass the session.
        """
        if isinstance(base_deps, AsyncSession):
            self.db = base_deps
        else:
            self.db = base_deps.db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_document(
        self,
        request: DocumentIngestRequest,
        workspace_id: UUID,
    ) -> Document:
        """
        Create or update (upsert) a document ingestion record.

        Behavior:
        - If (workspace_id, reference_id) already exists (even if soft-deleted),
          we **update** the existing document and re-queue indexing.
        - Document titles are NOT unique; duplicates are allowed.

        Note:
        - reference_id is used as the document primary key (UUID) in this system.
        """
        ref_key = str(request.reference_id)
        # Upsert by (workspace_id, reference_id). We intentionally include soft-deleted rows
        # to avoid primary-key conflicts on insert and to allow "reviving" a document ID.
        existing = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.workspace_id == workspace_id,
                        Document.reference_id == ref_key,
                    )
                )
            )
        ).scalars().first()

        if existing:
            # Revive if soft-deleted
            existing.deleted_at = None

            # Update fields from request
            title_changed = (existing.title != request.title)
            existing.title = request.title
            existing.source = _derive_source(request.source_url)
            existing.source_url = request.source_url
            existing.metadata_ = request.metadata
            # If title changed, pick a new version to satisfy (workspace_id, title, version) uniqueness.
            if title_changed and request.title:
                max_version_row = await self.db.execute(
                    select(func.max(Document.version)).where(
                        and_(
                            Document.workspace_id == workspace_id,
                            Document.title == request.title,
                        )
                    )
                )
                max_version = max_version_row.scalar_one_or_none()
                existing.version = int(max_version or 0) + 1

            # Reset indexing state so a re-index is clean
            existing.status = "draft"
            existing.processing_error = None
            existing.processing_started_at = None
            existing.processing_completed_at = None
            existing.chunk_count = 0

            # Clear existing chunks (supports true re-index/upsert)
            await self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == existing.id)
            )

            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Choose version to avoid DB unique constraint violations for duplicate titles.
        next_version = 1
        if request.title:
            max_version_row = await self.db.execute(
                select(func.max(Document.version)).where(
                    and_(
                        Document.workspace_id == workspace_id,
                        Document.title == request.title,
                    )
                )
            )
            max_version = max_version_row.scalar_one_or_none()
            next_version = int(max_version or 0) + 1

        document = Document(
            id=request.reference_id,
            workspace_id=workspace_id,
            reference_id=ref_key,
            title=request.title,
            source=_derive_source(request.source_url),
            source_url=request.source_url,
            metadata_=request.metadata,
            status="draft",
            version=next_version,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        return document

    # ------------------------------------------------------------------
    # Load document (fetch + parse via loaders)
    # ------------------------------------------------------------------

    async def load_document(self, source_url: str) -> Tuple[str, dict]:
        """
        Fetch and parse document from S3/GCS/HTTP.

        Returns:
            (content: str, metadata: dict)

        Raises:
            UnsupportedMimetypeError: No loader for detected MIME type.
            DocumentLoadError: Fetch or parse failed.
        """
        from engine.pipelines.ingestion.exceptions import DocumentLoadError, UnsupportedMimetypeError
        from engine.pipelines.ingestion.loaders.registry import LoaderRegistry

        mime_type = self._detect_mime_type(source_url)
        logger.debug("Detected MIME type: %s for %s", mime_type, source_url)

        try:
            loader = LoaderRegistry.get_loader(mime_type)
        except UnsupportedMimetypeError as e:
            logger.error("Unsupported document type: %s from %s", mime_type, source_url)
            raise

        try:
            content, metadata = await loader.load_from_url(source_url)
            logger.info(
                "Loaded document: %s, %s chars, metadata keys=%s",
                mime_type, len(content), list(metadata.keys()) if metadata else [],
            )
            return content, metadata
        except Exception as e:
            logger.exception("Failed to load %s: %s", source_url, e)
            if isinstance(e, DocumentLoadError):
                raise
            raise DocumentLoadError(f"Document loading failed: {e}") from e

    async def load_document_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """Parse uploaded file bytes using the same loader registry as URL ingestion."""
        from engine.pipelines.ingestion.exceptions import DocumentLoadError, UnsupportedMimetypeError
        from engine.pipelines.ingestion.loaders.registry import LoaderRegistry

        if not file_bytes:
            raise DocumentLoadError("Empty file")

        detected_mime = mime_type or self._detect_mime_type(filename)
        if detected_mime == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(filename)
            detected_mime = guessed or detected_mime

        try:
            loader = LoaderRegistry.get_loader(detected_mime)
        except UnsupportedMimetypeError:
            raise

        suffix = Path(filename).suffix or mimetypes.guess_extension(detected_mime) or ""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            content, metadata = await loader.load_from_url(Path(tmp_path).as_uri())
            merged = dict(metadata or {})
            merged["source_filename"] = filename
            merged["upload_source"] = "cpanel"
            return content, merged
        except DocumentLoadError:
            raise
        except Exception as e:
            raise DocumentLoadError(f"Document loading failed: {e}") from e
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _detect_mime_type(self, uri: str) -> str:
        """Detect MIME type from URL path/filename (robust for presigned S3 URLs)."""
        import re
        from urllib.parse import parse_qs, unquote, urlparse

        parsed = urlparse(uri)

        # 1) Prefer MIME detection from URL path (e.g. /file.pdf).
        path = parsed.path or uri
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            return mime_type

        # 2) For presigned URLs, try response-content-disposition to extract filename.
        # This query param format can vary (quotes vs no quotes, filename vs filename*).
        #
        # Examples:
        # - inline; filename="sample123.pdf"
        # - attachment; filename=sample123.pdf
        # - inline; filename*=UTF-8''sample123.pdf
        qs = parse_qs(parsed.query or "")
        dispositions = qs.get("response-content-disposition", [])
        if dispositions:
            disp = unquote(dispositions[0])

            # RFC5987: filename*=UTF-8''<value>
            m_star = re.search(r"filename\*\s*=\s*([^;]+)", disp, flags=re.IGNORECASE)
            if m_star:
                raw_val = m_star.group(1).strip()
                # raw_val may look like: UTF-8''sample123.pdf or just sample123.pdf
                if "''" in raw_val:
                    _charset, _lang, val = raw_val.split("''", 2)
                    candidate = val
                else:
                    candidate = raw_val

                candidate = candidate.strip().strip('"').strip()
                mime_type, _ = mimetypes.guess_type(candidate)
                if mime_type:
                    return mime_type

            # filename="..." or filename=...
            m = re.search(
                r"filename\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^;]+))",
                disp,
                flags=re.IGNORECASE,
            )
            if m:
                candidate = next(g for g in m.groups() if g)
                candidate = candidate.strip().strip('"').strip()
                mime_type, _ = mimetypes.guess_type(candidate)
                if mime_type:
                    return mime_type

        # 3) Try direct filename-like query params (common in signed links and gateways).
        # Examples: ?filename=abc.docx, ?file=abc.xlsx, ?key=path/to/file.json
        for query_key in ("filename", "file", "name", "key", "path"):
            vals = qs.get(query_key, [])
            if not vals:
                continue
            candidate = unquote(vals[0]).strip().strip('"').strip()
            if not candidate:
                continue
            mime_type, _ = mimetypes.guess_type(candidate)
            if mime_type:
                return mime_type

        # 4) Last-resort extension sniff from decoded full URI text.
        # Helps when gateways wrap the real filename into opaque URLs.
        lowered = unquote(uri).lower()
        ext_to_mime = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".csv": "text/csv",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
        }
        for ext, guessed in ext_to_mime.items():
            if re.search(rf"{re.escape(ext)}(\b|[^a-z0-9_])", lowered):
                return guessed

        return "application/octet-stream"

    # ------------------------------------------------------------------
    # Read — single
    # ------------------------------------------------------------------

    async def get_document(self, document_id: UUID, workspace_id: UUID) -> DocumentResponse:
        """Fetch a single document with workspace isolation. Raises 404 if not found."""
        doc = await self._get_document_safe(document_id, workspace_id)
        return self._to_response(doc)

    async def get_document_status(self, document_id: UUID) -> str:
        """Fetch ingestion status by document id. Raises 404 if not found."""
        doc = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.id == document_id,
                        Document.deleted_at.is_(None),
                    )
                )
            )
        ).scalars().first()

        if not doc:
            raise DocumentNotFoundError()

        return doc.status

    # ------------------------------------------------------------------
    # Read — list
    # ------------------------------------------------------------------

    async def list_documents(
        self,
        workspace_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        source: Optional[str] = None,
        sort: str = "-created_at",
    ) -> Tuple[List[DocumentResponse], int]:
        """
        Return a page of documents and the total count.

        sort: field name, prefix with '-' for descending (e.g. '-created_at').
        """
        filters = [
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        ]
        if status:
            filters.append(Document.status == status)
        if source:
            filters.append(Document.source == source)

        total: int = (
            await self.db.execute(
                select(func.count(Document.id)).where(and_(*filters))
            )
        ).scalar() or 0

        order_col = _resolve_sort(sort)

        rows = (
            await self.db.execute(
                select(Document)
                .where(and_(*filters))
                .order_by(order_col)
                .limit(limit)
                .offset(offset)
            )
        ).scalars().all()

        return [self._to_response(d) for d in rows], total

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update_document(
        self,
        document_id: UUID,
        workspace_id: UUID,
        request: DocumentUpdateMetadataRequest,
    ) -> DocumentResponse:
        """Update status, metadata, chunk_count, or version fields."""
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
            if request.version < 1:
                raise InvalidDocumentStatusError()
            doc.version = request.version

        if request.metadata is not None:
            # Merge (not replace) — consistent with how other modules handle JSONB patches
            current = (doc.metadata_ or {}).copy()
            current.update(request.metadata)
            doc.metadata_ = current
            flag_modified(doc, "metadata_")

        await self.db.commit()
        await self.db.refresh(doc)
        return self._to_response(doc)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_document(self, document_id: UUID) -> None:
        """
        Permanently delete the document by id.

        `knowledge.document_chunks.document_id` references `knowledge.documents.id`
        with ON DELETE CASCADE, so chunk rows are removed with the document.
        """
        result = await self.db.execute(
            delete(Document).where(Document.id == document_id)
        )
        if result.rowcount == 0:
            await self.db.rollback()
            raise DocumentNotFoundError()
        await self.db.commit()

    # ------------------------------------------------------------------
    # Status helpers (called by async indexing jobs)
    # ------------------------------------------------------------------

    async def set_processing_status(
        self,
        document_id: UUID,
        workspace_id: UUID,
        status: str,
        error: Optional[str] = None,
    ) -> DocumentResponse:
        """Update processing status during async job lifecycle."""
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
        """Batch-insert chunks after embedding; updates denormalised chunk_count."""
        if not chunks_data:
            raise InvalidChunkError()
        
        doc = await self._get_document_safe(document_id, workspace_id)

        # Remove existing chunks first (supports re-indexing)
        await self.db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )

        for i, data in enumerate(chunks_data):
            if not data.get("text"):
                raise InvalidChunkError()

            # Postgres (UTF-8) rejects null bytes inside TEXT.
            # Some loaders (PDF extraction, presigned downloads) can yield '\x00'
            # characters in the extracted content. Strip them to keep ingestion reliable.
            text_val = data["text"]
            if isinstance(text_val, str):
                text_val = text_val.replace("\x00", "")
            else:
                text_val = str(text_val).replace("\x00", "")
            
            self.db.add(
                DocumentChunk(
                    document_id=document_id,
                    workspace_id=workspace_id,
                    sequence_number=data.get("sequence_number", i),
                    text=text_val,
                    token_count=data.get("token_count"),
                    embedding=data.get("embedding"),
                    embedding_model=data.get("embedding_model"),
                    embedding_metadata=data.get("embedding_metadata")
                )
            )

        doc.chunk_count = len(chunks_data)
        await self.db.commit()
        return len(chunks_data)

    # ------------------------------------------------------------------
    # Get Chunk Count
    # ------------------------------------------------------------------

    async def get_chunk_count(
        self,
        document_id: UUID,
        workspace_id: UUID,
    ) -> int:
        """
        Get the chunk count for a document.
        This is a quick lookup using the denormalized chunk_count field.
        """
        doc = await self._get_document_safe(document_id, workspace_id)
        return doc.chunk_count or 0

    # ------------------------------------------------------------------
    # Cpanel direct upload (persist file -> queue or sync index)
    # ------------------------------------------------------------------

    async def prepare_uploaded_document(
        self,
        *,
        reference_id: UUID,
        workspace_id: UUID,
        title: str,
        file_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Save upload to disk, create document record; indexing runs separately."""
        from engine.shared.config.settings import get_settings

        settings = get_settings()
        safe_name = Path(filename).name or "upload"
        upload_dir = Path(settings.document_upload_dir) / str(workspace_id) / str(reference_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / safe_name
        file_path.write_bytes(file_bytes)
        source_url = file_path.resolve().as_uri()

        merged_metadata = dict(metadata or {})
        merged_metadata.setdefault("upload_source", "cpanel")
        merged_metadata["source_filename"] = safe_name

        request = DocumentIngestRequest(
            reference_id=reference_id,
            source_url=source_url,
            title=title,
            metadata=merged_metadata,
        )
        doc = await self.create_document(request, workspace_id=workspace_id)

        if mime_type:
            doc.mime_type = mime_type
        doc.file_size_bytes = len(file_bytes)
        doc.file_path = str(file_path)
        doc.source = "upload"
        doc.source_url = source_url
        await self.db.commit()
        await self.db.refresh(doc)

        return {
            "doc_id": doc.id,
            "reference_id": doc.reference_id,
            "status": doc.status,
            "chunk_count": 0,
            "processing_error": None,
        }

    async def ingest_and_index_from_upload(
        self,
        *,
        reference_id: UUID,
        workspace_id: UUID,
        title: str,
        file_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Create document from upload and run synchronous indexing (legacy / tests)."""
        from engine.pipelines.ingestion.indexing import run_index_document_task

        prepared = await self.prepare_uploaded_document(
            reference_id=reference_id,
            workspace_id=workspace_id,
            title=title,
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            metadata=metadata,
        )
        await run_index_document_task(prepared["doc_id"], workspace_id)
        doc = await self._get_document_safe(prepared["doc_id"], workspace_id)
        return {
            "doc_id": doc.id,
            "reference_id": doc.reference_id,
            "status": doc.status,
            "chunk_count": doc.chunk_count or 0,
            "processing_error": doc.processing_error,
            "message": (
                "Document uploaded and indexed successfully"
                if doc.status == "indexed"
                else "Document upload failed during indexing"
            ),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_document_safe(self, document_id: UUID, workspace_id: UUID) -> Document:
        """
        Fetch document and assert workspace ownership.
        Raises HTTPException 404 if not found or soft-deleted.
        """
        doc = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.id == document_id,
                        Document.workspace_id == workspace_id,
                        Document.deleted_at.is_(None),
                    )
                )
            )
        ).scalars().first()

        if not doc:
            raise DocumentNotFoundError()
        return doc

    def _to_response(self, doc: Document) -> DocumentResponse:
        return DocumentResponse(
            id=doc.id,
            workspace_id=doc.workspace_id,
            reference_id=doc.reference_id,
            title=doc.title,
            source=doc.source,
            source_url=doc.source_url,
            file_path=doc.file_path,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status,
            processing_error=doc.processing_error,
            processing_started_at=doc.processing_started_at,
            processing_completed_at=doc.processing_completed_at,
            chunk_count=doc.chunk_count,
            version=doc.version,
            metadata=doc.metadata_,  # mapped from ORM alias
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            created_by=getattr(doc, "created_by", None),
        )


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

def _derive_source(source_url: str) -> str:
    """Infer source type from URL prefix."""
    if source_url.startswith("s3://"):
        return "s3"
    if source_url.startswith("gs://"):
        return "gcs"
    if source_url.startswith("upload://") or source_url.startswith("file://"):
        return "upload"
    return "api"


def _resolve_sort(sort: str):
    """Convert sort string like '-created_at' to a SQLAlchemy order expression."""
    descending = sort.startswith("-")
    field_name = sort.lstrip("-")
    col = getattr(Document, field_name, Document.created_at)
    return desc(col) if descending else asc(col)
