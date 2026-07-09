"""add_llm_config_to_assistant

Revision ID: 86e9ebe4f060
Revises: 147fe9a986b9
Create Date: 2026-07-09 11:50:50.515084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86e9ebe4f060'
down_revision: Union[str, Sequence[str], None] = '147fe9a986b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'assistant',
        sa.Column('llm_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('assistant', 'llm_config')

