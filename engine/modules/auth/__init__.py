"""
auth module
===========
Public surface of the auth module. Import everything from here.

Usage::

    from engine.modules.auth import User, AuthService, AuthResponse, LoginRequest, router
"""

from engine.modules.auth.auth_models import User
from engine.modules.auth.auth_schemas import LoginRequest, AuthResponse
from engine.modules.auth.auth_service import AuthService
from engine.modules.auth.auth_routes import router

__all__ = [
    # Model
    "User",
    # Schemas
    "LoginRequest",
    "AuthResponse",
    # Service
    "AuthService",
    # Router
    "router",
]
