from fastapi import APIRouter
from engine.routes.v1.health_route import router as health_router
from engine.modules.assistant import router as assistant_router
from engine.modules.auth import router as auth_router
from engine.modules.service_account import router as service_account_router
from engine.modules.conversation import conversation_router
from engine.modules.organization import organization_router
from engine.modules.documents import router as documents_router
from engine.modules.drive_documents import router as drive_documents_router

router = APIRouter()

# Register all v1 endpoints here
router.include_router(health_router)
router.include_router(assistant_router)
router.include_router(auth_router)
router.include_router(service_account_router)
router.include_router(conversation_router)
router.include_router(organization_router)
router.include_router(documents_router)
router.include_router(drive_documents_router)
