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

    @property
    def display_info(self):
        info = {}
        if self.auth_data:
            if "email" in self.auth_data:
                info["email"] = self.auth_data["email"]
            if "host" in self.auth_data:
                info["host"] = self.auth_data["host"]
            if "username" in self.auth_data:
                info["username"] = self.auth_data["username"]
            if "api_key" in self.auth_data:
                from engine.shared.security.encryption import decrypt_value
                encrypted_key = self.auth_data.get("api_key") or ""
                try:
                    decrypted_key = decrypt_value(encrypted_key)
                    if decrypted_key:
                        if len(decrypted_key) > 10:
                            info["masked_key"] = f"{decrypted_key[:7]}...{decrypted_key[-4:]}"
                        else:
                            info["masked_key"] = "••••••••••••"
                    else:
                        info["masked_key"] = "••••••••••••"
                except Exception:
                    info["masked_key"] = "••••••••••••"
        return info
