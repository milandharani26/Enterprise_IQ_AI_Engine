"""add credentials and connectors tables

Revision ID: f6c5210f84c5
Revises: 77694edb12d6
Create Date: 2026-06-18 18:11:20.822056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6c5210f84c5'
down_revision: Union[str, Sequence[str], None] = '77694edb12d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.credentials (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL,
            provider VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'Active',
            auth_data JSONB NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            last_used_at TIMESTAMP WITHOUT TIME ZONE
        );
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.connectors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL,
            connector_id VARCHAR(100) NOT NULL,
            name VARCHAR(255) NOT NULL,
            provider VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'disabled',
            credential_id UUID REFERENCES public.credentials(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT uq_connectors_org_connector UNIQUE (organization_id, connector_id)
        );
    """)

    # Seed the google_drive and postgres connectors for all existing organizations
    op.execute("""
        INSERT INTO public.connectors (organization_id, connector_id, name, provider, status)
        SELECT id, 'google_drive', 'Google Drive', 'Google', 'disabled' FROM organizations
        ON CONFLICT (organization_id, connector_id) DO NOTHING;
    """)

    op.execute("""
        INSERT INTO public.connectors (organization_id, connector_id, name, provider, status)
        SELECT id, 'postgres', 'PostgreSQL', 'PostgreSQL', 'disabled' FROM organizations
        ON CONFLICT (organization_id, connector_id) DO NOTHING;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS public.connectors;")
    op.execute("DROP TABLE IF EXISTS public.credentials;")
