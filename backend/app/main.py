import os
import tempfile
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.routers import upload, process, health
from app.services.cleanup import cleanup_temp_files

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Medical Document Translator starting up...")
    
    # Cleanup task - runs every 30 seconds
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    yield
    
    # Shutdown
    print("🔄 Shutting down...")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    # Final cleanup
    await cleanup_temp_files()
    print("✅ Shutdown complete")

async def periodic_cleanup():
    """Periodische Bereinigung temporärer Dateien"""
    while True:
        try:
            await asyncio.sleep(30)  # Alle 30 Sekunden
            await cleanup_temp_files()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

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
        reload=os.getenv("ENVIRONMENT") == "development"
    ) 