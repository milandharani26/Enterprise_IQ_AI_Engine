import logging
from uuid import UUID
from typing import Dict, List, Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import asyncpg
# import aiomysql  # Will be added for MySQL support

from engine.modules.database_connector.models import (
    DatabaseConnection,
    SchemaTable,
    SchemaColumn,
    SchemaRelationship
)
from engine.modules.database_connector.embedding_service import SchemaEmbeddingService

logger = logging.getLogger(__name__)

class SchemaCrawlerService:
    async def sync_database_schema(self, db: AsyncSession, connection_id: UUID, org_id: UUID):
        """Orchestrates the syncing of schema from external database to our metadata tables."""
        logger.info(f"Starting schema sync for connection {connection_id}")
        
        # 1. Fetch connection details
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.organization_id == org_id,
            DatabaseConnection.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        conn_obj = result.scalars().first()
        
        if not conn_obj:
            logger.error(f"Connection {connection_id} not found or deleted.")
            return

        conn_obj.sync_status = "syncing"
        await db.commit()

        try:
            # 2. Extract metadata based on DB type
            if conn_obj.database_type.lower() == "postgresql":
                tables, columns, relationships = await self._crawl_postgres(conn_obj)
            elif conn_obj.database_type.lower() == "mysql":
                tables, columns, relationships = await self._crawl_mysql(conn_obj)
            else:
                raise ValueError(f"Unsupported database type: {conn_obj.database_type}")

            # 3. Persist metadata
            await self._persist_metadata(db, conn_obj, tables, columns, relationships)

            # 4. Generate embeddings
            embedding_service = SchemaEmbeddingService()
            await embedding_service.generate_embeddings(db, connection_id, org_id)

            # 5. Update status
            conn_obj.sync_status = "synced"
            from datetime import datetime
            conn_obj.last_synced_at = datetime.utcnow()
            conn_obj.sync_error = None
            await db.commit()
            logger.info(f"Schema sync completed successfully for connection {connection_id}")

        except Exception as e:
            logger.exception(f"Schema sync failed for connection {connection_id}")
            conn_obj.sync_status = "failed"
            conn_obj.sync_error = str(e)
            await db.commit()

    async def _crawl_postgres(self, conn_obj: DatabaseConnection):
        """Connects to PostgreSQL and extracts schema metadata."""
        schema_filter = conn_obj.schema_name or 'public'
        
        try:
            conn = await asyncpg.connect(
                user=conn_obj.username,
                password=conn_obj.password,
                database=conn_obj.database_name,
                host=conn_obj.host,
                port=conn_obj.port,
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

    async def _crawl_mysql(self, conn_obj: DatabaseConnection):
        """Connects to MySQL and extracts schema metadata."""
        import aiomysql
        schema_filter = conn_obj.schema_name or conn_obj.database_name
        
        try:
            conn = await aiomysql.connect(
                host=conn_obj.host,
                port=conn_obj.port,
                user=conn_obj.username,
                password=conn_obj.password,
                db=conn_obj.database_name,
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

    async def _persist_metadata(self, db: AsyncSession, conn_obj: DatabaseConnection, tables: list, columns: list, relationships: list):
        """Saves metadata to database, replacing old records."""
        
        # 1. Delete existing relationships and tables (cascades to columns and embeddings)
        await db.execute(delete(SchemaRelationship).where(SchemaRelationship.database_connection_id == conn_obj.id))
        await db.execute(delete(SchemaTable).where(SchemaTable.database_connection_id == conn_obj.id))
        await db.flush()

        # 2. Insert Tables
        table_objs = []
        table_map = {} # map table_name -> UUID
        for t in tables:
            obj = SchemaTable(
                organization_id=conn_obj.organization_id,
                database_connection_id=conn_obj.id,
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
                database_connection_id=conn_obj.id,
                source_table=r["source_table"],
                source_column=r["source_column"],
                target_table=r["target_table"],
                target_column=r["target_column"]
            )
            rel_objs.append(obj)
        
        if rel_objs:
            db.add_all(rel_objs)

        await db.commit()
