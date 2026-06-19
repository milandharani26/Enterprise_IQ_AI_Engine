from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class ConnectorBase(BaseModel):
    connector_id: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    provider: str = Field(..., max_length=100)
    status: str = Field("disabled", max_length=50)


class ConnectorCreate(ConnectorBase):
    organization_id: UUID
    credential_id: Optional[UUID] = None


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    credential_id: Optional[UUID] = None


class ConnectorResponse(ConnectorBase):
    id: UUID
    organization_id: UUID
    credential_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
