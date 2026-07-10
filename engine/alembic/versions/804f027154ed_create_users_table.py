"""create_users_table

Revision ID: 804f027154ed
Revises: 
Create Date: 2026-06-12 10:51:01.516747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '804f027154ed'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=255), unique=True, nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=True),
        sa.Column('user_name', sa.String(length=100), nullable=False),
        sa.Column('account_type', sa.String(length=20), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('service_token', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_by', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('users')

