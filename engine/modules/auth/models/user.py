from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from engine.shared.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(Text, nullable=True)
    user_name = Column(String(100), nullable=False)
    account_type = Column(String(20), nullable=False)
    refresh_token = Column(Text, nullable=True)
    service_token = Column(Text, nullable=True)
    is_active = Column(Boolean, server_default='true', nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
