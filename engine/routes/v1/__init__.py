from fastapi import APIRouter
from engine.routes.v1.health_route import router as health_router
from engine.modules.assistant.assistant_routes import router as assistant_router
from engine.modules.auth.auth_routes import router as auth_router

router = APIRouter()

# Register all v1 endpoints here
router.include_router(health_router)
router.include_router(assistant_router)
router.include_router(auth_router)
