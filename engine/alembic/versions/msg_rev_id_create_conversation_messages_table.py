"""create_conversation_messages_table

Revision ID: msg_rev_id
Revises: conv_rev_id
Create Date: 2026-06-15 12:44:10.166786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'msg_rev_id'
down_revision: Union[str, Sequence[str], None] = 'conv_rev_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversation_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM','TOOL', name='messagerole'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_admin_messages_conversation_id', 'conversation_messages', ['conversation_id'])
    op.create_index('idx_admin_messages_organization_id', 'conversation_messages', ['organization_id'])

def downgrade() -> None:
    op.drop_index('idx_admin_messages_organization_id', table_name='conversation_messages')
    op.drop_index('idx_admin_messages_conversation_id', table_name='conversation_messages')
    op.drop_table('conversation_messages')
    sa.Enum(name='messagerole').drop(op.get_bind(), checkfirst=False)
