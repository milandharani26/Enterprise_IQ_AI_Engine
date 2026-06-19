"""migrate db connections to connectors

Revision ID: f7d1210a84c6
Revises: f6c5210f84c5
Create Date: 2026-06-19 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7d1210a84c6'
down_revision: Union[str, Sequence[str], None] = 'connector_rev'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sync status columns to public.connectors
    op.add_column('connectors', sa.Column('sync_status', sa.String(length=50), nullable=True), schema='public')
    op.add_column('connectors', sa.Column('last_synced_at', sa.DateTime(), nullable=True), schema='public')
    op.add_column('connectors', sa.Column('sync_error', sa.Text(), nullable=True), schema='public')

    # Rename foreign keys in connectors schema tables
    op.alter_column('schema_tables', 'database_connection_id', new_column_name='connector_id', schema='connectors')
    op.drop_constraint('schema_tables_database_connection_id_fkey', 'schema_tables', schema='connectors', type_='foreignkey')
    op.create_foreign_key(None, 'schema_tables', 'connectors', ['connector_id'], ['id'], source_schema='connectors', referent_schema='public', ondelete='CASCADE')

    op.alter_column('schema_relationships', 'database_connection_id', new_column_name='connector_id', schema='connectors')
    op.drop_constraint('schema_relationships_database_connection_id_fkey', 'schema_relationships', schema='connectors', type_='foreignkey')
    op.create_foreign_key(None, 'schema_relationships', 'connectors', ['connector_id'], ['id'], source_schema='connectors', referent_schema='public', ondelete='CASCADE')

    op.alter_column('schema_embeddings', 'database_connection_id', new_column_name='connector_id', schema='connectors')
    op.drop_constraint('schema_embeddings_database_connection_id_fkey', 'schema_embeddings', schema='connectors', type_='foreignkey')
    op.create_foreign_key(None, 'schema_embeddings', 'connectors', ['connector_id'], ['id'], source_schema='connectors', referent_schema='public', ondelete='CASCADE')

    op.alter_column('sql_query_logs', 'database_connection_id', new_column_name='connector_id', schema='connectors')
    op.drop_constraint('sql_query_logs_database_connection_id_fkey', 'sql_query_logs', schema='connectors', type_='foreignkey')
    op.create_foreign_key(None, 'sql_query_logs', 'connectors', ['connector_id'], ['id'], source_schema='connectors', referent_schema='public', ondelete='SET NULL')

    # Drop the old database_connections table
    op.drop_table('database_connections', schema='connectors')


def downgrade() -> None:
    pass
