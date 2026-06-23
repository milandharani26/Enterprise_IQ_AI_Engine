import logging
from uuid import UUID
from typing import Dict, List, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import asyncpg
# import aiomysql  # Will be added for MySQL support

from engine.modules.database_connector.database_connector_models import (
    SchemaTable,
    SchemaColumn,
    SchemaRelationship,
    SchemaEmbedding
)
from engine.shared.models.connector_model import Connector
from engine.shared.models.credential_model import Credential
from engine.pipelines.ingestion.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class SchemaCrawlerService:
    async def sync_database_schema(self, db: AsyncSession, connection_id: UUID, org_id: UUID):
        """Orchestrates the syncing of schema from external database to our metadata tables."""
        logger.info(f"Starting schema sync for connection {connection_id}")
        
        # 1. Fetch connection details
        stmt = select(Connector).where(
            Connector.id == connection_id,
            Connector.organization_id == org_id
        )
        result = await db.execute(stmt)
        conn_obj = result.scalars().first()
        
        if not conn_obj:
            logger.error(f"Connection {connection_id} not found or deleted.")
            return

        cred_stmt = select(Credential).where(Credential.id == conn_obj.credential_id)
        cred_result = await db.execute(cred_stmt)
        cred_obj = cred_result.scalars().first()
        
        if not cred_obj:
            logger.error(f"Credential {conn_obj.credential_id} not found for connection.")
            return

        conn_obj.sync_status = "syncing"
        await db.commit()

        auth_data = cred_obj.auth_data
        database_type = conn_obj.connector_id

        try:
            # 2. Extract metadata based on DB type
            if database_type.lower() in ("postgresql", "postgres"):
                tables, columns, relationships = await self._crawl_postgres(auth_data)
            elif database_type.lower() == "mysql":
                tables, columns, relationships = await self._crawl_mysql(auth_data)
            else:
                raise ValueError(f"Unsupported database type: {database_type}")

            # 3. Persist metadata
            await self._persist_metadata(db, conn_obj, tables, columns, relationships)

            # 4. Generate embeddings using batched pipeline service
            await self._generate_embeddings(db, connection_id, org_id)

            # 5. Update status
            conn_obj.sync_status = "synced"
            from datetime import datetime
            conn_obj.last_synced_at = datetime.utcnow()
            conn_obj.sync_error = None
            
            # Invalidate semantic cache for the organization
            from engine.modules.assistant.semantic_cache import SemanticCacheService
            await SemanticCacheService.invalidate_workspace_cache(db, org_id)
            
            await db.commit()
            logger.info(f"Schema sync completed successfully for connection {connection_id}")

        except Exception as e:
            logger.exception(f"Schema sync failed for connection {connection_id}")
            conn_obj.sync_status = "failed"
            conn_obj.sync_error = str(e)
            await db.commit()

    async def _generate_embeddings(self, db: AsyncSession, connection_id: UUID, org_id: UUID):
        """Generates natural language descriptions of tables and relationships, and embeds them."""
        logger.info(f"Generating schema embeddings for connection {connection_id}")

        # 1. Clear old embeddings
        await db.execute(delete(SchemaEmbedding).where(SchemaEmbedding.connector_id == connection_id))
        await db.flush()

        # 2. Fetch tables and columns
        stmt = select(SchemaTable).where(
            SchemaTable.connector_id == connection_id,
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
            SchemaRelationship.connector_id == connection_id
        )
        relationships = (await db.execute(stmt_rels)).scalars().all()

        embeddings_to_insert = []
        all_texts = []
        embed_defs = []

        # A. Embed the whole database summary
        table_names = [f"{t.schema_name + '.' if t.schema_name else ''}{t.table_name}" for t in tables]
        db_summary = f"Database containing {len(tables)} tables: {', '.join(table_names)}."
        all_texts.append(db_summary)
        embed_defs.append({
            "object_type": "database",
            "object_name": "database_summary",
            "content": db_summary
        })

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
            all_texts.append(content)
            embed_defs.append({
                "object_type": "table",
                "object_name": full_t_name,
                "content": content
            })

        # C. Embed each relationship
        for r in relationships:
            content = f"Relationship: Table {r.source_table} column {r.source_column} is a foreign key referencing Table {r.target_table} column {r.target_column}."
            all_texts.append(content)
            embed_defs.append({
                "object_type": "relationship",
                "object_name": f"{r.source_table}->{r.target_table}",
                "content": content
            })

        # Batch embed
        pipeline_embed_svc = EmbeddingService()
        vectors = await pipeline_embed_svc.embed_chunks(all_texts)

        for i, vec in enumerate(vectors):
            meta = embed_defs[i]
            embeddings_to_insert.append(
                SchemaEmbedding(
                    organization_id=org_id,
                    connector_id=connection_id,
                    object_type=meta["object_type"],
                    object_name=meta["object_name"],
                    content=meta["content"],
                    embedding=vec
                )
            )

        # Batch insert
        db.add_all(embeddings_to_insert)
        await db.commit()
        logger.info(f"Successfully generated {len(embeddings_to_insert)} schema embeddings for connection {connection_id}")

    async def _crawl_postgres(self, auth_data: dict):
        """Connects to PostgreSQL and extracts schema metadata."""
        schema_filter = auth_data.get('schema') or 'public'
        
        try:
            conn = await asyncpg.connect(
                user=auth_data.get('username'),
                password=auth_data.get('password'),
                database=auth_data.get('database'),
                host=auth_data.get('host'),
                port=int(auth_data.get('port')),
            )
        except Exception as e:
            raise Exception(f"Failed to connect to PostgreSQL: {e}")

        try:
            # Fetch Tables with descriptions
            tables_query = f"""
                SELECT 
                    t.table_name,
                    obj_description(pgc.oid, 'pg_class') AS table_description
                FROM information_schema.tables t
                JOIN pg_class pgc ON pgc.relname = t.table_name
                JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace AND pgn.nspname = t.table_schema
                WHERE t.table_schema = $1 AND t.table_type = 'BASE TABLE'
            """
            table_rows = await conn.fetch(tables_query, schema_filter)
            tables = [
                {
                    "table_name": r["table_name"],
                    "schema_name": schema_filter,
                    "table_description": r["table_description"]
                }
                for r in table_rows
            ]

            # Fetch Columns with descriptions
            columns_query = f"""
                SELECT 
                    cols.table_name, 
                    cols.column_name, 
                    cols.data_type, 
                    cols.is_nullable, 
                    cols.ordinal_position, 
                    cols.column_default,
                    col_description(pgc.oid, cols.ordinal_position::int) AS column_description
                FROM information_schema.columns cols
                JOIN pg_class pgc ON pgc.relname = cols.table_name
                JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace AND pgn.nspname = cols.table_schema
                WHERE cols.table_schema = $1
            """
            col_rows = await conn.fetch(columns_query, schema_filter)
            columns = []
            for r in col_rows:
                columns.append({
                    "table_name": r["table_name"],
                    "column_name": r["column_name"],
                    "data_type": r["data_type"],
                    "is_nullable": r["is_nullable"] == 'YES',
                    "ordinal_position": r["ordinal_position"],
                    "default_value": r["column_default"],
                    "column_description": r["column_description"],
                    "is_primary_key": False # Will be updated in next query
                })

            # Fetch Primary Keys
            pk_query = f"""
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tco
                JOIN information_schema.key_column_usage kcu 
                  ON kcu.constraint_name = tco.constraint_name
                  AND kcu.constraint_schema = tco.constraint_schema
                WHERE tco.constraint_type = 'PRIMARY KEY' AND tco.table_schema = $1
            """
            pk_rows = await conn.fetch(pk_query, schema_filter)
            pk_set = {(r["table_name"], r["column_name"]) for r in pk_rows}
            for col in columns:
                if (col["table_name"], col["column_name"]) in pk_set:
                    col["is_primary_key"] = True

            # Fetch Foreign Keys
            fk_query = f"""
                SELECT
                    tc.table_name AS source_table,
                    kcu.column_name AS source_column,
                    ccu.table_name AS target_table,
                    ccu.column_name AS target_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = $1
            """
            fk_rows = await conn.fetch(fk_query, schema_filter)
            relationships = []
            for r in fk_rows:
                relationships.append({
                    "source_table": r["source_table"],
                    "source_column": r["source_column"],
                    "target_table": r["target_table"],
                    "target_column": r["target_column"]
                })

            return tables, columns, relationships
        finally:
            await conn.close()

    async def _crawl_mysql(self, auth_data: dict):
        """Connects to MySQL and extracts schema metadata."""
        import aiomysql
        schema_filter = auth_data.get('schema') or auth_data.get('database')
        
        try:
            conn = await aiomysql.connect(
                host=auth_data.get('host'),
                port=int(auth_data.get('port')),
                user=auth_data.get('username'),
                password=auth_data.get('password'),
                db=auth_data.get('database'),
            )
        except Exception as e:
            raise Exception(f"Failed to connect to MySQL: {e}")

        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Fetch Tables with comments
                await cur.execute(
                    "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'",
                    (schema_filter,)
                )
                table_rows = await cur.fetchall()
                tables = [
                    {
                        "table_name": r["TABLE_NAME"],
                        "schema_name": schema_filter,
                        "table_description": r.get("TABLE_COMMENT")
                    }
                    for r in table_rows
                ]

                # Fetch Columns with comments
                await cur.execute(
                    "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION, COLUMN_DEFAULT, COLUMN_KEY, COLUMN_COMMENT "
                    "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s",
                    (schema_filter,)
                )
                col_rows = await cur.fetchall()
                columns = []
                for r in col_rows:
                    columns.append({
                        "table_name": r["TABLE_NAME"],
                        "column_name": r["COLUMN_NAME"],
                        "data_type": r["DATA_TYPE"],
                        "is_nullable": r["IS_NULLABLE"] == 'YES',
                        "ordinal_position": r["ORDINAL_POSITION"],
                        "default_value": r["COLUMN_DEFAULT"],
                        "column_description": r.get("COLUMN_COMMENT"),
                        "is_primary_key": r["COLUMN_KEY"] == 'PRI'
                    })

                # Fetch Foreign Keys
                await cur.execute(
                    "SELECT TABLE_NAME as source_table, COLUMN_NAME as source_column, "
                    "REFERENCED_TABLE_NAME as target_table, REFERENCED_COLUMN_NAME as target_column "
                    "FROM information_schema.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL",
                    (schema_filter,)
                )
                fk_rows = await cur.fetchall()
                relationships = []
                for r in fk_rows:
                    relationships.append({
                        "source_table": r["source_table"],
                        "source_column": r["source_column"],
                        "target_table": r["target_table"],
                        "target_column": r["target_column"]
                    })

                return tables, columns, relationships
        finally:
            conn.close()

    async def _persist_metadata(self, db: AsyncSession, conn_obj: Connector, tables: list, columns: list, relationships: list):
        """Saves metadata to database, replacing old records."""
        
        # 1. Delete existing relationships and tables (cascades to columns and embeddings)
        await db.execute(delete(SchemaRelationship).where(SchemaRelationship.connector_id == conn_obj.id))
        await db.execute(delete(SchemaTable).where(SchemaTable.connector_id == conn_obj.id))
        await db.flush()

        # 2. Insert Tables
        table_objs = []
        table_map = {} # map table_name -> UUID
        for t in tables:
            obj = SchemaTable(
                organization_id=conn_obj.organization_id,
                connector_id=conn_obj.id,
                schema_name=t["schema_name"],
                table_name=t["table_name"],
                table_description=t.get("table_description")
            )
            db.add(obj)
            table_objs.append(obj)
        
        await db.flush()
        
        for obj in table_objs:
            table_map[obj.table_name] = obj.id

        # 3. Insert Columns
        col_objs = []
        for c in columns:
            table_id = table_map.get(c["table_name"])
            if not table_id:
                continue # Edge case
            obj = SchemaColumn(
                table_id=table_id,
                column_name=c["column_name"],
                data_type=c["data_type"],
                is_nullable=c["is_nullable"],
                is_primary_key=c["is_primary_key"],
                default_value=str(c["default_value"]) if c["default_value"] is not None else None,
                column_description=c.get("column_description"),
                ordinal_position=c["ordinal_position"]
            )
            col_objs.append(obj)
        
        if col_objs:
            db.add_all(col_objs)

        # 4. Insert Relationships
        rel_objs = []
        for r in relationships:
            obj = SchemaRelationship(
                organization_id=conn_obj.organization_id,
                connector_id=conn_obj.id,
                source_table=r["source_table"],
                source_column=r["source_column"],
                target_table=r["target_table"],
                target_column=r["target_column"]
            )
            rel_objs.append(obj)
        
        if rel_objs:
            db.add_all(rel_objs)

        await db.commit()
