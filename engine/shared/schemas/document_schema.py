"""Pydantic schemas for knowledge management (documents and chunks)."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from engine.shared.schemas.common import SuccessDataResponse, SuccessListResponse, SuccessResponse


class DocumentIngestRequest(BaseModel):
    reference_id: UUID = Field(
        ...,
        description="Client-supplied UUID; becomes the document id and deduplication key",
    )
    source_url: str = Field(..., min_length=1, max_length=2048)
    title: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(None)

    @field_validator("reference_id", mode="before")
    @classmethod
    def parse_reference_id_uuid(cls, v) -> UUID:
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("reference_id must not be empty")
            return UUID(stripped)
        raise ValueError("reference_id must be a UUID")

    @field_validator("title", mode="before")
    @classmethod
    def strip_and_require_nonempty_title(cls, v: str) -> str:
        stripped = v.strip() if isinstance(v, str) else v
        if not stripped:
            raise ValueError("Field must not be empty or whitespace only")
        return stripped

    @field_validator("source_url", mode="before")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        stripped = v.strip() if isinstance(v, str) else v
        if not stripped:
            raise ValueError("source_url must not be empty")
        allowed_prefixes = ("s3://", "gs://", "http://", "https://", "upload://", "file://")
        if not any(stripped.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(
                "source_url must start with s3://, gs://, http://, https://, upload://, or file://"
            )
        return stripped

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("metadata must have at most 10 keys")
        for key, val in v.items():
            if isinstance(val, str) and len(val) > 500:
                raise ValueError(f"metadata value for key '{key}' exceeds 500 characters")
        return v


class DocumentUpdateMetadataRequest(BaseModel):
    status: Optional[str] = Field(None, pattern="^(draft|processing|indexed|failed)$")
    processing_error: Optional[str] = None
    chunk_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    version: Optional[int] = None


class DocumentResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    reference_id: str
    title: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    processing_error: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    chunk_count: int
    version: int
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class DocumentIngestData(BaseModel):
    doc_id: UUID
    reference_id: str
    status: str
    message: str
    task_id: Optional[str] = None
    chunk_count: Optional[int] = None
    processing_error: Optional[str] = None


class DocumentIngestResponse(SuccessDataResponse[DocumentIngestData]):
    pass


class DocumentDataResponse(SuccessDataResponse[DocumentResponse]):
    pass


class DocumentListResponse(SuccessListResponse[DocumentResponse]):
    pass


class DocumentSimpleResponse(SuccessResponse):
    pass


class DocumentSearchRequest(BaseModel):
    organization_ids: List[UUID] = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class DocumentSearchChunk(BaseModel):
    text: str
    title: str
    reference_id: str
    similarity: Optional[float] = None
    vector_score: Optional[float] = None
    text_score: Optional[float] = None


class DocumentSearchResponse(SuccessDataResponse[List[DocumentSearchChunk]]):
    pass
