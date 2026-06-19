"""add_connector_schema

Revision ID: connector_rev
Revises: knowledge_rev
Create Date: 2026-06-17 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "connector_rev"
down_revision: Union[str, Sequence[str], None] = "f6c5210f84c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS connectors")

    # 1. database_connections 
    op.create_table(
        "database_connections",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("database_type", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=512), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(length=255), nullable=False),
        sa.Column("schema_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_status", sa.String(length=50), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="connectors",
    )
    op.create_index("idx_db_conn_org_id", "database_connections", ["organization_id"], schema="connectors")
    op.create_index("idx_db_conn_org_id_active", "database_connections", ["organization_id", "is_active"], schema="connectors")
    op.execute(
        "CREATE UNIQUE INDEX uq_database_connections_name_org "
        "ON connectors.database_connections (organization_id, name) "
        "WHERE deleted_at IS NULL"
    )

    # 2. schema_tables is to store tables for each database connection here we add table_description
    op.create_table(
        "schema_tables",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("database_connection_id", sa.UUID(), nullable=False),
        sa.Column("schema_name", sa.String(length=255), nullable=True),
        sa.Column("table_name", sa.String(length=255), nullable=False),
        sa.Column("table_description", sa.Text(), nullable=True),
        sa.Column("row_count_estimate", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["database_connection_id"], ["connectors.database_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("database_connection_id", "schema_name", "table_name", name="uq_schema_tables_db_schema_table"),
        schema="connectors",
    )
    op.create_index("idx_schema_tables_org_db", "schema_tables", ["organization_id", "database_connection_id"], schema="connectors")

    # 3. schema_columns is to store columns for each table here we add column_description
    op.create_table(
        "schema_columns",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("table_id", sa.UUID(), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=100), nullable=False),
        sa.Column("is_nullable", sa.Boolean(), nullable=False),
        sa.Column("is_primary_key", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("default_value", sa.Text(), nullable=True),
        sa.Column("column_description", sa.Text(), nullable=True),
        sa.Column("ordinal_position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["table_id"], ["connectors.schema_tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_id", "column_name", name="uq_schema_columns_table_col"),
        schema="connectors",
    )

    # 4. schema_relationships table is for storing relationships between tables (foreign keys)
    op.create_table(
        "schema_relationships",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("database_connection_id", sa.UUID(), nullable=False),
        sa.Column("source_table", sa.String(length=512), nullable=False),
        sa.Column("source_column", sa.String(length=255), nullable=False),
        sa.Column("target_table", sa.String(length=512), nullable=False),
        sa.Column("target_column", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["database_connection_id"], ["connectors.database_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("database_connection_id", "source_table", "source_column", "target_table", "target_column", name="uq_schema_rels_all"),
        schema="connectors",
    )

    # 5. schema_embeddings to store embeddings for schema
    op.create_table(
        "schema_embeddings",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("database_connection_id", sa.UUID(), nullable=False),
        sa.Column("object_type", sa.String(length=50), nullable=False),
        sa.Column("object_name", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["database_connection_id"], ["connectors.database_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="connectors",
    )
    op.create_index("idx_schema_embeddings_org_db", "schema_embeddings", ["organization_id", "database_connection_id"], schema="connectors")
    
    # Add HNSW index using vector_cosine_ops
    op.execute(
        "CREATE INDEX idx_schema_embeddings_hnsw "
        "ON connectors.schema_embeddings USING hnsw (embedding vector_cosine_ops)"
    )

    # 6. sql_query_logs this is to log query which we fire for debuging perpose
    op.create_table(
        "sql_query_logs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("database_connection_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("selected_database", sa.String(length=255), nullable=True),
        sa.Column("retrieved_tables", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["database_connection_id"], ["connectors.database_connections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        schema="connectors",
    )
    op.create_index("idx_sql_logs_org", "sql_query_logs", ["organization_id"], schema="connectors")
    op.create_index("idx_sql_logs_created", "sql_query_logs", ["created_at"], schema="connectors")


def downgrade() -> None:
    op.drop_table("sql_query_logs", schema="connectors")
    op.drop_table("schema_embeddings", schema="connectors")
    op.drop_table("schema_relationships", schema="connectors")
    op.drop_table("schema_columns", schema="connectors")
    op.drop_table("schema_tables", schema="connectors")
    op.drop_table("database_connections", schema="connectors")
    op.execute("DROP SCHEMA IF EXISTS connectors")
