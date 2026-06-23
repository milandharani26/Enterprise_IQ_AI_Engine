from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class CredentialBase(BaseModel):
    name: str = Field(..., max_length=255)
    provider: str = Field(..., max_length=100)
    status: str = Field("Active", max_length=50)


class CredentialCreate(CredentialBase):
    organization_id: UUID
    auth_data: Dict[str, Any]


class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    auth_data: Optional[Dict[str, Any]] = None


class CredentialResponse(CredentialBase):
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CredentialTestRequest(BaseModel):
    provider: str
    auth_data: Dict[str, Any]


class CredentialTestResponse(BaseModel):
    success: bool
    message: Optional[str] = None


class OAuthGenerateUrlRequest(BaseModel):
    name: str
    organization_id: UUID
    client_id: str
    client_secret: str
    redirect_uri: str


class OAuthGenerateUrlResponse(BaseModel):
    auth_url: str
    state: str


class OAuthExchangeRequest(BaseModel):
    code: str
    state: str
