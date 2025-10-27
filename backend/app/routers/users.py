"""
Users Management Router

Provides endpoints for user management including creation, listing, updating,
and deletion. Admin-only endpoints for managing user accounts and roles.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.permissions import require_admin
from app.database.auth_models import UserDB, UserRole, UserStatus
from app.database.connection import get_session
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ==================== PYDANTIC MODELS ====================

class CreateUserRequest(BaseModel):
    """Create user request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    role: UserRole = Field(..., description="User role")


class CreateUserResponse(BaseModel):
    """Create user response model"""
    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: UserRole = Field(..., description="User role")
    status: UserStatus = Field(..., description="User status")
    created_at: str = Field(..., description="Creation date")


class UserResponse(BaseModel):
    """User response model (public user data)"""
    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    role: UserRole = Field(..., description="User role")
    status: UserStatus = Field(..., description="User status")
    is_active: bool = Field(..., description="User active status")
    created_at: str = Field(..., description="Account creation date")
    last_login_at: str | None = Field(None, description="Last login date")
    created_by_admin_id: UUID | None = Field(None, description="Admin who created this user")

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """User list response model"""
    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")


class UpdateUserRequest(BaseModel):
    """Update user request model"""
    email: EmailStr | None = Field(None, description="New email address")
    full_name: str | None = Field(None, min_length=1, max_length=255, description="New full name")
    role: UserRole | None = Field(None, description="New role")
    status: UserStatus | None = Field(None, description="New status")


class UpdateUserResponse(BaseModel):
    """Update user response model"""
    message: str = Field(..., description="Update confirmation message")


class ResetPasswordRequest(BaseModel):
    """Reset password request model"""
    new_password: str = Field(..., min_length=8, description="New password")


class ResetPasswordResponse(BaseModel):
    """Reset password response model"""
    message: str = Field(..., description="Password reset confirmation message")


class UserStatsResponse(BaseModel):
    """User statistics response model"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    admin_users: int = Field(..., description="Number of admin users")
    user_users: int = Field(..., description="Number of regular users")


# ==================== USER MANAGEMENT ENDPOINTS ====================

@router.post("", response_model=CreateUserResponse)
async def create_user(
    request: Request,
    user_data: CreateUserRequest,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Create a new user (admin only).

    Args:
        request: FastAPI request object
        user_data: User creation data
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Created user information

    Raises:
        HTTPException: If creation fails
    """
    try:
        auth_service = AuthService(db)

        # Create user
        user = auth_service.create_user_by_admin(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            role=user_data.role,
            created_by_admin_id=current_user.id
        )

        logger.info(f"Admin {current_user.email} created user {user_data.email} with role {user_data.role}")

        return CreateUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            created_at=user.created_at.isoformat()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Error creating user {user_data.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        ) from e


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    role_filter: UserRole | None = None,
    status_filter: UserStatus | None = None,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    List all users with optional filtering (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        role_filter: Filter by user role
        status_filter: Filter by user status
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        List of users
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        users = user_repo.list_all_users(
            skip=skip,
            limit=limit,
            role_filter=role_filter,
            status_filter=status_filter
        )

        user_responses = [
            UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                status=user.status,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
                created_by_admin_id=user.created_by_admin_id
            )
            for user in users
        ]

        return UserListResponse(users=user_responses, total=len(user_responses))

    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        ) from e


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get user by ID (admin only).

    Args:
        user_id: User ID to get
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        User information

    Raises:
        HTTPException: If user not found
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        user = user_repo.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
            created_by_admin_id=user.created_by_admin_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        ) from e


@router.put("/{user_id}", response_model=UpdateUserResponse)
async def update_user(
    user_id: str,
    update_data: UpdateUserRequest,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Update user information (admin only).

    Args:
        user_id: User ID to update
        update_data: Update data
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Update confirmation message

    Raises:
        HTTPException: If update fails
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        # Get user
        user = user_repo.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if admin is trying to update themselves
        if user.id == current_user.id and update_data.role and update_data.role != current_user.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role"
            )

        # Check if trying to demote last admin
        if user.role == UserRole.ADMIN and update_data.role and update_data.role != UserRole.ADMIN:
            admin_count = user_repo.count_admins()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote the last admin user"
                )

        # Check email uniqueness if changing email
        if update_data.email and update_data.email != user.email:
            if user_repo.is_email_taken(update_data.email, exclude_user_id=user.id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already taken"
                )

        # Update fields
        update_fields = {}
        if update_data.email is not None:
            update_fields["email"] = update_data.email
        if update_data.full_name is not None:
            update_fields["full_name"] = update_data.full_name
        if update_data.role is not None:
            update_fields["role"] = update_data.role
        if update_data.status is not None:
            update_fields["status"] = update_data.status
            update_fields["is_active"] = update_data.status == UserStatus.ACTIVE

        if update_fields:
            user_repo.update(UUID(user_id), **update_fields)

            # Log update
            from app.repositories.audit_log_repository import AuditLogRepository
            audit_repo = AuditLogRepository(db)
            audit_repo.create_log(
                user_id=current_user.id,
                action="USER_UPDATED",
                resource_type="user",
                resource_id=user_id,
                details=update_fields
            )

        logger.info(f"Admin {current_user.email} updated user {user_id}")

        return UpdateUserResponse(message="User updated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        ) from e


@router.delete("/{user_id}", response_model=UpdateUserResponse)
async def delete_user(
    user_id: str,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Delete user (soft delete - admin only).

    Args:
        user_id: User ID to delete
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Deletion confirmation message

    Raises:
        HTTPException: If deletion fails
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        # Get user
        user = user_repo.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if admin is trying to delete themselves
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        # Check if trying to delete last admin
        if user.role == UserRole.ADMIN:
            admin_count = user_repo.count_admins()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin user"
                )

        # Soft delete user
        success = user_repo.soft_delete_user(UUID(user_id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )

        # Log deletion
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="USER_DELETED",
            resource_type="user",
            resource_id=user_id,
            details={"deleted_user_email": user.email}
        )

        logger.info(f"Admin {current_user.email} deleted user {user.email}")

        return UpdateUserResponse(message="User deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        ) from e


@router.patch("/{user_id}/activate", response_model=UpdateUserResponse)
async def activate_user(
    user_id: str,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Activate a user account (admin only).

    Args:
        user_id: User ID to activate
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Activation confirmation message
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        success = user_repo.activate_user(UUID(user_id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Log activation
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="USER_UPDATED",
            resource_type="user",
            resource_id=user_id,
            details={"action": "activated"}
        )

        logger.info(f"Admin {current_user.email} activated user {user_id}")

        return UpdateUserResponse(message="User activated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate user"
        ) from e


@router.patch("/{user_id}/deactivate", response_model=UpdateUserResponse)
async def deactivate_user(
    user_id: str,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Deactivate a user account (admin only).

    Args:
        user_id: User ID to deactivate
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Deactivation confirmation message
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        # Check if trying to deactivate last admin
        user = user_repo.get_by_id(UUID(user_id))
        if user and user.role == UserRole.ADMIN:
            admin_count = user_repo.count_admins()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last admin user"
                )

        success = user_repo.deactivate_user(UUID(user_id))

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Log deactivation
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="USER_UPDATED",
            resource_type="user",
            resource_id=user_id,
            details={"action": "deactivated"}
        )

        logger.info(f"Admin {current_user.email} deactivated user {user_id}")

        return UpdateUserResponse(message="User deactivated successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user"
        ) from e


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: str,
    password_data: ResetPasswordRequest,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Reset user password (admin only).

    Args:
        user_id: User ID to reset password for
        password_data: New password data
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Password reset confirmation message
    """
    try:
        from app.core.security import hash_password
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        # Get user
        user = user_repo.get_by_id(UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Hash new password
        new_password_hash = hash_password(password_data.new_password)

        # Update password
        success = user_repo.change_password(UUID(user_id), new_password_hash)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password"
            )

        # Revoke all user tokens for security
        auth_service = AuthService(db)
        auth_service.revoke_all_user_tokens(UUID(user_id))

        # Log password reset
        from app.repositories.audit_log_repository import AuditLogRepository
        audit_repo = AuditLogRepository(db)
        audit_repo.create_log(
            user_id=current_user.id,
            action="PASSWORD_CHANGED",
            resource_type="user",
            resource_id=user_id,
            details={"reset_by_admin": True}
        )

        logger.info(f"Admin {current_user.email} reset password for user {user.email}")

        return ResetPasswordResponse(message="Password reset successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        ) from e


@router.get("/stats/overview", response_model=UserStatsResponse)
async def get_user_stats(
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session)
):
    """
    Get user statistics (admin only).

    Args:
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        User statistics
    """
    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(db)

        total_users = user_repo.count()
        active_users = len(user_repo.get_active_users())
        admin_users = user_repo.count_admins()
        user_users = total_users - admin_users

        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            admin_users=admin_users,
            user_users=user_users
        )

    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        ) from e


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def users_health_check():
    """
    Users service health check.

    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "users",
        "version": "1.0.0"
    }
