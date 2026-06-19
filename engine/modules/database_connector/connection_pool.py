import asyncio
import logging
from typing import Dict, Any

import asyncpg
# import aiomysql  # Will be added for MySQL support

from engine.modules.database_connector.models import DatabaseConnection

logger = logging.getLogger(__name__)

class ExternalConnectionPoolService:
    """
    Singleton service managing connection pools to external tenant databases.
    This drastically reduces query latency by keeping connections warm.
    """
    _instance = None
    _pools: Dict[str, Any] = {}
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExternalConnectionPoolService, cls).__new__(cls)
        return cls._instance

    async def get_pool(self, conn_obj: DatabaseConnection):
        """Gets or creates an async connection pool for the given external database."""
        pool_key = str(conn_obj.id)
        
        async with self._lock:
            if pool_key in self._pools:
                return self._pools[pool_key]
                
            logger.info(f"Creating new connection pool for external database {pool_key}")
            
            try:
                if conn_obj.database_type.lower() == "postgresql":
                    pool = await asyncpg.create_pool(
                        user=conn_obj.username,
                        password=conn_obj.password,
                        database=conn_obj.database_name,
                        host=conn_obj.host,
                        port=conn_obj.port,
                        min_size=1,
                        max_size=10,
                        command_timeout=30.0
                    )
                elif conn_obj.database_type.lower() == "mysql":
                    import aiomysql
                    pool = await aiomysql.create_pool(
                        host=conn_obj.host,
                        port=conn_obj.port,
                        user=conn_obj.username,
                        password=conn_obj.password,
                        db=conn_obj.database_name,
                        minsize=1,
                        maxsize=10
                    )
                else:
                    raise ValueError(f"Unsupported database type: {conn_obj.database_type}")
                
                self._pools[pool_key] = pool
                return pool
                
            except Exception as e:
                logger.error(f"Failed to create connection pool for {pool_key}: {e}")
                raise

    async def close_all_pools(self):
        """Gracefully shuts down all external connection pools."""
        async with self._lock:
            for pool_key, pool in self._pools.items():
                logger.info(f"Closing pool {pool_key}")
                if hasattr(pool, 'close'):
                    # aiomysql / asyncpg generic close pattern
                    if asyncio.iscoroutinefunction(pool.close):
                        await pool.close()
                    else:
                        pool.close()
                        if hasattr(pool, 'wait_closed'):
                            await pool.wait_closed()
            self._pools.clear()

# Global singleton instance
pool_service = ExternalConnectionPoolService()
