"""add_email_to_organizations

Revision ID: add_org_email
Revises: msg_rev_id
Create Date: 2026-06-15 13:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = 'add_org_email'
down_revision = 'msg_rev_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add the email column as nullable first to safely accommodate existing data
    op.add_column('organizations', sa.Column('email', sa.String(length=255), nullable=True))
    
    # 2. Add a unique constraint to ensure organization emails are unique
    op.create_unique_constraint('uq_organizations_email', 'organizations', ['email'])


def downgrade() -> None:
    # 1. Drop the unique constraint first
    op.drop_constraint('uq_organizations_email', 'organizations', type_='unique')
    
    # 2. Drop the email column
    op.drop_column('organizations', 'email')