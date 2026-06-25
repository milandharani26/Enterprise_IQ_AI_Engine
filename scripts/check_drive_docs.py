"""Quick diagnostic: list all drive_documents in the DB."""
import asyncio
from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.drive_document_model import DriveDocument
from sqlalchemy import select


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                DriveDocument.id,
                DriveDocument.title,
                DriveDocument.status,
                DriveDocument.workspace_id,
                DriveDocument.created_at,
            )
        )
        rows = result.all()
        print(f"\nTotal drive_documents in DB: {len(rows)}\n")
        for r in rows:
            title = (r[1] or "(no title)")[:50]
            print(f"  id={r[0]} | status={r[2]} | workspace={r[3]} | created={r[4]} | title={title}")


asyncio.run(main())
