# modules/conversation/conversation_schemas.py
from pydantic import BaseModel
from uuid import UUID
from typing import Optional, Any, Dict, List
from datetime import datetime
from engine.modules.conversation.conversation_models import MessageRole

# --- Message Schemas ---

class MessageBaseSchema(BaseModel):
    content: str
    role: MessageRole  # Validates against USER, ASSISTANT, or SYSTEM
    metadata_json: Optional[Dict[str, Any]] = None

class MessageCreateSchema(MessageBaseSchema):
    id: Optional[UUID] = None
    conversation_id: UUID
    organization_id: UUID

class MessageResponseSchema(MessageBaseSchema):
    id: UUID
    conversation_id: UUID
    organization_id: UUID
    created_at: datetime
    metadata_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# --- Conversation Room Schemas ---

class ConversationBaseSchema(BaseModel):
    user_id: UUID
    organization_id: UUID
    agent_id: Optional[UUID] = None
    title: Optional[str] = None

class ConversationCreateSchema(ConversationBaseSchema):
    id: Optional[UUID] = None

class ConversationResponseSchema(ConversationBaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationDetailResponseSchema(ConversationResponseSchema):
    messages: List[MessageResponseSchema] = []  # Includes the whole chat history thread


# --- Frontend Interaction Payloads ---

class NewUserMessagePayloadSchema(BaseModel):
    """Payload sent by the frontend chat component when a user types a message."""
    conversation_id: UUID
    user_id: UUID
    organization_id: Optional[UUID] = None  # Optional so NestJS doesn't have to send it
    agent_id: Optional[UUID] = None
    content: str