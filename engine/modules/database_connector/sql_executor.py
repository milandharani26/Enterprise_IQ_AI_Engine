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

from shared.logging import get_logger
logger = get_logger("sql_executor")

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
        logger.info(f"Retrieving connection details from database for connector ID: {connection_id}")
        stmt = select(Connector).where(
            Connector.id == connection_id,
            Connector.organization_id == org_id
        )
        try:
            result = await db.execute(stmt)
            conn_obj = result.scalars().first()
        except Exception as e:
            logger.error(f"Failed to query local database for connection {connection_id}: {e}")
            raise Exception(f"Failed to retrieve database connection from repository: {e}")
        
        if not conn_obj:
            logger.error(f"Database connection {connection_id} not found in database records.")
            raise ValueError(f"Database connection {connection_id} not found.")

        # Also get credential
        if not conn_obj.credential_id:
            logger.error(f"No credentials ID associated with database connection '{conn_obj.name}' (ID: {connection_id}).")
            raise ValueError(f"No credentials found for database connection {connection_id}.")
            
        logger.info(f"Retrieving credentials from database for credential ID: {conn_obj.credential_id}")
        cred_stmt = select(Credential).where(Credential.id == conn_obj.credential_id)
        try:
            cred_result = await db.execute(cred_stmt)
            cred_obj = cred_result.scalars().first()
        except Exception as e:
            logger.error(f"Failed to query credentials for credential ID {conn_obj.credential_id}: {e}")
            raise Exception(f"Failed to retrieve database credentials from repository: {e}")
        
        if not cred_obj:
            logger.error(f"Credential record {conn_obj.credential_id} not found in database records.")
            raise ValueError(f"Credential {conn_obj.credential_id} not found.")

        auth_data = cred_obj.auth_data
        database_type = conn_obj.connector_id # e.g., 'postgres', 'mysql'

        logger.info(
            f"Successfully retrieved connection details for '{conn_obj.name}'. "
            f"Database Type: {database_type}, Host: {auth_data.get('host')}, Port: {auth_data.get('port')}, Database Name: {auth_data.get('database')}"
        )

        # 2. Safety wrapper (auto-limit if missing)
        upper_sql = sql.upper()
        if "LIMIT " not in upper_sql and database_type.lower() in ("postgresql", "postgres", "mysql"):
            sql = f"{sql.rstrip(';')} LIMIT 100"

        # 3. Get pool and execute
        logger.info(f"Retrieving/creating connection pool for '{conn_obj.name}' (Key: {conn_obj.id})...")
        try:
            pool = await pool_service.get_pool(str(conn_obj.id), database_type, auth_data)
            logger.info("Connection pool successfully retrieved/created.")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool for external database: {e}")
            raise Exception(f"Failed to establish database connection pool: {e}")
        
        logger.info("Acquiring connection from pool and executing query...")
        try:
            if database_type.lower() in ("postgresql", "postgres"):
                async with pool.acquire() as conn:
                    # Enforce read-only at transaction level
                    async with conn.transaction(readonly=True):
                        # Use timeout
                        stmt = await conn.prepare(sql)
                        records = await asyncio.wait_for(stmt.fetch(), timeout=timeout_seconds)
                        
                        if not records:
                            logger.info("Query executed successfully, returned 0 rows.")
                            return [], [], 0
                            
                        columns = list(records[0].keys())
                        rows = [dict(r) for r in records]
                        logger.info(f"Query executed successfully, returned {len(rows)} rows.")
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
                            logger.info("Query executed successfully, returned 0 rows.")
                            return [], [], 0
                            
                        columns = list(rows[0].keys())
                        logger.info(f"Query executed successfully, returned {len(rows)} rows.")
                        return columns, list(rows), len(rows)
            else:
                logger.error(f"Unsupported database type attempted: {database_type}")
                raise ValueError(f"Unsupported database type: {database_type}")
                
        except asyncio.TimeoutError:
            logger.error("SQL query execution timed out")
            raise Exception("Query execution timed out. Try refining your question to query less data.")
        except asyncpg.InsufficientPrivilegeError as e:
            logger.error(f"SQL privilege error on database connection: {e}")
            raise Exception(f"Insufficient database privileges: {e}")
        except Exception as e:
            err_name = type(e).__name__
            err_msg = str(e).lower()
            logger.error(f"External database execution failed: class={err_name}, error={e}")
            
            # Check for credential / auth failure
            if "password" in err_msg or "auth" in err_msg or "access denied" in err_msg or "invalidauthorization" in err_msg.lower():
                logger.error(f"Database authentication check failed for connector {conn_obj.name}: {e}")
                raise Exception(f"Database credentials validation failed: {e}")
            # Check for invalid database name
            elif "database" in err_msg and ("unknown" in err_msg or "does not exist" in err_msg or "invalidcatalogname" in err_msg.lower()):
                logger.error(f"Database '{auth_data.get('database')}' does not exist on host: {e}")
                raise Exception(f"Database '{auth_data.get('database')}' not found on host: {e}")
            # Check for network / connection refusal
            elif "connection refused" in err_msg or "cant_connect" in err_msg or "conn" in err_msg or "host" in err_msg or "unreachable" in err_msg:
                logger.error(f"Network connectivity check failed for host {auth_data.get('host')}: {e}")
                raise Exception(f"Failed to connect to database server (host={auth_data.get('host')}, port={auth_data.get('port')}): {e}")
            else:
                raise Exception(f"Query execution failed: {e}")
