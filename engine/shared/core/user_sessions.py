"""Redis-backed interactive user sessions (one key per device/login)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from engine.shared.config import get_settings
from engine.shared.core.redis import redis_client

settings = get_settings()

SESSION_ID_CLAIM = "sid"
LEGACY_SESSION_KEY_PREFIX = "user_session:"


def new_session_id() -> str:
    return str(uuid.uuid4())


def session_redis_key(admin_id: str, session_id: str) -> str:
    return f"{LEGACY_SESSION_KEY_PREFIX}{admin_id}:{session_id}"


def legacy_session_redis_key(admin_id: str) -> str:
    return f"{LEGACY_SESSION_KEY_PREFIX}{admin_id}"


async def save_session(
    admin_id: str,
    session_id: str,
    access_token: str,
    refresh_token: str,
) -> None:
    payload = {"access_token": access_token, "refresh_token": refresh_token}
    await redis_client.set_token(
        session_redis_key(admin_id, session_id),
        json.dumps(payload),
        settings.REFRESH_TOKEN_EXPIRE_MIN,
    )


async def get_session(admin_id: str, session_id: str) -> dict[str, Any] | None:
    raw = await redis_client.get_token(session_redis_key(admin_id, session_id))
    if not raw:
        return None
    return json.loads(raw)


async def touch_session(admin_id: str, session_id: str) -> None:
    await redis_client.expire_token(
        session_redis_key(admin_id, session_id),
        settings.REFRESH_TOKEN_EXPIRE_MIN,
    )


async def delete_session(admin_id: str, session_id: str) -> None:
    await redis_client.delete_token(session_redis_key(admin_id, session_id))


async def delete_all_sessions(admin_id: str) -> None:
    """Remove every device session for a user (e.g. password change)."""
    await redis_client.delete_token(legacy_session_redis_key(admin_id))
    pattern = f"{LEGACY_SESSION_KEY_PREFIX}{admin_id}:*"
    await redis_client.delete_keys_matching(pattern)
