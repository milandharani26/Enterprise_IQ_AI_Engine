import asyncio
from engine.shared.db.session import async_session
from engine.modules.assistant.assistant_models import Assistant
from engine.modules.conversation.conversation_models import Conversation
from sqlalchemy.future import select

async def main():
    async with async_session() as db:
        print("--- ASSISTANTS ---")
        result = await db.execute(select(Assistant))
        assistants = result.scalars().all()
        for a in assistants:
            print(f"ID: {a.assistant_id}, Org: {a.organization_id}, Status: {a.status}, Name: {a.assistant_name}")
            
        print("\n--- CONVERSATIONS ---")
        result = await db.execute(select(Conversation))
        conversations = result.scalars().all()
        for c in conversations:
            print(f"Conv ID: {c.id}, Agent ID: {c.agent_id}, Org: {c.organization_id}")

if __name__ == "__main__":
    asyncio.run(main())
