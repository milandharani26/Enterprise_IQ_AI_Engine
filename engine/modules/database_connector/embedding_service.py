import os
import logging
import asyncio
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from engine.shared.config.settings import get_settings
from engine.modules.database_connector.models import (
    SchemaTable,
    SchemaColumn,
    SchemaRelationship,
    SchemaEmbedding
)

logger = logging.getLogger(__name__)

class SchemaEmbeddingService:
    def __init__(self):
        settings = get_settings()
        self._embedding_model = "text-embedding-3-small"
        
        embedding_provider = (
            os.getenv("EMBEDDING_PROVIDER")
            or getattr(settings, "embedding_provider", "")
            or "openai"
        ).strip().lower()

        if embedding_provider == "groq":
            api_key = os.getenv("GROQ_API_KEY") or getattr(settings, "groq_api_key", "")
            base_url = "https://api.groq.com/openai/v1"
        else:
            api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "openai_api_key", "")
            base_url = None

        if not api_key:
            logger.warning("Embedding API key missing, schema embedding will fail.")
        
        self._openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def _embed_text(self, text: str) -> list[float]:
        try:
            response = await asyncio.wait_for(
                self._openai_client.embeddings.create(
                    model=self._embedding_model,
                    input=text,
                    encoding_format="float",
                ),
                timeout=30,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise

    async def generate_embeddings(self, db: AsyncSession, connection_id: UUID, org_id: UUID):
        """Generates natural language descriptions of tables and relationships, and embeds them."""
        logger.info(f"Generating schema embeddings for connection {connection_id}")

        # 1. Clear old embeddings
        await db.execute(delete(SchemaEmbedding).where(SchemaEmbedding.database_connection_id == connection_id))
        await db.flush()

        # 2. Fetch tables and columns
        stmt = select(SchemaTable).where(
            SchemaTable.database_connection_id == connection_id,
            SchemaTable.organization_id == org_id
        )
        tables = (await db.execute(stmt)).scalars().all()

        if not tables:
            logger.warning(f"No tables found for connection {connection_id} to embed.")
            return

        table_ids = [t.id for t in tables]
        stmt_cols = select(SchemaColumn).where(SchemaColumn.table_id.in_(table_ids))
        columns = (await db.execute(stmt_cols)).scalars().all()

        col_map = {}
        for c in columns:
            col_map.setdefault(c.table_id, []).append(c)

        # 3. Fetch relationships
        stmt_rels = select(SchemaRelationship).where(
            SchemaRelationship.database_connection_id == connection_id
        )
        relationships = (await db.execute(stmt_rels)).scalars().all()

        embeddings_to_insert = []

        # A. Embed the whole database summary
        table_names = [f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}" for t in tables]
        db_summary = f"Database containing {len(tables)} tables: {', '.join(table_names)}."
        db_vec = await self._embed_text(db_summary)
        embeddings_to_insert.append(
            SchemaEmbedding(
                organization_id=org_id,
                database_connection_id=connection_id,
                object_type="database",
                object_name="database_summary",
                content=db_summary,
                embedding=db_vec
            )
        )

        # B. Embed each table
        for t in tables:
            t_cols = col_map.get(t.id, [])
            col_desc = []
            for c in t_cols:
                pk_str = " (Primary Key)" if c.is_primary_key else ""
                desc_str = f" - {c.column_description}" if c.column_description else ""
                col_desc.append(f"{c.column_name} ({c.data_type}){pk_str}{desc_str}")
            
            full_t_name = f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}"
            desc = t.table_description or "No description provided."
            content = f"Table {full_t_name}: {desc}. Columns: {', '.join(col_desc)}."
            
            vec = await self._embed_text(content)
            embeddings_to_insert.append(
                SchemaEmbedding(
                    organization_id=org_id,
                    database_connection_id=connection_id,
                    object_type="table",
                    object_name=full_t_name,
                    content=content,
                    embedding=vec
                )
            )

        # C. Embed each relationship
        for r in relationships:
            content = f"Relationship: Table {r.source_table} column {r.source_column} is a foreign key referencing Table {r.target_table} column {r.target_column}."
            vec = await self._embed_text(content)
            embeddings_to_insert.append(
                SchemaEmbedding(
                    organization_id=org_id,
                    database_connection_id=connection_id,
                    object_type="relationship",
                    object_name=f"{r.source_table}->{r.target_table}",
                    content=content,
                    embedding=vec
                )
            )

        # Batch insert
        db.add_all(embeddings_to_insert)
        await db.commit()
        logger.info(f"Successfully generated {len(embeddings_to_insert)} schema embeddings for connection {connection_id}")
