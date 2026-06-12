from fastapi import APIRouter
from engine.routes.v1.health_route import router as health_router
from engine.modules.assistant import router as assistant_router
from engine.modules.auth import router as auth_router
from engine.modules.service_account import router as service_account_router

router = APIRouter()

# Register all v1 endpoints here
router.include_router(health_router)
router.include_router(assistant_router)
router.include_router(auth_router)
router.include_router(service_account_router, prefix="/service-accounts")
