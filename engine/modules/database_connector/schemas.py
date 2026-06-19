from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

# --------------------------
# Database Connection
# --------------------------

class DatabaseConnectionBase(BaseModel):
    name: str = Field(..., description="Human-readable connection name")
    database_type: str = Field(..., description="Type of database (e.g., postgresql, mysql)")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database_name: str = Field(..., description="Name of the database")
    schema_name: Optional[str] = Field(None, description="Schema name (e.g., public)")
    username: str = Field(..., description="Database username")

class DatabaseConnectionCreate(DatabaseConnectionBase):
    password: str = Field(..., description="Database password")

class DatabaseConnectionUpdate(BaseModel):
    name: Optional[str] = None
    database_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    schema_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class DatabaseConnectionResponse(DatabaseConnectionBase):
    id: UUID
    organization_id: UUID
    is_active: bool
    last_synced_at: Optional[datetime] = None
    sync_status: Optional[str] = None
    sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --------------------------
# Connection Testing
# --------------------------

class DatabaseConnectionTestRequest(DatabaseConnectionCreate):
    pass

class DatabaseConnectionTestResponse(BaseModel):
    success: bool
    message: str

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
