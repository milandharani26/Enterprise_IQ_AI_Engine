from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from engine.modules.database_connector.models import DatabaseConnection, SchemaTable, SchemaColumn
from engine.modules.database_connector.schemas import DatabaseConnectionCreate, DatabaseConnectionUpdate


class DatabaseConnectionService:
    @staticmethod
    async def create_connection(
        db: AsyncSession, obj_in: DatabaseConnectionCreate, org_id: UUID, background_tasks = None
    ) -> DatabaseConnection:
        # Check for existing connection with same name
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.organization_id == org_id,
            DatabaseConnection.name == obj_in.name,
            DatabaseConnection.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Database connection with this name already exists")

        db_obj = DatabaseConnection(
            organization_id=org_id,
            name=obj_in.name,
            database_type=obj_in.database_type,
            host=obj_in.host,
            port=obj_in.port,
            database_name=obj_in.database_name,
            schema_name=obj_in.schema_name,
            username=obj_in.username,
            password=obj_in.password,  # Stored in plain text initially as requested
            sync_status="pending"
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Trigger immediate background schema sync using schedule function
        from engine.modules.database_connector.tasks import schedule_sync_schema
        schedule_sync_schema(db_obj.id, org_id, background_tasks=background_tasks)

        return db_obj

    @staticmethod
    async def get_connection(
        db: AsyncSession, connection_id: UUID, org_id: UUID
    ) -> Optional[DatabaseConnection]:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.id == connection_id,
            DatabaseConnection.organization_id == org_id,
            DatabaseConnection.deleted_at.is_(None)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    @staticmethod
    async def list_connections(
        db: AsyncSession, org_id: UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List[DatabaseConnection], int]:
        stmt = select(DatabaseConnection).where(
            DatabaseConnection.organization_id == org_id,
            DatabaseConnection.deleted_at.is_(None)
        )
        
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(total_stmt)
        total = total_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        items = result.scalars().all()
        
        return list(items), total

    @staticmethod
    async def update_connection(
        db: AsyncSession, connection_id: UUID, obj_in: DatabaseConnectionUpdate, org_id: UUID
    ) -> DatabaseConnection:
        db_obj = await DatabaseConnectionService.get_connection(db, connection_id, org_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Database connection not found")

        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete_connection(
        db: AsyncSession, connection_id: UUID, org_id: UUID
    ) -> bool:
        db_obj = await DatabaseConnectionService.get_connection(db, connection_id, org_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Database connection not found")

        # Soft delete
        db_obj.deleted_at = func.now()
        await db.commit()
        return True

    @staticmethod
    async def get_schema_tables(
        db: AsyncSession, connection_id: UUID, org_id: UUID
    ) -> List[dict]:
        # Validate connection ownership
        db_obj = await DatabaseConnectionService.get_connection(db, connection_id, org_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Database connection not found")

        # Fetch tables
        stmt = select(SchemaTable).where(
            SchemaTable.database_connection_id == connection_id,
            SchemaTable.organization_id == org_id
        )
        result = await db.execute(stmt)
        tables = result.scalars().all()

        if not tables:
            return []

        table_ids = [t.id for t in tables]

        # Fetch columns for all these tables
        stmt_cols = select(SchemaColumn).where(SchemaColumn.table_id.in_(table_ids))
        result_cols = await db.execute(stmt_cols)
        columns = result_cols.scalars().all()

        col_map = {}
        for c in columns:
            col_map.setdefault(c.table_id, []).append(c)

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
                    for c in col_map.get(t.id, [])
                ]
            })

        return response
