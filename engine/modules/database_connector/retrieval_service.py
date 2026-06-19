import logging
from uuid import UUID
from typing import List, Tuple, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.modules.database_connector.models import SchemaEmbedding, SchemaTable, SchemaColumn, SchemaRelationship

logger = logging.getLogger(__name__)

class DatabaseRetrievalService:
    @staticmethod
    async def find_relevant_database(
        db: AsyncSession, question_embedding: List[float], org_id: UUID, top_k: int = 3
    ) -> List[UUID]:
        """
        Finds the most relevant databases for a given question using pgvector cosine similarity.
        """
        # `<=>` is the cosine distance operator in pgvector
        stmt = (
            select(SchemaEmbedding.database_connection_id)
            .where(
                SchemaEmbedding.organization_id == org_id,
                SchemaEmbedding.object_type == "database"
            )
            .order_by(SchemaEmbedding.embedding.cosine_distance(question_embedding))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def find_relevant_tables(
        db: AsyncSession, question_embedding: List[float], org_id: UUID, database_connection_ids: List[UUID], top_k: int = 10
    ) -> List[str]:
        """
        Finds the most relevant tables and relationships across candidate databases.
        """
        if not database_connection_ids:
            return []

        stmt = (
            select(SchemaEmbedding.object_name)
            .where(
                SchemaEmbedding.organization_id == org_id,
                SchemaEmbedding.database_connection_id.in_(database_connection_ids),
                SchemaEmbedding.object_type.in_(["table", "relationship"])
            )
            .order_by(SchemaEmbedding.embedding.cosine_distance(question_embedding))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        
        # Some object names might be relationships (A->B), some are tables.
        # We just return the list of raw object names for now.
        return list(result.scalars().all())

    @staticmethod
    async def build_schema_context(
        db: AsyncSession, org_id: UUID, database_connection_ids: List[UUID], relevant_object_names: List[str]
    ) -> str:
        """
        Builds the markdown schema block to inject into the LLM prompt.
        """
        if not database_connection_ids or not relevant_object_names:
            return "No relevant database tables found."

        # Extract actual table names from the relevant objects
        table_names = set()
        for name in relevant_object_names:
            if "->" in name: # It's a relationship
                parts = name.split("->")
                table_names.add(parts[0])
                table_names.add(parts[1])
            else:
                table_names.add(name)

        if not table_names:
            return "No relevant database tables found."

        # Fetch actual table models
        stmt = select(SchemaTable).where(
            SchemaTable.organization_id == org_id,
            SchemaTable.database_connection_id.in_(database_connection_ids)
        )
        # In a real scenario we might want to filter by table_names specifically
        # but because schema_name.table_name is what we stored, we need to match it.
        tables = (await db.execute(stmt)).scalars().all()
        
        filtered_tables = []
        for t in tables:
            full_name = f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}"
            if full_name in table_names:
                filtered_tables.append(t)

        if not filtered_tables:
            return "No relevant database tables found."

        table_ids = [t.id for t in filtered_tables]
        stmt_cols = select(SchemaColumn).where(SchemaColumn.table_id.in_(table_ids))
        columns = (await db.execute(stmt_cols)).scalars().all()

        col_map = {}
        for c in columns:
            col_map.setdefault(c.table_id, []).append(c)

        context_lines = []
        for t in filtered_tables:
            full_name = f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}"
            context_lines.append(f"CREATE TABLE {full_name} (")
            t_cols = col_map.get(t.id, [])
            col_defs = []
            for c in t_cols:
                pk = " PRIMARY KEY" if c.is_primary_key else ""
                null = " NULL" if c.is_nullable else " NOT NULL"
                comment = f" -- {c.column_description}" if c.column_description else ""
                col_defs.append(f"    {c.column_name} {c.data_type}{pk}{null}{comment}")
            context_lines.append(",\n".join(col_defs))
            context_lines.append(");")
            if t.table_description:
                context_lines.append(f"-- Description: {t.table_description}\n")
            else:
                context_lines.append("\n")

        # Add relationships
        stmt_rels = select(SchemaRelationship).where(
            SchemaRelationship.organization_id == org_id,
            SchemaRelationship.database_connection_id.in_(database_connection_ids)
        )
        rels = (await db.execute(stmt_rels)).scalars().all()
        
        if rels:
            context_lines.append("-- Relationships:")
            for r in rels:
                if r.source_table in table_names or r.target_table in table_names:
                    context_lines.append(f"-- {r.source_table}.{r.source_column} -> {r.target_table}.{r.target_column}")

        return "\n".join(context_lines)
