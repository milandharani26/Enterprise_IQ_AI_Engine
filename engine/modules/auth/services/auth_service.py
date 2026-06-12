from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from engine.modules.auth.models.user import User
from engine.modules.auth.schemas.auth_schema import LoginRequest
from engine.shared.core.security import JWTService, PasswordHelper

jwt_service = JWTService()

class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(self, data: LoginRequest) -> tuple[str, str]:
        # 1. Find admin user
        query = select(User).where(User.email == data.email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        # 2. Verify password
        if not PasswordHelper.verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

        # 3. Generate access token
        access_payload = {"user_id": str(user.id), "account_type": user.account_type}
        access_token, _ = jwt_service.create_access_token(access_payload)

        # 4. Generate refresh token
        refresh_payload = {"user_id": str(user.id)}
        refresh_token = jwt_service.create_refresh_token(refresh_payload)

        # 5. Store refresh token in database
        user.refresh_token = refresh_token
        await self.db.commit()

        # 6. Return tokens
        return access_token, refresh_token

    async def refresh_token(self, refresh_token_str: str) -> tuple[str, str]:
        # 1. Validate refresh token
        payload = jwt_service.verify_token(refresh_token_str)
        if not payload or payload.get("token_type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        # 2. Verify it matches users.refresh_token
        query = select(User).where(User.id == user_id, User.refresh_token == refresh_token_str)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        # 3. Generate new access token
        access_payload = {"user_id": str(user.id), "account_type": user.account_type}
        access_token, _ = jwt_service.create_access_token(access_payload)
        
        # also rotate refresh token
        refresh_payload = {"user_id": str(user.id)}
        new_refresh_token = jwt_service.create_refresh_token(refresh_payload)
        user.refresh_token = new_refresh_token
        await self.db.commit()

        # 4. Return access token
        return access_token, new_refresh_token

    async def logout_user(self, user: User) -> None:
        # 2. Remove refresh_token from database
        user.refresh_token = None
        await self.db.commit()
