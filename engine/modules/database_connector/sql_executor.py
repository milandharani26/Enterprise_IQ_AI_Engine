import logging
import asyncio
from uuid import UUID
from typing import Dict, Any, Tuple, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncpg

from engine.modules.database_connector.models import DatabaseConnection
from engine.modules.database_connector.connection_pool import pool_service

logger = logging.getLogger(__name__)

class SqlExecutionService:
    @staticmethod
    async def execute_query(
        db: AsyncSession, connection_id: UUID, org_id: UUID, sql: str, timeout_seconds: int = 30
    ) -> Tuple[List[str], List[Dict[str, Any]], int]:
        """
        Executes a SQL query against an external database via a connection pool.
        Returns (columns, rows, row_count).
        """
        logger.info(f"Executing SQL query on connection {connection_id}")
        
        # 1. Fetch connection details
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.organization_id == org_id,
            DatabaseConnection.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        conn_obj = result.scalars().first()
        
        if not conn_obj:
            raise ValueError(f"Database connection {connection_id} not found.")

        # 2. Safety wrapper (auto-limit if missing)
        upper_sql = sql.upper()
        if "LIMIT " not in upper_sql and conn_obj.database_type.lower() in ("postgresql", "mysql"):
            sql = f"{sql.rstrip(';')} LIMIT 100"

        # 3. Get pool and execute
        pool = await pool_service.get_pool(conn_obj)
        
        try:
            if conn_obj.database_type.lower() == "postgresql":
                async with pool.acquire() as conn:
                    # Enforce read-only at transaction level
                    async with conn.transaction(readonly=True):
                        # Use timeout
                        stmt = await conn.prepare(sql)
                        records = await asyncio.wait_for(stmt.fetch(), timeout=timeout_seconds)
                        
                        if not records:
                            return [], [], 0
                            
                        columns = list(records[0].keys())
                        rows = [dict(r) for r in records]
                        return columns, rows, len(rows)
            
            elif conn_obj.database_type.lower() == "mysql":
                import aiomysql
                async with pool.acquire() as conn:
                    async with conn.cursor(aiomysql.DictCursor) as cur:
                        # Enforce read-only
                        await cur.execute("SET SESSION TRANSACTION READ ONLY")
                        await asyncio.wait_for(cur.execute(sql), timeout=timeout_seconds)
                        rows = await cur.fetchall()
                        
                        if not rows:
                            return [], [], 0
                            
                        columns = list(rows[0].keys())
                        return columns, list(rows), len(rows)
            else:
                raise ValueError(f"Unsupported database type: {conn_obj.database_type}")
                
        except asyncio.TimeoutError:
            logger.error("SQL query execution timed out")
            raise Exception("Query execution timed out. Try refining your question to query less data.")
        except asyncpg.InsufficientPrivilegeError as e:
            logger.error(f"SQL privilege error: {e}")
            raise Exception(f"Insufficient database privileges: {e}")
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise Exception(f"Query execution failed: {e}")
