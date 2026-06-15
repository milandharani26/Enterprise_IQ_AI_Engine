# modules/organization/organization_models.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from engine.shared.db.base_class import Base
class Organization(Base):
    __tablename__ = 'organizations'

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)  # 👈 Add this line
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)