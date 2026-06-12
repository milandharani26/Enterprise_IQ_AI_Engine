"""create_assistant_table

Revision ID: 6881d867c2c6
Revises: 60cba1426bc3
Create Date: 2026-06-12 12:07:45.459907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6881d867c2c6'
down_revision: Union[str, Sequence[str], None] = '60cba1426bc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy.dialects import postgresql
    op.create_table(
        'assistant',
        sa.Column('assistant_id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('assistant_name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('assistant_code', sa.String(length=100), nullable=False, unique=True),
        sa.Column('type', sa.String(length=50), nullable=False, server_default='simple_reactive'),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='enabled'),
        sa.Column('guardrails', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tools', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('prompt_library', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.CheckConstraint("status IN ('enabled', 'disabled')", name='check_assistant_status')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('assistant')
