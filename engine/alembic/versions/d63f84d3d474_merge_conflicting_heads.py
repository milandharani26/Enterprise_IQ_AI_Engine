"""Merge conflicting heads

Revision ID: d63f84d3d474
Revises: f6c5210f84c5, rag_hnsw_idx
Create Date: 2026-06-19 10:26:02.631935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd63f84d3d474'
down_revision: Union[str, Sequence[str], None] = ('f6c5210f84c5', 'rag_hnsw_idx')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
