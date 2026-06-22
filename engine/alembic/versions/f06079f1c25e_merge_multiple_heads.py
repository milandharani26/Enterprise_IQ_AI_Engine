"""merge multiple heads

Revision ID: f06079f1c25e
Revises: d63f84d3d474, f7d1210a84c6
Create Date: 2026-06-22 11:33:41.005407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f06079f1c25e'
down_revision: Union[str, Sequence[str], None] = ('d63f84d3d474', 'f7d1210a84c6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
