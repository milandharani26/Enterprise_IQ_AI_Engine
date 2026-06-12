from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
from loguru import logger

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.core.security import JWTService


auth_scheme = APIKeyHeader(name="Authorization", auto_error=False)
jwt_service = JWTService()

@dataclass
class BaseDeps:
    """Base typed container for domain endpoint dependencies."""
    db: AsyncSession
    current_user: object  # Use object to avoid circular import issues

async def get_db():
    """Yield async DB session for dependency injection. Closes on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(auth_scheme)
):
    # Delayed import to avoid circular import
    from engine.modules.auth.models.user import User
    """Validate token and return current user."""
    # AuthMiddleware already validates bearer tokens and attaches a user.
    # Reuse it to avoid duplicate DB lookups on every request.
    request_user = getattr(request.state, "user", None)
    if request_user is not None:
        return request_user

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Session required",
        )

    # Clean token (remove 'Bearer ' if present in the input)
    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "")
    
    # Try to decode and verify the token
    try:
        payload = jwt_service.verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=423,
            detail="Your session has expired. Please login again",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    try:
        user_id = UUID(user_id_raw) if isinstance(user_id_raw, str) else user_id_raw
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalars().first()
    except Exception as e:
        logger.exception(
            "Auth DB lookup failed for user_id={}: {}", user_id_raw, e
        )
        raise HTTPException(
            status_code=500,
            detail="Authentication service temporarily unavailable",
        )
 
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )
 
    # Validation Checks
    # Validation Checks
    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is disabled",
        )

    # Expiry check (DB-level) – apply only to interactive users.
    # Service accounts rely on JWT expiry + token_hash rotation instead.
    expires_at = getattr(user, "expires_at", None)
    if user.account_type != "service_account" and expires_at:
        now = datetime.utcnow()
        if expires_at < now:
            raise HTTPException(
                status_code=423,
                detail="Your session has expired. Please login again",
            )

    # Token hash check (critical for service accounts to invalidate old JWTs on rotation)
    jwt_token_hash = payload.get("token_hash")
    if jwt_token_hash:
        if user.password_hash != jwt_token_hash:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session"
            )

    return user

async def get_current_admin(current_user = Depends(get_current_user)):
    # Delayed import to avoid circular import
    from engine.modules.auth.models.user import User
    """Ensure the current user is an admin (interactive account)."""
    # if current_user.account_type != "interactive":
    #     raise HTTPException(
    #         status_code=401, 
    #         detail="Invalid username or password"
    #     )
    return current_user

async def get_base_deps(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Delayed import to avoid circular import
    from engine.modules.auth.models.user import User
    """Inject common dependencies with type safety (reusable across domains)."""
    return BaseDeps(
        db=db,
        current_user=current_user        
    )