import logging
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case

from engine.shared.db.session import AsyncSessionLocal
from engine.shared.models.credential_model import Credential
from engine.shared.models.connector_model import Connector
from engine.shared.models.document_model import Document
from engine.modules.assistant.assistant_models import Assistant
from engine.modules.conversation.conversation_models import Conversation, ConversationMessage

router = APIRouter()
logger = logging.getLogger(__name__)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/metrics/{organization_id}")
async def get_dashboard_metrics(organization_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        # Count Assistants
        total_assistants = await db.scalar(
            select(func.count(Assistant.assistant_id))
            .where(Assistant.organization_id == organization_id)
        )

        # Count Active Connectors & check health
        connectors_query = await db.execute(
            select(Connector.status, Connector.sync_status)
            .where(Connector.organization_id == organization_id)
        )
        connectors = connectors_query.all()
        active_connectors = sum(1 for c in connectors if c.status == 'enabled')
        system_health = "Operational"
        if any(c.sync_status == 'failed' for c in connectors if c.status == 'enabled'):
            system_health = "Degraded"

        # Count Credentials
        total_credentials = await db.scalar(
            select(func.count(Credential.id))
            .where(Credential.organization_id == organization_id)
        )

        # Count Conversations and Messages
        total_conversations = await db.scalar(
            select(func.count(Conversation.id))
            .where(Conversation.organization_id == organization_id)
        )
        total_messages = await db.scalar(
            select(func.count(ConversationMessage.id))
            .where(ConversationMessage.organization_id == organization_id)
        )

        # Get Recent Conversations (Top 5)
        recent_convos_result = await db.execute(
            select(Conversation)
            .where(Conversation.organization_id == organization_id)
            .order_by(desc(Conversation.created_at))
            .limit(5)
        )
        recent_conversations = []
        for c in recent_convos_result.scalars().all():
            recent_conversations.append({
                "id": str(c.id),
                "title": c.title or "New Conversation",
                "created_at": c.created_at.isoformat()
            })

        # Calculate 7-Day Activity for chart (conversations AND messages per day)
        today = datetime.utcnow().date()
        chart_data = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            start_of_day = datetime(day.year, day.month, day.day)
            end_of_day = start_of_day + timedelta(days=1)
            
            day_convos = await db.scalar(
                select(func.count(Conversation.id))
                .where(Conversation.organization_id == organization_id)
                .where(Conversation.created_at >= start_of_day)
                .where(Conversation.created_at < end_of_day)
            )
            
            day_messages = await db.scalar(
                select(func.count(ConversationMessage.id))
                .where(ConversationMessage.organization_id == organization_id)
                .where(ConversationMessage.created_at >= start_of_day)
                .where(ConversationMessage.created_at < end_of_day)
            )
            
            chart_data.append({
                "date": day.strftime("%b %d"),
                "conversations": day_convos or 0,
                "messages": day_messages or 0
            })

        # Knowledge Base Composition
        kb_result = await db.execute(
            select(Document.source, func.count(Document.id))
            .where(Document.workspace_id == organization_id)
            .group_by(Document.source)
        )
        knowledge_composition = []
        for row in kb_result.all():
            source = row[0] or "Unknown"
            count = row[1]
            knowledge_composition.append({
                "source": source,
                "count": count
            })

        # Top Assistants by Usage
        top_assistants_result = await db.execute(
            select(Assistant.assistant_name, func.count(Conversation.id).label('usage_count'))
            .join(Conversation, Conversation.agent_id == Assistant.assistant_id)
            .where(Assistant.organization_id == organization_id)
            .group_by(Assistant.assistant_name)
            .order_by(desc('usage_count'))
            .limit(5)
        )
        top_assistants = []
        for row in top_assistants_result.all():
            top_assistants.append({
                "name": row[0],
                "conversations": row[1]
            })

        return {
            "total_assistants": total_assistants or 0,
            "active_connectors": active_connectors,
            "total_credentials": total_credentials or 0,
            "total_conversations": total_conversations or 0,
            "total_messages": total_messages or 0,
            "system_health": system_health,
            "recent_conversations": recent_conversations,
            "activity_chart": chart_data,
            "knowledge_composition": knowledge_composition,
            "top_assistants": top_assistants
        }

    except Exception as e:
        logger.error(f"Failed to fetch dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard metrics")
