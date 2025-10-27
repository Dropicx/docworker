"""
API Keys Router

Provides endpoints for API key management including creation, listing,
revocation, and usage tracking. Users can manage their own keys, admins
can manage all keys.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import (
    get_current_user_required,
    require_admin,
    check_resource_access
)
from app.database.auth_models import UserDB, APIKeyDB
from app.database.connection import get_session
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


# ==================== PYDANTIC MODELS ====================

class CreateAPIKeyRequest(BaseModel):
    """Create API key request model"""
    name: str = Field(..., min_length=1, max_length=255, description="User-friendly name for the key")
    expires_days: int | None = Field(None, ge=1, le=365, description="Days until expiration (1-365)")


class CreateAPIKeyResponse(BaseModel):
    """Create API key response model"""
    api_key: str = Field(..., description="Generated API key (only shown once)")
    key_id: str = Field(..., description="API key ID")
    name: str = Field(..., description="Key name")
    expires_at: str | None = Field(None, description="Expiration date")
    created_at: str = Field(..., description="Creation date")


class APIKeyResponse(BaseModel):
    """API key response model (without key value)"""
    id: UUID = Field(..., description="API key ID")
    name: str = Field(..., description="Key name")
    is_active: bool = Field(..., description="Active status")
    expires_at: str | None = Field(None, description="Expiration date")
    last_used_at: str | None = Field(None, description="Last used date")
    usage_count: int = Field(..., description="Usage count")
    created_at: str = Field(..., description="Creation date")

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """API key list response model"""
    keys: list[APIKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of keys")


class RevokeAPIKeyResponse(BaseModel):
    """Revoke API key response model"""
    message: str = Field(..., description="Revocation confirmation message")


class UpdateAPIKeyRequest(BaseModel):
    """Update API key request model"""
    name: str | None = Field(None, min_length=1, max_length=255, description="New key name")
    expires_days: int | None = Field(None, ge=1, le=365, description="New expiration days")


class UpdateAPIKeyResponse(BaseModel):
    """Update API key response model"""
    message: str = Field(..., description="Update confirmation message")


# ==================== USER API KEY ENDPOINTS ====================

@router.post("", response_model=CreateAPIKeyResponse)
async def create_api_key(
    request: Request,
    key_data: CreateAPIKeyRequest,
    current_user: UserDB = Depends(get_current_user_required),
    db: Session = Depends(get_session)
):
    """
    Create a new API key for the current user.

    Args:
        request: FastAPI request object
        key_data: API key creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Generated API key and metadata

    Raises:
        HTTPException: If creation fails
    """
    try:
        auth_service = AuthService(db)

        # Create API key
        plain_key, key_id = auth_service.create_api_key(
            user_id=current_user.id,
            name=key_data.name,
            expires_days=key_data.expires_days
        )

        # Get the created key for response
        from app.repositories.api_key_repository import APIKeyRepository
        api_key_repo = APIKeyRepository(db)
        created_key = api_key_repo.get_by_id(UUID(key_id))

        logger.info(f"Created API key '{key_data.name}' for user {current_user.email}")

        return CreateAPIKeyResponse(
            api_key=plain_key,
            key_id=key_id,
            name=created_key.name,
            expires_at=created_key.expires_at.isoformat() if created_key.expires_at else None,
            created_at=created_key.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Error creating API key for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    current_user: UserDB = Depends(get_current_user_required),
    db: Session = Depends(get_session)
):
    """
    List all API keys for the current user.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of user's API keys
    """
    try:
        auth_service = AuthService(db)
        keys = auth_service.get_user_api_keys(current_user.id)

        key_responses = [
            APIKeyResponse(
                id=key.id,
                name=key.name,
                is_active=key.is_active,
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                usage_count=key.usage_count,
                created_at=key.created_at.isoformat()
            )
            for key in keys
        ]

        return APIKeyListResponse(keys=key_responses, total=len(key_responses))

    except Exception as e:
        logger.error(f"Error listing API keys for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.delete("/{key_id}", response_model=RevokeAPIKeyResponse)
async def revoke_api_key(
    key_id: str,
    current_user: UserDB = Depends(get_current_user_required),
    db: Session = Depends(get_session)
):
    """
    Revoke an API key for the current user.

    Args:
        key_id: API key ID to revoke
        current_user: Current authenticated user
        db: Database session

    Returns:
        Revocation confirmation message

    Raises:
        HTTPException: If revocation fails
    """
    try:
        auth_service = AuthService(db)

        # Revoke API key
        success = auth_service.revoke_api_key(key_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or access denied"
            )

        logger.info(f"Revoked API key {key_id} for user {current_user.email}")

        return RevokeAPIKeyResponse(message="API key revoked successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key {key_id} for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.put("/{key_id}", response_model=UpdateAPIKeyResponse)
async def update_api_key(
    key_id: str,
    update_data: UpdateAPIKeyRequest,
    current_user: UserDB = Depends(get_current_user_required),
    db: Session = Depends(get_session)
):
    """
    Update an API key for the current user.

    Args:
        key_id: API key ID to update
        update_data: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        Update confirmation message

    Raises:
        HTTPException: If update fails
    """
    try:
        from app.repositories.api_key_repository import APIKeyRepository
        api_key_repo = APIKeyRepository(db)

        # Get API key
        api_key = api_key_repo.get_by_id(UUID(key_id))
        if not api_key or api_key.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found or access denied"
            )

        # Update fields
        update_fields = {}
        if update_data.name is not None:
            update_fields["name"] = update_data.name

        if update_data.expires_days is not None:
            from datetime import timedelta
            update_fields["expires_at"] = datetime.now(datetime.UTC) + timedelta(days=update_data.expires_days)

        if update_fields:
            api_key_repo.update(UUID(key_id), **update_fields)

            # Log update
            from app.repositories.audit_log_repository import AuditLogRepository
            audit_repo = AuditLogRepository(db)
            audit_repo.create_log(
                user_id=current_user.id,
                action="API_KEY_UPDATED",
                resource_type="api_key",
                resource_id=key_id,
                details=update_fields
            )

        logger.info(f"Updated API key {key_id} for user {current_user.email}")

        return UpdateAPIKeyResponse(message="API key updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key {key_id} for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update API key"
        )


# ==================== ADMIN API KEY ENDPOINTS ====================

@router.get("/admin/all", response_model=APIKeyListResponse)
async def list_all_api_keys(
    skip: int = 0,
    limit: int = 100,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    List all API keys across all users (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        List of all API keys
    """
    try:
        from app.repositories.api_key_repository import APIKeyRepository
        api_key_repo = APIKeyRepository(db)

        keys = api_key_repo.get_all_active(skip=skip, limit=limit)

        key_responses = [
            APIKeyResponse(
                id=key.id,
                name=key.name,
                is_active=key.is_active,
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                usage_count=key.usage_count,
                created_at=key.created_at.isoformat()
            )
            for key in keys
        ]

        return APIKeyListResponse(keys=key_responses, total=len(key_responses))

    except Exception as e:
        logger.error(f"Error listing all API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get("/admin/user/{user_id}", response_model=APIKeyListResponse)
async def list_user_api_keys(
    user_id: str,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    List API keys for a specific user (admin only).

    Args:
        user_id: User ID to get keys for
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        List of user's API keys
    """
    try:
        from app.repositories.api_key_repository import APIKeyRepository
        api_key_repo = APIKeyRepository(db)

        keys = api_key_repo.get_by_user(UUID(user_id))

        key_responses = [
            APIKeyResponse(
                id=key.id,
                name=key.name,
                is_active=key.is_active,
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                usage_count=key.usage_count,
                created_at=key.created_at.isoformat()
            )
            for key in keys
        ]

        return APIKeyListResponse(keys=key_responses, total=len(key_responses))

    except Exception as e:
        logger.error(f"Error listing API keys for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list user API keys"
        )


@router.delete("/admin/{key_id}", response_model=RevokeAPIKeyResponse)
async def admin_revoke_api_key(
    key_id: str,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Revoke any API key (admin only).

    Args:
        key_id: API key ID to revoke
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Revocation confirmation message

    Raises:
        HTTPException: If revocation fails
    """
    try:
        from app.repositories.api_key_repository import APIKeyRepository
        api_key_repo = APIKeyRepository(db)

        # Get API key
        api_key = api_key_repo.get_by_id(UUID(key_id))
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        # Revoke key
        success = api_key_repo.revoke_key(UUID(key_id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke API key"
            )

        # Log admin action
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="API_KEY_REVOKED",
            resource_type="api_key",
            resource_id=key_id,
            details={"revoked_by_admin": True, "original_user_id": str(api_key.user_id)}
        )

        logger.info(f"Admin {current_user.email} revoked API key {key_id} (owned by user {api_key.user_id})")

        return RevokeAPIKeyResponse(message="API key revoked successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key {key_id} by admin {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


@router.post("/admin/cleanup")
async def cleanup_expired_keys(
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Clean up expired API keys (admin only).

    Args:
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Cleanup results
    """
    try:
        from app.repositories.api_key_repository import APIKeyRepository
        api_key_repo = APIKeyRepository(db)

        count = api_key_repo.cleanup_expired_keys()

        # Log cleanup action
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="API_KEY_CLEANUP",
            resource_type="system",
            resource_id="api_keys",
            details={"keys_cleaned": count}
        )

        logger.info(f"Admin {current_user.email} cleaned up {count} expired API keys")

        return {"message": f"Cleaned up {count} expired API keys"}

    except Exception as e:
        logger.error(f"Error cleaning up API keys by admin {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup API keys"
        )


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def api_keys_health_check():
    """
    API keys service health check.

    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "api-keys",
        "version": "1.0.0"
    }
