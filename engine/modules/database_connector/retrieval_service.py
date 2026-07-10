import logging
from uuid import UUID
from typing import List, Tuple, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.modules.database_connector.database_connector_models import (
    SchemaEmbedding,
    SchemaTable,
    SchemaColumn,
    SchemaRelationship,
)

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
            select(SchemaEmbedding.connector_id)
            .where(
                SchemaEmbedding.organization_id == org_id,
                SchemaEmbedding.object_type == "database",
            )
            .order_by(SchemaEmbedding.embedding.cosine_distance(question_embedding))
            .limit(top_k)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def find_relevant_tables(
        db: AsyncSession,
        question_embedding: List[float],
        org_id: UUID,
        connector_ids: List[UUID],
        top_k: int = 10,
    ) -> List[str]:
        """
        Finds the most relevant tables and relationships across candidate databases.
        """
        if not connector_ids:
            return []

        stmt = (
            select(SchemaEmbedding.object_name)
            .where(
                SchemaEmbedding.organization_id == org_id,
                SchemaEmbedding.connector_id.in_(connector_ids),
                SchemaEmbedding.object_type.in_(["table", "relationship"]),
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
        db: AsyncSession,
        org_id: UUID,
        connector_ids: List[UUID],
        relevant_object_names: List[str],
        question: Optional[str] = None,
    ) -> str:
        """
        Builds the markdown schema block to inject into the LLM prompt.
        """
        if not connector_ids or not relevant_object_names:
            return "No relevant database tables found."

        # Extract actual table names from the relevant objects
        table_names = set()
        for name in relevant_object_names:
            if "->" in name:  # It's a relationship
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
            SchemaTable.connector_id.in_(connector_ids),
        )
        tables = (await db.execute(stmt)).scalars().all()

        filtered_tables = []
        for t in tables:
            full_name = f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}"
            if full_name in table_names or t.table_name in table_names:
                filtered_tables.append(t)

        if not filtered_tables:
            return "No relevant database tables found."

        table_ids = [t.id for t in filtered_tables]
        stmt_cols = select(SchemaColumn).where(SchemaColumn.table_id.in_(table_ids))
        columns = (await db.execute(stmt_cols)).scalars().all()

        col_map = {}
        for c in columns:
            col_map.setdefault(c.table_id, []).append(c)

        # Fetch relationships early so we can identify FK columns
        stmt_rels = select(SchemaRelationship).where(
            SchemaRelationship.organization_id == org_id,
            SchemaRelationship.connector_id.in_(connector_ids),
        )
        rels = (await db.execute(stmt_rels)).scalars().all()

        # Build list of columns used in relationships
        fk_columns = set()
        for r in rels:
            fk_columns.add((r.source_table, r.source_column))
            fk_columns.add((r.target_table, r.target_column))

        # Parse question words for smart column matching
        query_words = set()
        if question:
            import re

            # Extract alphanumeric words of length >= 3
            query_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9_]{3,}", question)}

        # Detect broad-intent queries that want ALL columns (e.g. "all information",
        # "everything", "complete details"). Skip pruning entirely for these.
        broad_intent_keywords = {"all", "everything", "every", "complete", "full", "entire", "detail", "details"}
        wants_all_columns = bool(query_words & broad_intent_keywords)

        context_lines = []
        for t in filtered_tables:
            full_name = f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}"
            context_lines.append(f"CREATE TABLE {full_name} (")
            t_cols = col_map.get(t.id, [])

            # Smart column pruning logic
            keep_cols = []
            if not question or len(t_cols) <= 10 or wants_all_columns:
                # Keep all columns for short tables, broad-intent queries, or if no query was passed
                keep_cols = t_cols
            else:
                for c in t_cols:
                    # Always keep Primary Keys
                    if c.is_primary_key:
                        keep_cols.append(c)
                        continue

                    # Always keep Foreign Keys / Relationship columns
                    if (t.table_name, c.column_name) in fk_columns or (
                        full_name,
                        c.column_name,
                    ) in fk_columns:
                        keep_cols.append(c)
                        continue

                    # Keep column if name matches query terms
                    col_name_lower = c.column_name.lower()
                    if any(
                        word in col_name_lower or col_name_lower in word
                        for word in query_words
                    ):
                        keep_cols.append(c)
                        continue

                    # Keep column if description matches query terms
                    if c.column_description:
                        desc_lower = c.column_description.lower()
                        if any(word in desc_lower for word in query_words):
                            keep_cols.append(c)
                            continue

            col_defs = []
            for c in keep_cols:
                pk = " PK" if c.is_primary_key else ""
                comment = ""
                if c.column_description:
                    desc = c.column_description.strip()
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    comment = f" -- {desc}"
                col_defs.append(f"    {c.column_name} {c.data_type}{pk}{comment}")

            context_lines.append(",\n".join(col_defs))
            context_lines.append(");")
            if t.table_description:
                context_lines.append(f"-- Description: {t.table_description}\n")
            else:
                context_lines.append("\n")

        # Add relationships strictly where BOTH tables exist in the selected table_names
        active_table_names = {
            f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}"
            for t in filtered_tables
        }
        active_table_names.update({t.table_name for t in filtered_tables})

        filtered_rels = []
        for r in rels:
            if (r.source_table in active_table_names) and (
                r.target_table in active_table_names
            ):
                filtered_rels.append(
                    f"-- {r.source_table}.{r.source_column} -> {r.target_table}.{r.target_column}"
                )

        if filtered_rels:
            context_lines.append("-- Relationships:")
            context_lines.extend(filtered_rels)

        return "\n".join(context_lines)
