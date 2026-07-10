"""
conversation module
===================
Public surface of the conversation module. Import everything from here.
"""

from engine.modules.conversation.conversation_routes import router as conversation_router
from engine.modules.conversation.conversation_models import Conversation, ConversationMessage, MessageRole
from engine.modules.conversation.conversation_schemas import (
    MessageBaseSchema,
    MessageCreateSchema,
    MessageResponseSchema,
    ConversationBaseSchema,
    ConversationCreateSchema,
    ConversationResponseSchema,
    ConversationDetailResponseSchema,
    NewUserMessagePayloadSchema
)
from engine.modules.conversation.conversation_service import ConversationService

__all__ = [
    "conversation_router",
    "Conversation",
    "ConversationMessage",
    "MessageRole",
    "MessageBaseSchema",
    "MessageCreateSchema",
    "MessageResponseSchema",
    "ConversationBaseSchema",
    "ConversationCreateSchema",
    "ConversationResponseSchema",
    "ConversationDetailResponseSchema",
    "NewUserMessagePayloadSchema",
    "ConversationService"
]