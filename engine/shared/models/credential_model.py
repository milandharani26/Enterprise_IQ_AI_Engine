"""SQLAlchemy models for integrations credentials."""
from sqlalchemy import Column, String, DateTime, text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from engine.shared.db.base_class import Base


class Credential(Base):
    __tablename__ = "credentials"
    __table_args__ = {"schema": "public"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)  # 'Google', 'PostgreSQL'
    status = Column(String(50), nullable=False, server_default="Active")
    auth_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_used_at = Column(DateTime, nullable=True)
