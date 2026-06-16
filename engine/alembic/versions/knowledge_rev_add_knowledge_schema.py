"""add_knowledge_schema_and_tables

Revision ID: knowledge_rev
Revises: c13676cdda0a
Create Date: 2026-06-16 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "knowledge_rev"
down_revision: Union[str, Sequence[str], None] = "c13676cdda0a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS knowledge")

    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("reference_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'processing', 'indexed', 'failed')",
            name="documents_status_check",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "reference_id", name="uq_documents_workspace_reference"),
        sa.UniqueConstraint("workspace_id", "title", "version", name="uq_documents_workspace_title_version"),
        schema="knowledge",
    )

    op.create_index("idx_documents_workspace_id", "documents", ["workspace_id"], schema="knowledge")
    op.create_index("idx_documents_status", "documents", ["status"], schema="knowledge")
    op.create_index("idx_documents_created_at", "documents", ["created_at"], schema="knowledge")
    op.create_index("idx_documents_source", "documents", ["source"], schema="knowledge")

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("embedding_created_at", sa.DateTime(), nullable=True),
        sa.Column("embedding_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge.documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "sequence_number", name="uq_document_chunks_doc_seq"),
        schema="knowledge",
    )

    op.create_index(
        "idx_document_chunks_document_id",
        "document_chunks",
        ["document_id"],
        schema="knowledge",
    )
    op.execute(
        "CREATE INDEX idx_document_chunks_embedding_ivfflat "
        "ON knowledge.document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("document_chunks", schema="knowledge")
    op.drop_table("documents", schema="knowledge")
    op.execute("DROP SCHEMA IF EXISTS knowledge")
