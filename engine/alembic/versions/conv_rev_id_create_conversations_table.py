"""create_conversations_table

Revision ID: conv_rev_id
Revises: org_rev_id
Create Date: 2026-06-15 12:44:09.032092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'conv_rev_id'
down_revision: Union[str, Sequence[str], None] = 'org_rev_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_admin_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('idx_admin_conversations_organization_id', 'conversations', ['organization_id'])

def downgrade() -> None:
    op.drop_index('idx_admin_conversations_organization_id', table_name='conversations')
    op.drop_index('idx_admin_conversations_user_id', table_name='conversations')
    op.drop_table('conversations')