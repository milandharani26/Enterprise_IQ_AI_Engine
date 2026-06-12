from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from engine.shared.db.base_class import Base

class Assistant(Base):
    __tablename__ = "assistant"

    assistant_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assistant_name = Column(String(255), nullable=False, unique=True)
    assistant_code = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False, default='simple_reactive')
    description = Column(String(1000), nullable=True)
    category = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='enabled')
    guardrails = Column(JSONB(astext_type=Text()), nullable=True)
    tools = Column(JSONB(astext_type=Text()), nullable=True)
    prompt_library = Column(Boolean, default=False, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('enabled', 'disabled')", name='check_assistant_status'),
    )
