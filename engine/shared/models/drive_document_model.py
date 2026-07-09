"""SQLAlchemy models for Google Drive ingestion and vector search."""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    text,
    func,
    ForeignKey,
    Integer,
    BigInteger,
    CheckConstraint,
    UniqueConstraint,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from engine.shared.db.base_class import Base


class DriveDocument(Base):
    """Master table for ingested Google Drive files."""

    __tablename__ = "drive_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'processing', 'indexed', 'failed')",
            name="drive_documents_status_check",
        ),
        UniqueConstraint("workspace_id", "drive_file_id", name="uq_drive_documents_workspace_file_id"),
        {"schema": "knowledge"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Google Drive Specific Identifiers
    drive_file_id = Column(String(255), nullable=False, index=True)
    drive_folder_id = Column(String(255), nullable=True, index=True)
    owner_email = Column(String(255), nullable=True)
    
    # Content Metadata
    title = Column(String(512), nullable=True)
    web_view_link = Column(String(2048), nullable=True)  # Equivalent to source_url
    web_content_link = Column(String(2048), nullable=True) # Direct download link
    mime_type = Column(String(100), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)

    # Processing State
    status = Column(String(50), nullable=False, server_default="draft")
    processing_error = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)

    # Flexible Metadata
    metadata_ = Column("metadata", JSONB, nullable=True)
    
    # Optimization & State
    chunk_count = Column(Integer, nullable=False, server_default="0")
    version = Column(Integer, nullable=False, server_default="1")

    # Audit
    last_modified_in_drive = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class DriveDocumentChunk(Base):
    """Chunked text segments and embeddings for Google Drive RAG retrieval."""

    __tablename__ = "drive_document_chunks"
    __table_args__ = (
        UniqueConstraint("drive_document_id", "sequence_number", name="uq_drive_document_chunks_doc_seq"),
        {"schema": "knowledge"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    drive_document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.drive_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    embedding_model = Column(String(255), nullable=True)
    embedding_created_at = Column(DateTime, nullable=True)
    embedding_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
