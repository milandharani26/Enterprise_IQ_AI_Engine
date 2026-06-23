"""rag_improvement_ivfflat_to_hnsw

Switch the vector similarity index from IVFFlat to HNSW for better recall.

HNSW provides ~95-99% recall vs IVFFlat's ~80-90%, with marginally higher
memory usage.  It is the industry standard for <1M vectors and does NOT
require periodic retraining like IVFFlat.

Parameters chosen:
  m = 16           — number of bi-directional links per element (default 16)
  ef_construction = 64  — size of dynamic candidate list during build (default 64)

Revision ID: rag_hnsw_idx
Revises: rag_improvement_gin_idx
Create Date: 2026-06-17
"""
from typing import Sequence, Union
from alembic import op

revision: str = "rag_hnsw_idx"
down_revision: Union[str, Sequence[str], None] = "rag_improvement_gin_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop old IVFFlat index (lower recall, requires retraining)
    op.execute(
        "DROP INDEX IF EXISTS knowledge.idx_document_chunks_embedding_ivfflat"
    )

    # 2. Create HNSW index (higher recall, no retraining needed)
    op.execute("""
        CREATE INDEX idx_document_chunks_embedding_hnsw
        ON knowledge.document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    # Revert to IVFFlat index
    op.execute(
        "DROP INDEX IF EXISTS knowledge.idx_document_chunks_embedding_hnsw"
    )
    op.execute("""
        CREATE INDEX idx_document_chunks_embedding_ivfflat
        ON knowledge.document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)
