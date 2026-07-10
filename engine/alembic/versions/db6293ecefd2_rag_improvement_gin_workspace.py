"""rag_improvement_gin_workspace_idx

Revision ID: rag_improvement_gin_idx
Revises: knowledge_rev
Create Date: 2026-06-17
"""
from typing import Sequence, Union
from alembic import op

revision: str = "rag_improvement_gin_idx"
down_revision: Union[str, Sequence[str], None] = "knowledge_rev"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add stored tsvector column — computed once at write time, never recomputed per query
    op.execute("""
        ALTER TABLE knowledge.document_chunks
        ADD COLUMN IF NOT EXISTS text_search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED
    """)

    # 2. GIN index on stored tsvector — replaces per-row to_tsvector() recomputation
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_text_gin
        ON knowledge.document_chunks USING gin(text_search_vector)
    """)

    # 3. workspace_id index — eliminates seq scan on every org-scoped query
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_chunks_workspace_id
        ON knowledge.document_chunks (workspace_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS knowledge.idx_document_chunks_workspace_id")
    op.execute("DROP INDEX IF EXISTS knowledge.idx_document_chunks_text_gin")
    op.execute("""
        ALTER TABLE knowledge.document_chunks
        DROP COLUMN IF EXISTS text_search_vector
    """)