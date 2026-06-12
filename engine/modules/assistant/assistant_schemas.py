from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class AssistantBase(BaseModel):
    assistant_name: str = Field(..., max_length=255)
    assistant_code: str = Field(..., max_length=100)
    type: str = Field(default="simple_reactive", max_length=50)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: Optional[str] = Field(default=None, max_length=100)
    system_prompt: Optional[str] = None
    status: str = Field(default="enabled", max_length=50)
    guardrails: Optional[List[Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    prompt_library: Optional[bool] = False

class AssistantCreate(AssistantBase):
    pass

class AssistantUpdate(BaseModel):
    assistant_name: Optional[str] = Field(None, max_length=255)
    assistant_code: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=100)
    system_prompt: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    guardrails: Optional[List[Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    prompt_library: Optional[bool] = None

class AssistantStatusUpdate(BaseModel):
    status: str = Field(..., max_length=50)

class AssistantResponse(AssistantBase):
    assistant_id: UUID
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: Optional[UUID] = None

    class Config:
        from_attributes = True
