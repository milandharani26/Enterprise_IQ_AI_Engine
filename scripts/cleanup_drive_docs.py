"""
Clean ALL drive_documents before server restart.
Run this AFTER stopping python main.py and BEFORE restarting it.
"""
import asyncio
from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.drive_document_model import DriveDocument
from sqlalchemy import select, delete, text


async def main():
    async with AsyncSessionLocal() as db:
        # Show current state
        result = await db.execute(select(DriveDocument.id, DriveDocument.title, DriveDocument.status))
        rows = result.all()
        print(f"\nFound {len(rows)} drive_documents:")
        for r in rows:
            print(f"  [{r[2]}] {r[1]}")

        # Wipe both tables cleanly (chunks cascade from documents)
        await db.execute(text("DELETE FROM knowledge.drive_document_chunks"))
        await db.execute(text("DELETE FROM knowledge.drive_documents"))
        await db.commit()

        print(f"\n✅ Deleted all {len(rows)} drive_document records (chunks cascade-deleted).")
        print("Now restart the server: python main.py")
        print("The background worker will re-sync from Google Drive with the fixed de-duplication logic.")


asyncio.run(main())
