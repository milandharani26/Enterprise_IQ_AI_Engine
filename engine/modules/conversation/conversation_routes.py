from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from engine.shared.core.deps import get_db
from engine.shared.core.security import JWTService
from engine.modules.conversation.conversation_schemas import (
    NewUserMessagePayloadSchema,
    MessageResponseSchema,
    ConversationDetailResponseSchema,
)
from engine.modules.conversation.conversation_service import ConversationService
from engine.modules.conversation.conversation_models import Conversation
from uuid import UUID
from typing import List
from engine.shared.core.middleware import require_service_account

router = APIRouter(prefix="/conversations", tags=["Conversations & Chat Logs"])

security = HTTPBearer(auto_error=False)
jwt_service = JWTService()

@router.post("/chat", response_model=MessageResponseSchema, status_code=status.HTTP_201_CREATED)
async def process_chat_message(
    payload: NewUserMessagePayloadSchema,
    db: AsyncSession = Depends(get_db),
    auth: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Primary real-time chat execution hub.
    Receives prompt text from your frontend, logs it as a USER message,
    runs the AI core, logs the ASSISTANT response, and returns the AI reply.
    """
    print(f"Received chat payload: {payload.dict()}")
    # 1. Extract organization_id from the Service Token if present
    if auth and auth.credentials:
        try:
            from jose import jwt
            from engine.shared.config import get_settings

            settings = get_settings()
            service_secret = getattr(
                settings, "service_token_secret_key", "dev-service-token-secret-key"
            )

            # Decode using the Service Token Secret Key
            token_data = jwt.decode(
                auth.credentials, service_secret, algorithms=["HS256"]
            )

            if token_data:
                token_org_id = token_data.get("organization_id")
                if token_org_id:
                    try:
                        payload.organization_id = UUID(str(token_org_id))
                    except ValueError:
                        pass
        except Exception as e:
            # Token might be invalid or a placeholder. If so, it will fall back to default organization.
            print("Failed to decode service token:", e)

    service = ConversationService(db)
    return await service.handle_chat_turn(payload)


@router.get("/{conversation_id}/history", response_model=List[MessageResponseSchema])
async def fetch_chat_history(conversation_id: UUID, db: AsyncSession = Depends(get_db)):
    """Returns all message instances ordered by chronology for a given conversation session."""
    service = ConversationService(db)
    return await service.get_conversation_history(conversation_id)



@router.get("/{conversation_id}", response_model=ConversationDetailResponseSchema)
async def get_conversation_details(
    
    conversation_id: UUID, db: AsyncSession = Depends(get_db)

):
    """Fetches full conversational session tracking details alongside its historical records."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation room trace missing",,
        )
    return conversation