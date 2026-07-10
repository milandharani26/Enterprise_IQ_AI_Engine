from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

# --------------------------
# Sync Status & Schema
# --------------------------

class SyncStatusResponse(BaseModel):
    sync_status: Optional[str]
    last_synced_at: Optional[datetime]
    table_count: int

class SchemaColumnResponse(BaseModel):
    column_name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    column_description: Optional[str]
    
    class Config:
        orm_mode = True

class SchemaTableResponse(BaseModel):
    table_name: str
    schema_name: Optional[str]
    table_description: Optional[str]
    row_count_estimate: Optional[int]
    columns: List[SchemaColumnResponse] = []
    
    class Config:
        orm_mode = True

# --------------------------
# Metadata Enrichment (detailed, with IDs and user-override flags)
# --------------------------

class SchemaColumnDetailResponse(BaseModel):
    id: UUID
    column_name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    default_value: Optional[str]
    column_description: Optional[str]
    # True = user manually set this; sync will not overwrite
    user_column_description: bool
    ordinal_position: int
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True

class SchemaTableDetailResponse(BaseModel):
    id: UUID
    table_name: str
    schema_name: Optional[str]
    table_description: Optional[str]
    # True = user manually set this; sync will not overwrite
    user_table_description: bool
    row_count_estimate: Optional[int]
    updated_at: Optional[datetime]
    columns: List[SchemaColumnDetailResponse] = []

    class Config:
        orm_mode = True

# --------------------------
# Metadata Enrichment — Request Bodies
# --------------------------

class UpdateTableDescriptionRequest(BaseModel):
    description: Optional[str] = Field(
        None,
        description="New description text. Pass null/None to clear the manual override."
    )

class UpdateColumnDescriptionRequest(BaseModel):
    description: Optional[str] = Field(
        None,
        description="New description text. Pass null/None to clear the manual override."
    )

# --------------------------
# Query Logs
# --------------------------

class SqlQueryLogResponse(BaseModel):
    id: UUID
    question: str
    generated_sql: Optional[str]
    selected_database: Optional[str]
    retrieved_tables: Optional[List[str]]
    execution_time_ms: Optional[int]
    row_count: Optional[int]
    success: bool
    error_message: Optional[str]
    created_at: datetime
    
    class Config:
        orm_mode = True
