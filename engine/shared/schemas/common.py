from datetime import datetime, timezone
import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationInfo(BaseModel):
    total: int
    offset: int
    limit: int
    total_pages: int
    has_more: bool


class MetaInfo(BaseModel):
    pagination: PaginationInfo


class SuccessResponse(BaseModel):
    success: bool = True
    status_code: int = 200
    message: str = "Request processed successfully"


class SuccessDataResponse(SuccessResponse, Generic[T]):
    data: T


class SuccessListResponse(BaseModel, Generic[T]):
    success: bool = True
    status_code: int = 200
    message: str = "List retrieved successfully"
    data: List[T]
    meta: MetaInfo

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        offset: int,
        limit: int,
        status_code: int = 200,
        message: str = "List retrieved successfully",
    ):
        total_pages = math.ceil(total / limit) if limit > 0 else 0
        has_more = offset + limit < total
        return cls(
            status_code=status_code,
            message=message,
            data=items,
            meta=MetaInfo(
                pagination=PaginationInfo(
                    total=total,
                    offset=offset,
                    limit=limit,
                    total_pages=total_pages,
                    has_more=has_more,
                )
            ),
        )


class ErrorResponse(BaseModel):
    success: bool = False
    status_code: int
    error_code: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
