"""SQLAlchemy models for connectors mapping to credentials."""
from sqlalchemy import Column, String, DateTime, text, func, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from engine.shared.db.base_class import Base


class Connector(Base):
    __tablename__ = "connectors"
    __table_args__ = (
        UniqueConstraint("organization_id", "connector_id", name="uq_connectors_org_connector"),
        {"schema": "public"}
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    connector_id = Column(String(100), nullable=False)  # e.g., 'google_drive'
    name = Column(String(255), nullable=False)
    provider = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, server_default="disabled")  # 'enabled' / 'disabled'
    credential_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.credentials.id", ondelete="SET NULL"),
        nullable=True,
    )
    sync_status = Column(String(50), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_error = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
