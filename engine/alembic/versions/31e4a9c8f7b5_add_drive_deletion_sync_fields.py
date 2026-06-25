"""Add credential_id to drive_documents, drive_file_id to drive_document_chunks

Revision ID: 31e4a9c8f7b5
Revises: d73a37dba8c2
Create Date: 2026-06-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '31e4a9c8f7b5'
down_revision: Union[str, Sequence[str], None] = 'd73a37dba8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add credential_id to drive_documents
    op.add_column(
        'drive_documents',
        sa.Column('credential_id', sa.Uuid(), nullable=True),
        schema='knowledge',
    )
    op.create_index(
        op.f('ix_knowledge_drive_documents_credential_id'),
        'drive_documents',
        ['credential_id'],
        unique=False,
        schema='knowledge',
    )

    # Add drive_file_id to drive_document_chunks
    op.add_column(
        'drive_document_chunks',
        sa.Column('drive_file_id', sa.String(255), nullable=True),
        schema='knowledge',
    )
    op.create_index(
        op.f('ix_knowledge_drive_document_chunks_drive_file_id'),
        'drive_document_chunks',
        ['drive_file_id'],
        unique=False,
        schema='knowledge',
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_knowledge_drive_document_chunks_drive_file_id'),
        table_name='drive_document_chunks',
        schema='knowledge',
    )
    op.drop_column('drive_document_chunks', 'drive_file_id', schema='knowledge')
    op.drop_index(
        op.f('ix_knowledge_drive_documents_credential_id'),
        table_name='drive_documents',
        schema='knowledge',
    )
    op.drop_column('drive_documents', 'credential_id', schema='knowledge')
