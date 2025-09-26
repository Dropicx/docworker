import os
import tempfile
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routers import upload, process, health
from app.routers.settings_unified import router as settings_router
from app.services.cleanup import cleanup_temp_files
from app.database.init_db import init_database

# Configure logging for Railway - FORCE stdout output
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Force output to stdout for Railway
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)

# Also ensure print statements work
print("🔧 Logging configured for Railway deployment", flush=True)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - use both print and logger for Railway visibility
    print("🚀 Medical Document Translator starting up...", flush=True)
    logger.info("🚀 Medical Document Translator starting up...")
    
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}", flush=True)
    print(f"Railway Environment: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}", flush=True)
    print(f"Port: {os.getenv('PORT', '9122')}", flush=True)
    print(f"USE_OVH_ONLY: {os.getenv('USE_OVH_ONLY', 'not set')}", flush=True)
    
    # Initialize database
    print("🗄️ Initializing database...", flush=True)
    try:
        if init_database():
            print("✅ Database initialized successfully", flush=True)
            logger.info("Database initialized successfully")
        else:
            print("❌ Database initialization failed", flush=True)
            logger.error("Database initialization failed")
    except Exception as e:
        print(f"❌ Database initialization error: {e}", flush=True)
        logger.error(f"Database initialization error: {e}")
    
    # Log OVH configuration (without sensitive data)
    if os.getenv('OVH_AI_ENDPOINTS_ACCESS_TOKEN'):
        print("✅ OVH API Token is configured", flush=True)
        logger.info("✅ OVH API Token is configured")
    else:
        print("⚠️ OVH API Token is NOT configured", flush=True)
        logger.warning("⚠️ OVH API Token is NOT configured")
    
    print(f"OVH Base URL: {os.getenv('OVH_AI_BASE_URL', 'not set')}", flush=True)
    
    # Cleanup task - runs every 30 seconds
    cleanup_task = asyncio.create_task(periodic_cleanup())
    print("Started periodic cleanup task (30s interval)", flush=True)
    logger.info("Started periodic cleanup task (30s interval)")
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    # Final cleanup
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
                cleanup_log = f"🧹 Cleanup #{cleanup_count}: Removed {files_removed} temporary files"
                print(cleanup_log, flush=True)
                logger.info(cleanup_log)
            else:
                # Log auch wenn keine Dateien entfernt wurden (alle 5 Cleanups)
                if cleanup_count % 5 == 0:
                    status_log = f"✅ Cleanup #{cleanup_count}: System clean, no files to remove"
                    print(status_log, flush=True)
                    logger.debug(status_log)
        except asyncio.CancelledError:
            break
        except Exception as e:
            error_log = f"❌ Cleanup error: {e}"
            print(error_log, flush=True)
            logger.error(error_log)

# FastAPI App
app = FastAPI(
    title="Medical Document Translator",
    description="DSGVO-konforme Übersetzung medizinischer Dokumente",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") == "development" else None,
    lifespan=lifespan
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middleware - Docker-kompatibel (erlaubt interne Container-IPs)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # In Docker-Umgebung weniger restriktiv
)

# CORS Middleware - Railway compatible
allowed_origins = ["*"] if os.getenv("ENVIRONMENT") == "production" else [
    "http://localhost:9121", 
    "http://127.0.0.1:9121",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
            request_log = f"📥 {request.method} {request.url.path}"
            print(request_log, flush=True)
            logger.info(request_log)
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (datetime.now() - start_time).total_seconds()
    
    # Only log errors or slow requests
    if should_log and (response.status_code >= 400 or process_time > 1.0):
        response_log = f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}s"
        print(response_log, flush=True)
        logger.info(response_log)
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Relaxed CSP for Railway deployment
    if os.getenv("ENVIRONMENT") != "production":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
    
    return response

# Router einbinden
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(process.router, prefix="/api", tags=["process"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(settings_router, tags=["settings"])  # Settings has its own prefix

@app.get("/")
async def root():
    return {
        "message": "Medical Document Translator API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Railway provides PORT env variable
    port = int(os.getenv("PORT", "9122"))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        # Increase limits for large file uploads
        limit_max_requests=1000,
        limit_concurrency=100,
        # Set to 50MB for large image uploads
        h11_max_incomplete_event_size=52428800  # 50MB in bytes
    ) 