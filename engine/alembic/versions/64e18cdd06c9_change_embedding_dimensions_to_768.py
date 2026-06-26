"""change_embedding_dimensions_to_768

Revision ID: 64e18cdd06c9
Revises: d73a37dba8c2
Create Date: 2026-06-26 12:19:13.028636

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "64e18cdd06c9"
down_revision: Union[str, Sequence[str], None] = "d73a37dba8c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # We clear cache tables first since their vectors will be invalid dimensions
    op.execute("DELETE FROM public.assistant_query_cache;")
    op.execute("DELETE FROM connectors.schema_embeddings;")

    # We alter all 4 tables
    op.execute(
        "ALTER TABLE public.assistant_query_cache ALTER COLUMN query_embedding TYPE vector(768) USING NULL;"
    )
    op.execute(
        "ALTER TABLE connectors.schema_embeddings ALTER COLUMN embedding TYPE vector(768) USING NULL;"
    )
    op.execute(
        "ALTER TABLE knowledge.drive_document_chunks ALTER COLUMN embedding TYPE vector(768) USING NULL;"
    )
    op.execute(
        "ALTER TABLE knowledge.document_chunks ALTER COLUMN embedding TYPE vector(768) USING NULL;"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Clear cache again for downgrade
    op.execute("DELETE FROM public.assistant_query_cache;")
    op.execute("DELETE FROM connectors.schema_embeddings;")

    op.execute(
        "ALTER TABLE public.assistant_query_cache ALTER COLUMN query_embedding TYPE vector(1536) USING NULL;"
    )
    op.execute(
        "ALTER TABLE connectors.schema_embeddings ALTER COLUMN embedding TYPE vector(1536) USING NULL;"
    )
    op.execute(
        "ALTER TABLE knowledge.drive_document_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL;"
    )
    op.execute(
        "ALTER TABLE knowledge.document_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL;"
    )
