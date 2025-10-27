"""
Authentication Router

Provides endpoints for user authentication including login, token refresh,
logout, and password management. No public registration - users are created by admins.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.permissions import (
    get_current_user_required,
    log_auth_failure,
    log_permission_denied
)
from app.database.auth_models import UserDB, UserRole
from app.database.connection import get_session
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ==================== PYDANTIC MODELS ====================

class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    user: "UserResponse" = Field(..., description="User information")


class RefreshRequest(BaseModel):
    """Token refresh request model"""
    refresh_token: str = Field(..., description="Refresh token")


class RefreshResponse(BaseModel):
    """Token refresh response model"""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class LogoutRequest(BaseModel):
    """Logout request model"""
    refresh_token: str = Field(..., description="Refresh token to revoke")


class LogoutResponse(BaseModel):
    """Logout response model"""
    message: str = Field(..., description="Logout confirmation message")


class UserResponse(BaseModel):
    """User response model (public user data)"""
    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="User active status")
    created_at: str = Field(..., description="Account creation date")
    last_login_at: str | None = Field(None, description="Last login date")

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Change password request model"""
    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class ChangePasswordResponse(BaseModel):
    """Change password response model"""
    message: str = Field(..., description="Password change confirmation message")


# ==================== AUTHENTICATION ENDPOINTS ====================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_session)
):
    """
    Authenticate user and return access and refresh tokens.

    Args:
        request: FastAPI request object
        login_data: Login credentials
        db: Database session

    Returns:
        Access token, refresh token, and user information

    Raises:
        HTTPException: If authentication fails
    """
    try:
        auth_service = AuthService(db)

        # Authenticate user
        user = auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            # Log failed authentication
            log_auth_failure(login_data.email, request, "invalid_credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        # Create tokens
        tokens = auth_service.create_tokens(user)

        # Log successful login
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=user.id,
            action="USER_LOGIN",
            resource_type="authentication",
            resource_id=str(user.id),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        logger.info(f"User {login_data.email} logged in successfully")

        return LoginResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {login_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        ) from e


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_session)
):
    """
    Refresh access token using refresh token.

    Args:
        refresh_data: Refresh token
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        auth_service = AuthService(db)

        # Refresh access token
        access_token = auth_service.refresh_access_token(refresh_data.refresh_token)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        logger.debug("Access token refreshed successfully")

        return RefreshResponse(access_token=access_token)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        ) from e


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    logout_data: LogoutRequest,
    db: Session = Depends(get_session)
):
    """
    Logout user by revoking refresh token.

    Args:
        request: FastAPI request object
        logout_data: Refresh token to revoke
        db: Database session

    Returns:
        Logout confirmation message
    """
    try:
        auth_service = AuthService(db)

        # Revoke refresh token
        success = auth_service.revoke_refresh_token(logout_data.refresh_token)

        if not success:
            logger.warning("Failed to revoke refresh token during logout")

        # Log logout (if we can identify the user)
        try:
            # Try to get user from refresh token before revoking
            from app.core.security import hash_api_key
            refresh_token_hash = hash_api_key(logout_data.refresh_token)
            from app.repositories.refresh_token_repository import RefreshTokenRepository
            refresh_repo = RefreshTokenRepository(db)
            stored_token = refresh_repo.get_by_hash(refresh_token_hash)

            if stored_token:
                from app.repositories.audit_log_repository import AuditLogRepository
                audit_repo = AuditLogRepository(db)
                audit_repo.create_log(
                    user_id=stored_token.user_id,
                    action="USER_LOGOUT",
                    resource_type="authentication",
                    resource_id=str(stored_token.user_id),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
        except Exception as e:
            logger.debug(f"Could not log logout event: {e}")

        logger.info("User logged out successfully")

        return LogoutResponse(message="Logged out successfully")

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        ) from e


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserDB = Depends(get_current_user_required)
):
    """
    Get current user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: UserDB = Depends(get_current_user_required),
    db: Session = Depends(get_session)
):
    """
    Change user's password.

    Args:
        request: FastAPI request object
        password_data: Old and new password
        current_user: Current authenticated user
        db: Database session

    Returns:
        Password change confirmation message

    Raises:
        HTTPException: If password change fails
    """
    try:
        auth_service = AuthService(db)

        # Change password
        success = auth_service.change_password(
            current_user.id,
            password_data.old_password,
            password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            ) from e

        logger.info(f"Password changed for user {current_user.email}")

        return ChangePasswordResponse(message="Password changed successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        ) from e


@router.post("/logout-all")
async def logout_all_devices(
    current_user: UserDB = Depends(get_current_user_required),
    db: Session = Depends(get_session)
):
    """
    Logout from all devices by revoking all refresh tokens.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Logout confirmation message
    """
    try:
        auth_service = AuthService(db)

        # Revoke all user tokens
        count = auth_service.revoke_all_user_tokens(current_user.id)

        # Log logout all
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="USER_LOGOUT",
            resource_type="authentication",
            resource_id=str(current_user.id),
            details={"logout_all": True, "tokens_revoked": count}
        )

        logger.info(f"User {current_user.email} logged out from all devices ({count} tokens revoked)")

        return {"message": f"Logged out from all devices ({count} tokens revoked)"}

    except Exception as e:
        logger.error(f"Logout all error for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout all failed"
        ) from e


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def auth_health_check():
    """
    Authentication service health check.

    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "version": "1.0.0"
    }
