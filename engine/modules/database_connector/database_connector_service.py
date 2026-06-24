from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from engine.modules.database_connector.database_connector_models import SchemaTable, SchemaColumn
from engine.shared.models.connector_model import Connector


class DatabaseConnectionService:
    @staticmethod
    async def get_connector(
        db: AsyncSession, connection_id: UUID, org_id: UUID
    ) -> Optional[Connector]:
        stmt = select(Connector).where(
            Connector.id == connection_id,
            Connector.organization_id == org_id
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def get_schema_tables(
        db: AsyncSession, connection_id: UUID, org_id: UUID
    ) -> List[dict]:
        # Validate connection ownership
        db_obj = await DatabaseConnectionService.get_connector(db, connection_id, org_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Database connection not found")

        from sqlalchemy.orm import selectinload

        # Fetch tables with columns in a single query (eliminates N+1)
        stmt = select(SchemaTable).where(
            SchemaTable.connector_id == connection_id,
            SchemaTable.organization_id == org_id
        ).options(selectinload(SchemaTable.columns))
        result = await db.execute(stmt)
        tables = result.scalars().all()

        response = []
        for t in tables:
            response.append({
                "table_name": t.table_name,
                "schema_name": t.schema_name,
                "table_description": t.table_description,
                "row_count_estimate": t.row_count_estimate,
                "columns": [
                    {
                        "column_name": c.column_name,
                        "data_type": c.data_type,
                        "is_nullable": c.is_nullable,
                        "is_primary_key": c.is_primary_key,
                        "column_description": c.column_description,
                    }
                    for c in t.columns
                ]
            })

        return response

