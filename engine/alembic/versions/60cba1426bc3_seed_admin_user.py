"""seed_admin_user

Revision ID: 60cba1426bc3
Revises: 804f027154ed
Create Date: 2026-06-12 11:06:17.411540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60cba1426bc3'
down_revision: Union[str, Sequence[str], None] = '804f027154ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    import bcrypt
    from sqlalchemy import table, column, String, Text, Boolean, DateTime
    from sqlalchemy.sql import select
    from datetime import datetime, timezone

    # Define a stub of the users table for data insertion
    users_table = table('users',
        column('id'),
        column('email', String),
        column('password_hash', Text),
        column('user_name', String),
        column('account_type', String),
        column('is_active', Boolean),
        column('created_at', DateTime),
        column('updated_at', DateTime)
    )

    connection = op.get_bind()

    # Check if admin exists
    admin_email = 'admintest@gmai.com'
    query = select(users_table.c.id).where(users_table.c.email == admin_email)
    res = connection.execute(query).fetchone()

    if not res:
        # Create default admin user
        password_hash = bcrypt.hashpw('admin@123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        connection.execute(
            users_table.insert().values(
                email=admin_email,
                password_hash=password_hash,
                user_name='admin',
                account_type='admin',
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import table, column, String
    users_table = table('users', column('email', String))
    op.execute(users_table.delete().where(users_table.c.email == 'admintest@gmai.com'))
