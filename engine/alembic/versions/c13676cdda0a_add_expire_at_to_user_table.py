"""Add expire_at to User table

Revision ID: c13676cdda0a
Revises: add_org_email
Create Date: 2026-06-15 15:09:31.135271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c13676cdda0a'
down_revision: Union[str, Sequence[str], None] = 'ba149aa77ef6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("expire_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "expire_at")
