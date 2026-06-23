import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from engine.modules.assistant.assistant_models import Assistant, AssistantQueryCache

logger = logging.getLogger(__name__)

class SemanticCacheService:
    @staticmethod
    async def lookup_cache(
        db: AsyncSession,
        assistant_id: UUID,
        query_embedding: List[float],
        cache_version: int,
        threshold: float = 0.95
    ) -> Optional[AssistantQueryCache]:
        """
        Look up the semantically closest cached query for this assistant.
        Bypass if the query is older than the current cache_version of the assistant.
        """
        max_distance = 1.0 - threshold
        
        stmt = (
            select(AssistantQueryCache)
            .where(
                AssistantQueryCache.assistant_id == assistant_id,
                AssistantQueryCache.cache_version == cache_version,
                AssistantQueryCache.expires_at > datetime.now(timezone.utc).replace(tzinfo=None),
                AssistantQueryCache.query_embedding.cosine_distance(query_embedding) <= max_distance
            )
            .order_by(AssistantQueryCache.query_embedding.cosine_distance(query_embedding))
            .limit(1)
        )
        result = await db.execute(stmt)
        match = result.scalars().first()
        
        if match:
            logger.info(f"Semantic cache hit for assistant {assistant_id}")
            return match
            
        return None

    @staticmethod
    async def write_cache(
        db: AsyncSession,
        assistant_id: UUID,
        query: str,
        query_embedding: List[float],
        response: str,
        sources: Optional[List[Dict[str, Any]]],
        source_chunk_ids: Optional[List[UUID]],
        cache_version: int,
        ttl_days: int = 7
    ) -> AssistantQueryCache:
        """
        Write a new cache entry.
        """
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=ttl_days)
        
        cache_entry = AssistantQueryCache(
            assistant_id=assistant_id,
            query=query,
            query_embedding=query_embedding,
            response=response,
            sources=sources,
            source_chunk_ids=source_chunk_ids,
            cache_version=cache_version,
            expires_at=expires_at
        )
        
        db.add(cache_entry)
        await db.commit()
        await db.refresh(cache_entry)
        logger.info(f"Wrote semantic cache for assistant {assistant_id}")
        return cache_entry

    @staticmethod
    async def invalidate_workspace_cache(db: AsyncSession, workspace_id: UUID) -> None:
        """
        Increment the cache_version for all assistants in a workspace.
        This effectively invalidates their semantic caches.
        """
        logger.info(f"Invalidating semantic cache for workspace {workspace_id}")
        stmt = (
            update(Assistant)
            .where(Assistant.organization_id == workspace_id)
            .values(cache_version=Assistant.cache_version + 1)
        )
        await db.execute(stmt)
        await db.commit()
        
    @staticmethod
    async def cleanup_expired_cache(db: AsyncSession) -> int:
        """
        Delete expired cache entries. Can be run periodically.
        """
        stmt = delete(AssistantQueryCache).where(
            AssistantQueryCache.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount
