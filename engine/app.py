"""FastAPI application factory — production-ready with full middleware stack."""

from pathlib import Path
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from shared.logging import setup as setup_logging
from engine.shared.config import get_settings
from engine.shared.exceptions.exceptions import GlobalExceptionHandler, AppException
from engine.shared.db.session import AsyncSessionLocal

settings = get_settings()
logger = logging.getLogger("engine")

_PUBLIC_DIR = Path(__file__).resolve().parents[1] / "cpanel" / "out"


def create_app() -> FastAPI:
    app = FastAPI(
        title="My New API Engine",
        description="Core FastAPI engine for my project",
        version="0.1.0",
        debug=(settings.ENV == "local"),
        swagger_ui_parameters={"persistAuthorization": True}
    )

    # --- CORS (Cross-Origin Resource Sharing) ---
    _cors_origins = [
        o.strip()
        for o in settings.CORS_ORIGINS.split(",")
        if o.strip()
    ] if getattr(settings, "CORS_ORIGINS", None) else ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # --- Custom Middlewares ---
    # app.add_middleware(AuthMiddleware)
    # app.add_middleware(RequestLoggingMiddleware)

    # --- Global Exception Handlers ---
    app.add_exception_handler(AppException, GlobalExceptionHandler.handle_app_exception)
    app.add_exception_handler(RequestValidationError, GlobalExceptionHandler.handle_validation)
    app.add_exception_handler(HTTPException, GlobalExceptionHandler.handle_http)
    app.add_exception_handler(Exception, GlobalExceptionHandler.handle_unhandled)

    # --- API Routes ---
    from engine.routes.v1 import router as api_v1_router
    app.include_router(api_v1_router, prefix="/api/v1")

    # --- Frontend Static Files (Optional for rendering React/Next.js builds directly from FastAPI) ---
    if _PUBLIC_DIR.exists() and (_PUBLIC_DIR / "_next").exists():
        app.mount("/_next", StaticFiles(directory=str(_PUBLIC_DIR / "_next")), name="next_assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Fallback to index.html for frontend routing."""
        file_path = _PUBLIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
            
        # Check if it's an HTML page (e.g. /dashboard -> /dashboard.html or /dashboard/index.html)
        html_file_path = _PUBLIC_DIR / f"{full_path}.html"
        if html_file_path.exists() and html_file_path.is_file():
            return FileResponse(str(html_file_path))
            
        html_index_path = _PUBLIC_DIR / full_path / "index.html"
        if html_index_path.exists() and html_index_path.is_file():
            return FileResponse(str(html_index_path))
        
        index_path = _PUBLIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
            
        return JSONResponse(status_code=404, content={"message": "Frontend not found"})

    # --- Application Lifecycle Events ---
    @app.on_event("startup")
    async def startup():
        # Setup logging
        setup_logging(service_name="engine")
        logger.setLevel(logging.DEBUG if settings.ENV == "local" else logging.INFO)
        logger.info(f"🚀 Engine starting — env={settings.ENV}")
        
        # Check pgvector or database connection
        try:
            from sqlalchemy import text
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                )
                version = result.scalar_one_or_none()
                if version:
                    logger.info(f"✅ pgvector {version} detected")
                else:
                    logger.warning("⚠️ pgvector not installed (vector search disabled)")
        except Exception as e:
            logger.warning(f"Database connection check skipped or failed: {e}")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("🛑 Engine shutting down.")

    return app
