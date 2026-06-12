from fastapi import APIRouter, Depends, Response, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from engine.shared.core.deps import get_db
from engine.modules.auth.schemas.auth_schema import LoginRequest, AuthResponse
from engine.modules.auth.services.auth_service import AuthService
from engine.shared.core.middleware import require_admin
from engine.modules.auth.models.user import User
from engine.shared.core.security import JWTService

router = APIRouter(prefix="/auth", tags=["auth"])
jwt_service = JWTService()

@router.post("/login", response_model=AuthResponse)
async def login(
    request_data: LoginRequest, 
    response: Response, 
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    access_token, refresh_token = await auth_service.authenticate_user(request_data)
    
    # Attach cookies to response
    jwt_service.set_auth_cookies(response, access_token, refresh_token)
    return AuthResponse(success=True, message="Logged in successfully")

@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response, 
    db: AsyncSession = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
        
    auth_service = AuthService(db)
    new_access_token, new_refresh_token = await auth_service.refresh_token(refresh_token)
    
    # Attach new cookies to response
    jwt_service.set_auth_cookies(response, new_access_token, new_refresh_token)
    return AuthResponse(success=True, message="Token refreshed successfully")

@router.post("/logout", response_model=AuthResponse)
async def logout(
    response: Response,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    await auth_service.logout_user(current_user)
    
    # Clear cookies
    jwt_service.clear_auth_cookies(response)
    return AuthResponse(success=True, message="Logged out successfully")
