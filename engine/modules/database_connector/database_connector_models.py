"""
Database Connector Module Models
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    
    String,
    Text,
    BigInteger,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from engine.shared.db.base_class import Base




class SchemaTable(Base):
    __tablename__ = "schema_tables"
    __table_args__ = {"schema": "connectors"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("public.connectors.id", ondelete="CASCADE"), nullable=False)
    schema_name = Column(String(255), nullable=True)
    table_name = Column(String(255), nullable=False)
    table_description = Column(Text, nullable=True)
    row_count_estimate = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship for eager loading columns
    columns = relationship("SchemaColumn", foreign_keys="SchemaColumn.table_id", lazy="select")


class SchemaColumn(Base):
    __tablename__ = "schema_columns"
    __table_args__ = {"schema": "connectors"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    table_id = Column(UUID(as_uuid=True), ForeignKey("connectors.schema_tables.id", ondelete="CASCADE"), nullable=False)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(100), nullable=False)
    is_nullable = Column(Boolean, nullable=False)
    is_primary_key = Column(Boolean, server_default="false", nullable=False)
    default_value = Column(Text, nullable=True)
    column_description = Column(Text, nullable=True)
    ordinal_position = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class SchemaRelationship(Base):
    __tablename__ = "schema_relationships"
    __table_args__ = {"schema": "connectors"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("public.connectors.id", ondelete="CASCADE"), nullable=False)
    source_table = Column(String(512), nullable=False)
    source_column = Column(String(255), nullable=False)
    target_table = Column(String(512), nullable=False)
    target_column = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class SchemaEmbedding(Base):
    __tablename__ = "schema_embeddings"
    __table_args__ = {"schema": "connectors"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("public.connectors.id", ondelete="CASCADE"), nullable=False)
    object_type = Column(String(50), nullable=False)
    object_name = Column(String(512), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class SqlQueryLog(Base):
    __tablename__ = "sql_query_logs"
    __table_args__ = {"schema": "connectors"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    connector_id = Column(UUID(as_uuid=True), ForeignKey("public.connectors.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    question = Column(Text, nullable=False)
    generated_sql = Column(Text, nullable=True)
    selected_database = Column(String(255), nullable=True)
    retrieved_tables = Column(JSONB, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
