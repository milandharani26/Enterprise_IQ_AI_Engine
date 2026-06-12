from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class ServiceAccountCreate(BaseModel):
    name: str
    note: Optional[str] = None
    expire_at: datetime
    created_by: Optional[UUID] = None

class ServiceAccountResponse(BaseModel):
    id: UUID
    name: str
    expire_at: datetime
    is_active: bool
    token: Optional[str] = None
    created_by: Optional[UUID] = None

class ServiceAccountRegenerate(BaseModel):
    expire_at: Optional[datetime] = None
