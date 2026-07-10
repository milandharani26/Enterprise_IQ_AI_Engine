"""
assistant module
================
Public surface of the assistant module. Import everything from here.

Usage::

    from engine.modules.assistant import (
        Assistant,
        AssistantService,
        AssistantCreate, AssistantUpdate, AssistantResponse, AssistantStatusUpdate,
        router,
    )
"""

from engine.modules.assistant.assistant_models import Assistant
from engine.modules.assistant.assistant_schemas import (
    AssistantBase,
    AssistantCreate,
    AssistantUpdate,
    AssistantStatusUpdate,
    AssistantResponse,
)
from engine.modules.assistant.assistant_service import AssistantService
from engine.modules.assistant.assistant_routes import router

__all__ = [
    # Model
    "Assistant",
    # Schemas
    "AssistantBase",
    "AssistantCreate",
    "AssistantUpdate",
    "AssistantStatusUpdate",
    "AssistantResponse",
    # Service
    "AssistantService",
    # Router
    "router",
]
