import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime
import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.error_middleware import register_error_handlers
from app.database.init_db import init_database
from app.routers import health, process, upload
from app.routers.admin.config import router as admin_config_router
from app.routers.api_keys import router as api_keys_router
from app.routers.audit import router as audit_router
from app.routers.auth import router as auth_router
from app.routers.modular_pipeline import router as modular_pipeline_router
from app.routers.monitoring import router as monitoring_router
from app.routers.cost_statistics import router as cost_statistics_router
from app.routers.feedback import router as feedback_router
from app.routers.privacy_metrics import router as privacy_metrics_router
from app.routers.process_multi_file import router as multi_file_router
from app.routers.settings_auth import router as settings_auth_router
from app.routers.users import router as users_router
from app.services.cache_service import CacheService
from app.services.cleanup import cleanup_temp_files

# Configure logging with centralized settings
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format,
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Force output to stdout for Railway
    ],
    force=True,  # Override any existing configuration
)
logger = logging.getLogger(__name__)
logger.info("🔧 Logging configured for Railway deployment")

# Rate limiting (disabled in test/development)
limiter = Limiter(
    key_func=get_remote_address,
    enabled=os.getenv("ENVIRONMENT") not in ["test", "development"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Medical Document Translator starting up...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Railway Environment: {settings.railway_environment or 'not set'}")
    logger.info(f"Port: {settings.port}")
    logger.info(f"USE_OVH_ONLY: {settings.use_ovh_only}")

    # Detect test environment (pytest sets sys.modules['pytest'] when running)
    is_testing = "pytest" in sys.modules
    if is_testing:
        logger.info("🧪 Test environment detected - skipping database initialization")

    # Validate configuration
    if not is_testing:
        try:
            settings.validate_on_startup()
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            raise

    # Initialize database (skip in test environment)
    if not is_testing:
        logger.info("🗄️ Initializing database...")
        try:
            if init_database():
                logger.info("✅ Database initialized successfully")
            else:
                logger.error("❌ Database initialization failed")
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")

    # Initialize Redis cache (skip in test environment)
    cache_service = None
    if not is_testing and settings.cache_enabled:
        logger.info("🔄 Initializing Redis cache...")
        cache_service = CacheService()
        if await cache_service.health_check():
            logger.info("✅ Redis cache initialized successfully")
        else:
            logger.warning("⚠️ Redis cache unavailable - using database only")

    # Cleanup task - runs every 30 seconds (skip in test environment)
    cleanup_task = None
    if not is_testing:
        cleanup_task = asyncio.create_task(periodic_cleanup())
        logger.info("✅ Started periodic cleanup task (30s interval)")

    yield

    # Shutdown
    logger.info("🔄 Shutting down...")
    if cleanup_task is not None:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

    # Close Redis cache connections
    if cache_service is not None:
        await cache_service.close()
        logger.info("✅ Redis cache connections closed")

    # Final cleanup (skip in test environment to avoid cleanup conflicts)
    if not is_testing:
        await cleanup_temp_files()
    logger.info("✅ Shutdown complete")


async def periodic_cleanup():
    """Periodische Bereinigung temporärer Dateien"""
    cleanup_count = 0
    while True:
        try:
            await asyncio.sleep(30)  # Alle 30 Sekunden
            files_removed = await cleanup_temp_files()
            cleanup_count += 1
            if files_removed > 0:
                logger.info(f"🧹 Cleanup #{cleanup_count}: Removed {files_removed} temporary files")
            else:
                # Log auch wenn keine Dateien entfernt wurden (alle 5 Cleanups)
                if cleanup_count % 5 == 0:
                    logger.debug(f"✅ Cleanup #{cleanup_count}: System clean, no files to remove")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")


# FastAPI App
app = FastAPI(
    title=settings.app_name,
    description="GDPR-compliant medical document translation service",
    version="1.0.0",
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan,
)

# Register error handlers for standardized error responses
register_error_handlers(app)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    max_age=settings.cors_max_age,
)


# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()

    # Skip logging for status polling and health check endpoints to reduce spam
    skip_paths = ["/status", "/health", "/health/simple"]
    should_log = not any(request.url.path.endswith(path) for path in skip_paths)

    # Only log important requests (uploads, processing, errors)
    if should_log and request.method != "OPTIONS":
        # Only log non-GET requests or important GET requests
        if request.method != "GET" or "/process/" in request.url.path:
            logger.info(f"📥 {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = (datetime.now() - start_time).total_seconds()

    # Only log errors or slow requests
    if should_log and (response.status_code >= 400 or process_time > 1.0):
        logger.warning(
            f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s"
        )

    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)

    return response


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Enhanced security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

    # Content Security Policy
    if settings.is_production:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    else:
        # Relaxed CSP for development
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'"
        )

    return response


# Router einbinden
# Public endpoints (no authentication required)
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(multi_file_router, prefix="/api", tags=["multi-file"])
app.include_router(health.router, prefix="/api", tags=["health"])

# Authentication and user management
app.include_router(auth_router, tags=["authentication"])
app.include_router(users_router, tags=["users"])
app.include_router(api_keys_router, tags=["api-keys"])
app.include_router(audit_router, tags=["audit"])

# Legacy endpoints (will be updated with proper authentication)
app.include_router(settings_auth_router, tags=["settings"])  # Minimal auth for settings UI
app.include_router(
    modular_pipeline_router, tags=["pipeline"]
)  # Modular pipeline has its own prefix
app.include_router(admin_config_router, tags=["admin"])  # Admin configuration management
app.include_router(
    monitoring_router, tags=["monitoring"]
)  # Flower dashboard proxy and worker monitoring
app.include_router(
    privacy_metrics_router, tags=["privacy"]
)  # Privacy filter metrics and monitoring (Issue #35)
app.include_router(
    cost_statistics_router, tags=["cost-statistics"]
)  # Cost statistics dashboard (Issue #51)
app.include_router(
    feedback_router, tags=["feedback"]
)  # User feedback system with GDPR data protection (Issue #47)


@app.get("/")
async def root():
    return {
        "message": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # nosec
        port=settings.port,
        reload=settings.is_development,
        # Increase limits for large file uploads
        limit_max_requests=1000,
        limit_concurrency=100,
        # Set to 50MB for large image uploads
        h11_max_incomplete_event_size=settings.max_file_size_bytes,
    )
