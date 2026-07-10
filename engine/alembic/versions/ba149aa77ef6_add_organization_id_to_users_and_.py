"""add_organization_id_to_users_and_assistant

Revision ID: ba149aa77ef6
Revises: add_org_email
Create Date: 2026-06-15 14:28:15.100813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ba149aa77ef6'
down_revision: Union[str, Sequence[str], None] = 'add_org_email'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_users_organization_id', 'users', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    
    op.add_column('assistant', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_assistant_organization_id', 'assistant', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_assistant_organization_id', 'assistant', type_='foreignkey')
    op.drop_column('assistant', 'organization_id')
    
    op.drop_constraint('fk_users_organization_id', 'users', type_='foreignkey')
    op.drop_column('users', 'organization_id')
