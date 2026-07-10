import redis.asyncio as redis
from engine.shared.config import get_settings

settings = get_settings()

class RedisClient:
    def __init__(self):
        self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def set_token(self, name: str, value: str, ex_min: int):
        """Store token with expiry in minutes."""
        await self.client.set(name, value, ex=ex_min * 60)

    async def get_token(self, name: str) -> str:
        """Retrieve token."""
        return await self.client.get(name)

    async def delete_token(self, name: str):
        """Remove token."""
        await self.client.delete(name)

    async def expire_token(self, name: str, ex_min: int):
        """Extend expiration of a token in minutes."""
        await self.client.expire(name, ex_min * 60)

    async def delete_keys_matching(self, pattern: str) -> None:
        """Delete all keys matching a glob pattern."""
        async for key in self.client.scan_iter(match=pattern, count=100):
            await self.client.delete(key)

redis_client = RedisClient()
