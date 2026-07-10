from fastapi import APIRouter
from fastapi.responses import JSONResponse
from engine.shared.config import get_settings

router = APIRouter()
settings = get_settings()

import httpx

@router.get("/health", tags=["System"])
async def health_check():
    """Liveness check for the engine."""
    return JSONResponse(content={"status": "ok", "service": "engine", "env": settings.ENV})

@router.get("/ping-google", tags=["System"])
async def ping_google():
    """Test endpoint that uses the newly installed httpx package."""
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.google.com")
        return JSONResponse(content={
            "status": "success",
            "message": "Successfully imported and used httpx!",
            "google_status_code": response.status_code
        })
