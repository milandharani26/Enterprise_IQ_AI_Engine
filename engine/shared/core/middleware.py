from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from engine.shared.core.deps import get_db
from engine.shared.core.security import JWTService
from engine.modules.auth.models.user import User

jwt_service = JWTService()

def _auth_error(message: str = "Unauthorized"):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"success": False, "message": message})

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise _auth_error("Missing access token cookie")
        
    payload = jwt_service.verify_token(token)
    if not payload:
        raise _auth_error("Invalid or expired token")

    user_id = payload.get("user_id")
    if not user_id:
        raise _auth_error("Invalid token payload")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise _auth_error("User not found")
        
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"success": False, "message": "Account disabled"})

    return user

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.account_type != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"success": False, "message": "Admin privileges required"})
    return current_user

async def require_service_account(
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not x_api_key:
        raise _auth_error("Missing X-API-Key header")
        
    payload = jwt_service.verify_token(x_api_key)
    if not payload:
        raise _auth_error("Invalid or expired service token")

    user_id = payload.get("user_id")
    if not user_id:
        raise _auth_error("Invalid token payload")

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise _auth_error("Invalid service account")

    if user.account_type != "service_account":
        raise _auth_error("Not a service account")

    if user.service_token != x_api_key:
        raise _auth_error("Token revoked or mismatch")

    return user
