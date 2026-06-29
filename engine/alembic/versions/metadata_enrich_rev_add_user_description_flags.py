"""add_user_description_flags_to_schema_tables_and_columns

Revision ID: metadata_enrich_rev
Revises: 64e18cdd06c9
Create Date: 2026-06-29 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "metadata_enrich_rev"
down_revision: Union[str, Sequence[str], None] = "64e18cdd06c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sentinel flag to schema_tables:
    # When True, the sync crawler will NOT overwrite table_description
    op.add_column(
        "schema_tables",
        sa.Column(
            "user_table_description",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="connectors",
    )

    # Add sentinel flag to schema_columns:
    # When True, the sync crawler will NOT overwrite column_description
    op.add_column(
        "schema_columns",
        sa.Column(
            "user_column_description",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        schema="connectors",
    )

    # Add updated_at to schema_columns so the UI can show "last modified"
    op.add_column(
        "schema_columns",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="connectors",
    )


def downgrade() -> None:
    op.drop_column("schema_columns", "updated_at", schema="connectors")
    op.drop_column("schema_columns", "user_column_description", schema="connectors")
    op.drop_column("schema_tables", "user_table_description", schema="connectors")
