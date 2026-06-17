"""Pydantic schemas for Google Drive documents management."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from engine.shared.schemas.common import SuccessDataResponse, SuccessListResponse, SuccessResponse


class DriveDocumentIngestRequest(BaseModel):
    drive_file_id: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=512)
    web_view_link: Optional[str] = Field(None, max_length=2048)
    web_content_link: Optional[str] = Field(None, max_length=2048)
    mime_type: Optional[str] = Field(None, max_length=100)
    owner_email: Optional[str] = Field(None, max_length=255)
    drive_folder_id: Optional[str] = Field(None, max_length=255)
    file_size_bytes: Optional[int] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None)
    last_modified_in_drive: Optional[datetime] = Field(None)


class DriveDocumentUpdateMetadataRequest(BaseModel):
    status: Optional[str] = Field(None, pattern="^(draft|processing|indexed|failed)$")
    processing_error: Optional[str] = None
    chunk_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    version: Optional[int] = None


class DriveDocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    drive_file_id: str
    drive_folder_id: Optional[str] = None
    owner_email: Optional[str] = None
    title: Optional[str] = None
    web_view_link: Optional[str] = None
    web_content_link: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    processing_error: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    chunk_count: int
    version: int
    last_modified_in_drive: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DriveDocumentIngestData(BaseModel):
    doc_id: UUID
    drive_file_id: str
    status: str
    message: str
    task_id: Optional[str] = None
    chunk_count: Optional[int] = None
    processing_error: Optional[str] = None


class DriveDocumentIngestResponse(SuccessDataResponse[DriveDocumentIngestData]):
    pass


class DriveDocumentDataResponse(SuccessDataResponse[DriveDocumentResponse]):
    pass


class DriveDocumentListResponse(SuccessListResponse[DriveDocumentResponse]):
    pass


class DriveDocumentSimpleResponse(SuccessResponse):
    pass
