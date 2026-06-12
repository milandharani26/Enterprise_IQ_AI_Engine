from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class ServiceAccountCreate(BaseModel):
    name: str
    note: Optional[str] = None
    expire_at: datetime

class ServiceAccountResponse(BaseModel):
    id: UUID
    name: str
    note: Optional[str] = None
    expire_at: datetime
    is_active: bool
    token: Optional[str] = None

class ServiceAccountRegenerate(BaseModel):
    expire_at: Optional[datetime] = None
