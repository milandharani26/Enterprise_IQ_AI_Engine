from fastapi import APIRouter
from engine.routes.v1.health_route import router as health_router

router = APIRouter()

# Register all v1 endpoints here
router.include_router(health_router)
