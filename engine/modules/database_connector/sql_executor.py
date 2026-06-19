import logging
import asyncio
from uuid import UUID
from typing import Dict, Any, Tuple, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import asyncpg

from engine.shared.models.connector_model import Connector
from engine.shared.models.credential_model import Credential
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
        stmt = select(Connector).where(
            Connector.id == connection_id,
            Connector.organization_id == org_id
        )
        result = await db.execute(stmt)
        conn_obj = result.scalars().first()
        
        if not conn_obj:
            raise ValueError(f"Database connection {connection_id} not found.")

        # Also get credential
        if not conn_obj.credential_id:
            raise ValueError(f"No credentials found for database connection {connection_id}.")
            
        cred_stmt = select(Credential).where(Credential.id == conn_obj.credential_id)
        cred_result = await db.execute(cred_stmt)
        cred_obj = cred_result.scalars().first()
        
        if not cred_obj:
            raise ValueError(f"Credential {conn_obj.credential_id} not found.")

        auth_data = cred_obj.auth_data

        database_type = conn_obj.connector_id # e.g., 'postgres', 'mysql'

        # 2. Safety wrapper (auto-limit if missing)
        upper_sql = sql.upper()
        if "LIMIT " not in upper_sql and database_type.lower() in ("postgresql", "postgres", "mysql"):
            sql = f"{sql.rstrip(';')} LIMIT 100"

        # 3. Get pool and execute
        pool = await pool_service.get_pool(str(conn_obj.id), database_type, auth_data)
        
        try:
            if database_type.lower() in ("postgresql", "postgres"):
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
            
            elif database_type.lower() == "mysql":
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
                raise ValueError(f"Unsupported database type: {database_type}")
                
        except asyncio.TimeoutError:
            logger.error("SQL query execution timed out")
            raise Exception("Query execution timed out. Try refining your question to query less data.")
        except asyncpg.InsufficientPrivilegeError as e:
            logger.error(f"SQL privilege error: {e}")
            raise Exception(f"Insufficient database privileges: {e}")
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            raise Exception(f"Query execution failed: {e}")
