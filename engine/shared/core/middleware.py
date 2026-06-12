from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from engine.shared.core.deps import get_db
from engine.shared.core.security import JWTService
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engine.modules.auth.auth_models import User


class AuthMiddleware:
    """
    Central authentication middleware class.

    Bundles all auth dependency logic into a single class:
      - ``get_current_user``       — validates access_token cookie → returns User
      - ``require_admin``          — get_current_user + admin account_type check
      - ``require_service_account``— validates X-API-Key header for service accounts

    Usage with FastAPI Depends::

        auth = AuthMiddleware()

        async def endpoint(user: User = Depends(auth.get_current_user)): ...
        async def admin_ep(user: User = Depends(auth.require_admin)): ...
        async def svc_ep(user: User = Depends(auth.require_service_account)): ...
    """

    def __init__(self) -> None:
        self._jwt = JWTService()

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    @staticmethod
    def _auth_error(message: str = "Unauthorized") -> HTTPException:
        """Build a standardised 401 HTTPException."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "message": message},
        )

    # ------------------------------------------------------------------
    # get_current_user
    # ------------------------------------------------------------------

    async def get_current_user(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> "User":
        """
        Validate the ``access_token`` cookie and return the matching User.
        Raises 401 if the token is missing/invalid, 403 if the account is disabled.
        """
        from engine.modules.auth.auth_models import User
        token = request.cookies.get("access_token")
        if not token:
            raise self._auth_error("Missing access token cookie")

        payload = self._jwt.verify_token(token)
        if not payload:
            raise self._auth_error("Invalid or expired token")

        user_id = payload.get("user_id")
        if not user_id:
            raise self._auth_error("Invalid token payload")

        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise self._auth_error("User not found")

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Account disabled"},
            )

        return user

    # ------------------------------------------------------------------
    # require_admin
    # ------------------------------------------------------------------

    async def require_admin(
        self,
        request: Request,
        db: AsyncSession = Depends(get_db),
    ) -> "User":
        """
        Resolve the current user (via ``get_current_user``) and assert
        that ``account_type == 'admin'``. Raises 403 otherwise.
        """
        current_user = await self.get_current_user(request, db)
        if current_user.account_type != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"success": False, "message": "Admin privileges required"},
            )
        return current_user

    # ------------------------------------------------------------------
    # require_service_account
    # ------------------------------------------------------------------

    async def require_service_account(
        self,
        x_api_key: str = Header(None, alias="X-API-Key"),
        db: AsyncSession = Depends(get_db),
    ) -> "User":
        """
        Validate the ``X-API-Key`` header as a JWT, verify the user is an
        active service account, and confirm the token matches the stored
        ``service_token`` (revocation check).
        """
        from engine.modules.auth.auth_models import User
        if not x_api_key:
            raise self._auth_error("Missing X-API-Key header")

        payload = self._jwt.verify_token(x_api_key)
        if not payload:
            raise self._auth_error("Invalid or expired service token")

        user_id = payload.get("user_id")
        if not user_id:
            raise self._auth_error("Invalid token payload")

        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise self._auth_error("Invalid service account")

        if user.account_type != "service_account":
            raise self._auth_error("Not a service account")

        if user.service_token != x_api_key:
            raise self._auth_error("Token revoked or mismatch")

        return user


# ---------------------------------------------------------------------------
# Module-level singleton + named aliases
# All existing ``Depends(require_admin)`` / ``Depends(get_current_user)``
# call-sites continue to work without any import changes.
# ---------------------------------------------------------------------------

_auth = AuthMiddleware()

get_current_user      = _auth.get_current_user
require_admin         = _auth.require_admin
require_service_account = _auth.require_service_account
