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

    @staticmethod
    async def get_schema_tables_detailed(
        db: AsyncSession, connection_id: UUID, org_id: UUID
    ) -> List[dict]:
        """
        Returns tables with full metadata detail for the enrichment dashboard:
        includes row IDs, user-override flags, updated_at timestamps, and
        full column data so the UI can render inline editors.
        """
        db_obj = await DatabaseConnectionService.get_connector(db, connection_id, org_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Database connection not found")

        from sqlalchemy.orm import selectinload

        stmt = (
            select(SchemaTable)
            .where(
                SchemaTable.connector_id == connection_id,
                SchemaTable.organization_id == org_id
            )
            .options(selectinload(SchemaTable.columns))
            .order_by(SchemaTable.table_name)
        )
        result = await db.execute(stmt)
        tables = result.scalars().all()

        response = []
        for t in tables:
            cols = sorted(t.columns, key=lambda c: c.ordinal_position)
            response.append({
                "id": str(t.id),
                "table_name": t.table_name,
                "schema_name": t.schema_name,
                "table_description": t.table_description,
                "user_table_description": t.user_table_description,
                "row_count_estimate": t.row_count_estimate,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                "columns": [
                    {
                        "id": str(c.id),
                        "column_name": c.column_name,
                        "data_type": c.data_type,
                        "is_nullable": c.is_nullable,
                        "is_primary_key": c.is_primary_key,
                        "default_value": c.default_value,
                        "column_description": c.column_description,
                        "user_column_description": c.user_column_description,
                        "ordinal_position": c.ordinal_position,
                        "updated_at": c.updated_at.isoformat() if getattr(c, "updated_at", None) else None,
                    }
                    for c in cols
                ],
            })

        return response

    @staticmethod
    async def update_table_description(
        db: AsyncSession, table_id: UUID, org_id: UUID, description: Optional[str]
    ) -> SchemaTable:
        """
        Manually set (or clear) a table's description.
        - Providing a non-None string → sets description, marks user_table_description=True
          so future syncs will NOT overwrite it.
        - Passing None → clears the description and resets the sentinel to False,
          allowing the next sync to repopulate it from the source DB.
        """
        stmt = (
            select(SchemaTable)
            .join(Connector, SchemaTable.connector_id == Connector.id)
            .where(
                SchemaTable.id == table_id,
                Connector.organization_id == org_id,
            )
        )
        result = await db.execute(stmt)
        table = result.scalars().first()

        if not table:
            raise HTTPException(status_code=404, detail="Schema table not found")

        table.table_description = description
        # If user clears the description, release the lock so sync can fill it back in
        table.user_table_description = description is not None and description.strip() != ""

        await db.commit()
        await db.refresh(table)
        return table

    @staticmethod
    async def update_column_description(
        db: AsyncSession, column_id: UUID, org_id: UUID, description: Optional[str]
    ) -> SchemaColumn:
        """
        Manually set (or clear) a column's description.
        - Providing a non-None string → sets description, marks user_column_description=True
          so future syncs will NOT overwrite it.
        - Passing None → clears the description and resets the sentinel to False,
          allowing the next sync to repopulate it from the source DB.
        """
        stmt = (
            select(SchemaColumn)
            .join(SchemaTable, SchemaColumn.table_id == SchemaTable.id)
            .join(Connector, SchemaTable.connector_id == Connector.id)
            .where(
                SchemaColumn.id == column_id,
                Connector.organization_id == org_id,
            )
        )
        result = await db.execute(stmt)
        column = result.scalars().first()

        if not column:
            raise HTTPException(status_code=404, detail="Schema column not found")

        column.column_description = description
        # If user clears the description, release the lock so sync can fill it back in
        column.user_column_description = description is not None and description.strip() != ""

        await db.commit()
        await db.refresh(column)
        return column
