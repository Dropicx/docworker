"""
Settings Authentication Router

Minimal authentication endpoints for settings UI.
All pipeline configuration now handled by modular_pipeline.py router.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, status, Header
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])

# ==================== PYDANTIC MODELS ====================

class AuthRequest(BaseModel):
    password: str = Field(..., description="Access code for settings")

class AuthResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None

# ==================== AUTHENTICATION ====================

def verify_session_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify session token from Authorization header."""
    if not authorization:
        return False

    try:
        if not authorization.startswith("Bearer "):
            return False

        token = authorization.replace("Bearer ", "")

        # Simple token validation - in production use JWT
        # For now, just check if token matches access code hash
        import hashlib
        expected_token = hashlib.sha256(settings.admin_access_code.encode()).hexdigest()

        return token == expected_token

    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return False

@router.post("/auth", response_model=AuthResponse)
async def authenticate(auth_request: AuthRequest):
    """
    Authenticate with access code.
    Returns a session token for subsequent requests.
    """
    try:
        if auth_request.password == settings.admin_access_code:
            # Generate session token
            import hashlib
            session_token = hashlib.sha256(settings.admin_access_code.encode()).hexdigest()

            logger.info("Settings authentication successful")
            return AuthResponse(
                success=True,
                message="Authentifizierung erfolgreich",
                session_token=session_token
            )
        else:
            logger.warning("Settings authentication failed - invalid code")
            return AuthResponse(
                success=False,
                message="Ungültiger Zugangscode"
            )

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )

@router.get("/check-auth")
async def check_auth(authenticated: bool = Depends(verify_session_token)):
    """Check if current session is authenticated."""
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return {"authenticated": True, "message": "Session valid"}
