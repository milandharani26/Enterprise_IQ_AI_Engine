# modules/conversation/conversation_models.py
import enum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from engine.shared.db.base_class import Base

class MessageRole(str, enum.Enum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    SYSTEM = "SYSTEM"

class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    agent_id = Column(UUID(as_uuid=True), nullable=True)  # Links to which AI agent is running
    title = Column(String(255), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # One relationship to handle all message records
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_admin_conversations_user_id', 'user_id'),
        Index('idx_admin_conversations_organization_id', 'organization_id'),
    )


class ConversationMessage(Base):
    __tablename__ = 'conversation_messages'

    id = Column(UUID(as_uuid=True), primary_key=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    
    # 👈 This distinguishes if the chat came from USER or ASSISTANT
    role = Column(Enum(MessageRole), nullable=False) 
    
    content = Column(Text, nullable=False)
    metadata_json = Column(JSONB, name="metadata", nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index('idx_admin_messages_conversation_id', 'conversation_id'),
        Index('idx_admin_messages_organization_id', 'organization_id'),
    )