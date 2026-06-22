import asyncio
import json
from sqlalchemy import select
from engine.shared.db.session import AsyncSessionLocal
from engine.modules.assistant.assistant_models import Assistant

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Assistant))
        assistants = res.scalars().all()
        for a in assistants:
            print(f"Assistant {a.assistant_id}: tools={json.dumps(a.tools)}")

asyncio.run(main())
