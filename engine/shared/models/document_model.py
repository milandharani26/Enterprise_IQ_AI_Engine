"""SQLAlchemy models for document ingestion and vector search."""

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


class Document(Base):
    """Master table for ingested documents."""

    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'processing', 'indexed', 'failed')",
            name="documents_status_check",
        ),
        UniqueConstraint("workspace_id", "reference_id", name="uq_documents_workspace_reference"),
        UniqueConstraint("workspace_id", "title", "version", name="uq_documents_workspace_title_version"),
        {"schema": "knowledge"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    reference_id = Column(String(255), nullable=False)
    title = Column(String(512), nullable=True)
    source = Column(String(100), nullable=True)
    source_url = Column(String(2048), nullable=True)
    file_path = Column(String(1024), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    status = Column(String(50), nullable=False, server_default="draft")
    processing_error = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    content = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    chunk_count = Column(Integer, nullable=False, server_default="0")
    version = Column(Integer, nullable=False, server_default="1")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_by = Column(UUID(as_uuid=True), nullable=True)
    deleted_at = Column(DateTime, nullable=True)


class DocumentChunk(Base):
    """Chunked text segments and embeddings for RAG retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "sequence_number", name="uq_document_chunks_doc_seq"),
        {"schema": "knowledge"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("knowledge.documents.id", ondelete="CASCADE"),
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
