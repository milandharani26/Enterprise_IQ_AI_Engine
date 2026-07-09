from engine.shared.core.middleware import require_admin
from fastapi import APIRouter, Depends, Query, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from engine.shared.core.deps import get_db, get_current_organization_id
from engine.modules.auth.auth_models import User
from engine.modules.assistant.assistant_schemas import (
    AssistantCreate, AssistantUpdate, AssistantResponse, AssistantStatusUpdate, ToolInfoResponse,
    PreviewPromptRequest, PreviewPromptResponse
)
from engine.modules.assistant.assistant_service import AssistantService
from engine.modules.assistant.tools.tool_registry import ToolRegistryNew

router = APIRouter(prefix="/assistants", tags=["assistants"])

@router.get("/tools", response_model=List[ToolInfoResponse])
async def get_available_tools(
    current_user: User = Depends(require_admin),
):
    """Get list of available tools from the registry."""
    tools = ToolRegistryNew.get_available_tools()
    result = []
    for tool_cls in tools:
        tool_instance = tool_cls()
        result.append(ToolInfoResponse(
            tool_id=tool_instance.name,
            description=tool_instance.properties.description,
            category=tool_instance.properties.category,
            default_instructions=tool_instance.properties.default_instructions
        ))
    return result


@router.get("/available-llms")
async def get_available_llms(
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(require_admin)
):
    """
    Get the list of LLM providers and their available models dynamically
    based on the organization's credentials, falling back to system keys.
    """
    import httpx
    import os
    import asyncio
    import logging
    from sqlalchemy import select
    from engine.shared.models.credential_model import Credential
    from engine.shared.security.encryption import decrypt_value
    from engine.shared.config.settings import get_settings

    inner_logger = logging.getLogger("available_llms")
    settings = get_settings()
    available_providers = []

    # 1. Fetch credentials from DB for the organization
    stmt = select(Credential).where(
        Credential.organization_id == org_id,
        Credential.provider.in_(["Google API Key", "OpenAI API Key"]),
        Credential.status == "Active"
    )
    res = await db.execute(stmt)
    credentials = res.scalars().all()

    # Map database provider name to provider ID
    org_providers = {c.provider: c for c in credentials}

    # Helper to fetch models from OpenAI
    async def fetch_openai_models(api_key: str) -> list[str]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=api_key)
            resp = await asyncio.wait_for(client.models.list(), timeout=5)
            valid_models = []
            for m in resp.data:
                mid = m.id.lower()
                if any(x in mid for x in ["gpt-4", "gpt-3.5", "o1-", "o3-"]) and "embedding" not in mid and "moderation" not in mid:
                    valid_models.append(m.id)
            return sorted(valid_models)
        except Exception as e:
            inner_logger.error(f"[AvailableLLMs] Failed to fetch OpenAI models: {e}")
            return ["gpt-4o-mini", "gpt-4o", "o3-mini"]

    # Helper to fetch models from Google Gemini
    async def fetch_gemini_models(api_key: str) -> list[str]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    valid_models = []
                    for m in models:
                        name = m.get("name", "")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods:
                            short_name = name.replace("models/", "")
                            if not any(x in short_name for x in ["embedding", "aqa", "experimental"]):
                                valid_models.append(short_name)
                    return sorted(valid_models)
                else:
                    inner_logger.error(f"[AvailableLLMs] Google models API returned status {resp.status_code}")
        except Exception as e:
            inner_logger.error(f"[AvailableLLMs] Failed to fetch Gemini models: {e}")
        return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"]

    has_org_creds = len(org_providers) > 0

    # Check Google Gemini
    google_cred = org_providers.get("Google API Key")
    google_key = ""
    if google_cred:
        google_key = decrypt_value(google_cred.auth_data.get("api_key") or "")
    elif not has_org_creds:
        # Fall back to host env key only if the organization has no credentials of their own configured
        google_key = os.getenv("GOOGLE_API_KEY") or getattr(settings, "google_api_key", "")

    if google_key:
        models = await fetch_gemini_models(google_key)
        available_providers.append({
            "id": "google",
            "name": "Google Gemini",
            "models": models
        })

    # Check OpenAI
    openai_cred = org_providers.get("OpenAI API Key")
    openai_key = ""
    if openai_cred:
        openai_key = decrypt_value(openai_cred.auth_data.get("api_key") or "")
    elif not has_org_creds:
        # Fall back to host env key only if the organization has no credentials of their own configured
        openai_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "openai_api_key", "")

    if openai_key:
        models = await fetch_openai_models(openai_key)
        available_providers.append({
            "id": "openai",
            "name": "OpenAI",
            "models": models
        })

    return {"providers": available_providers}


@router.post("/preview-prompt", response_model=PreviewPromptResponse)
async def preview_prompt(
    preview_request: PreviewPromptRequest,
    current_user: User = Depends(require_admin),
):
    """Preview the compiled prompt and its metadata before saving an assistant."""
    return await AssistantService.preview_prompt(preview_request)

@router.post("", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    assistant_in: AssistantCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id)
):
    """Create a new assistant."""
    return await AssistantService.create_assistant(
        db=db,
        obj_in=assistant_in,
        user_id=current_user.id,
        org_id=org_id
    )

@router.get("", response_model=List[AssistantResponse])
async def get_assistants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id)
):
    """Get list of assistants with pagination."""
    return await AssistantService.get_assistants(
        db=db,
        skip=skip,
        limit=limit,
        org_id=org_id
    )

@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id)
):
    """Get assistant details."""
    return await AssistantService.get_assistant(db=db, assistant_id=assistant_id, org_id=org_id)

@router.put("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    assistant_in: AssistantCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id)
):
    """Update assistant details."""
    return await AssistantService.update_assistant(
        db=db,
        assistant_id=assistant_id,
        obj_in=assistant_in,
        user_id=current_user.id,
        org_id=org_id
    )

@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id)
):
    """Soft delete assistant."""
    await AssistantService.soft_delete_assistant(
        db=db,
        assistant_id=assistant_id,
        user_id=current_user.id,
        org_id=org_id
    )

@router.patch("/{assistant_id}/status", response_model=AssistantResponse)
async def update_assistant_status(
    assistant_id: UUID,
    status_in: AssistantStatusUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_organization_id)
):
    """Enable/Disable assistant."""
    return await AssistantService.update_status(
        db=db,
        assistant_id=assistant_id,
        obj_in=status_in,
        user_id=current_user.id,
        org_id=org_id
    )




