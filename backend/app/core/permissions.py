"""
Permission System

This module provides role-based access control (RBAC) for the DocTranslator system.
It defines roles, permissions, and FastAPI dependencies for protecting endpoints.

Access Model:
- Public: No authentication required (document upload, status check, results)
- User: Authentication required (pipeline configuration, own API keys)
- Admin: Full access (user management, all configurations, audit logs)
"""

from enum import Enum
import logging
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.auth_models import UserDB
from app.database.connection import get_session
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class Role(str, Enum):
    """User roles for RBAC"""
    USER = "user"    # Can manage pipeline configurations
    ADMIN = "admin"  # Can manage users and all configurations


class Permission(str, Enum):
    """Fine-grained permissions"""
    # Document permissions (public - no auth required)
    DOCUMENT_UPLOAD = "document:upload"
    DOCUMENT_STATUS = "document:status"
    DOCUMENT_RESULTS = "document:results"

    # Pipeline permissions (User + Admin)
    PIPELINE_READ = "pipeline:read"
    PIPELINE_WRITE = "pipeline:write"
    PROMPTS_READ = "prompts:read"
    PROMPTS_WRITE = "prompts:write"
    OCR_CONFIG_READ = "ocr_config:read"
    OCR_CONFIG_WRITE = "ocr_config:write"
    MODELS_READ = "models:read"
    DOCUMENT_CLASSES_READ = "document_classes:read"

    # Settings permissions (User + Admin)
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"

    # API key permissions (User + Admin for own keys)
    API_KEY_CREATE = "api_key:create"
    API_KEY_READ = "api_key:read"
    API_KEY_DELETE = "api_key:delete"

    # User management permissions (Admin only)
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"

    # Admin permissions (Admin only)
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    API_KEY_MANAGE_ALL = "api_key:manage_all"
    SYSTEM_CONFIG = "system:config"


# Define USER permissions first to avoid circular reference
USER_PERMISSIONS = [
    # Document access (public endpoints work without auth, but users can also access)
    Permission.DOCUMENT_UPLOAD,
    Permission.DOCUMENT_STATUS,
    Permission.DOCUMENT_RESULTS,

    # Pipeline configuration
    Permission.PIPELINE_READ,
    Permission.PIPELINE_WRITE,
    Permission.PROMPTS_READ,
    Permission.PROMPTS_WRITE,
    Permission.OCR_CONFIG_READ,
    Permission.OCR_CONFIG_WRITE,
    Permission.MODELS_READ,
    Permission.DOCUMENT_CLASSES_READ,

    # Settings access
    Permission.SETTINGS_READ,
    Permission.SETTINGS_WRITE,

    # Own API keys
    Permission.API_KEY_CREATE,
    Permission.API_KEY_READ,
    Permission.API_KEY_DELETE,
]

# Role-permission mapping
ROLE_PERMISSIONS = {
    Role.USER: USER_PERMISSIONS,
    Role.ADMIN: [
        # All USER permissions
        *USER_PERMISSIONS,

        # User management
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_LIST,

        # Admin functions
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.API_KEY_MANAGE_ALL,
        Permission.SYSTEM_CONFIG,
    ],
}


def has_permission(user: UserDB, permission: Permission) -> bool:
    """
    Check if a user has a specific permission.

    Args:
        user: User instance
        permission: Permission to check

    Returns:
        True if user has permission
    """
    if not user or not user.is_active:
        return False

    user_permissions = ROLE_PERMISSIONS.get(user.role, [])
    return permission in user_permissions


def has_role(user: UserDB, role: Role) -> bool:
    """
    Check if a user has a specific role.

    Args:
        user: User instance
        role: Role to check

    Returns:
        True if user has role
    """
    if not user or not user.is_active:
        return False

    return user.role == role


def has_any_role(user: UserDB, roles: list[Role]) -> bool:
    """
    Check if a user has any of the specified roles.

    Args:
        user: User instance
        roles: List of roles to check

    Returns:
        True if user has any of the roles
    """
    if not user or not user.is_active:
        return False

    return user.role in roles


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_session)
) -> UserDB | None:
    """
    Get current user from JWT token (optional - returns None if no token).

    Used for endpoints that can work with or without authentication.

    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session

    Returns:
        User instance if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        auth_service = AuthService(db)
        return auth_service.get_user_from_token(credentials.credentials)
    except Exception:
        return None


async def get_current_user_required(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session)
) -> UserDB:
    """
    Get current user from JWT token (required - raises exception if no token).

    Used for protected endpoints that require authentication.

    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session

    Returns:
        User instance

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_service = AuthService(db)
        user = auth_service.get_user_from_token(credentials.credentials)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_from_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_session)
) -> UserDB | None:
    """
    Get current user from API key (optional).

    Used for endpoints that support both JWT and API key authentication.

    Args:
        request: FastAPI request object
        credentials: Authorization credentials
        db: Database session

    Returns:
        User instance if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        auth_service = AuthService(db)

        # Try API key first
        user = auth_service.verify_api_key(credentials.credentials)
        if user:
            return user

        # Fall back to JWT token
        return auth_service.get_user_from_token(credentials.credentials)
    except Exception:
        return None


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission.

    Args:
        permission: Required permission

    Returns:
        FastAPI dependency function
    """
    async def permission_checker(
        current_user: UserDB = Depends(get_current_user_required)
    ) -> UserDB:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission.value}' required"
            )
        return current_user

    return permission_checker


def require_role(role: Role):
    """
    Decorator to require a specific role.

    Args:
        role: Required role

    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: UserDB = Depends(get_current_user_required)
    ) -> UserDB:
        if not has_role(current_user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' required"
            )
        return current_user

    return role_checker


def require_any_role(roles: list[Role]):
    """
    Decorator to require any of the specified roles.

    Args:
        roles: List of required roles

    Returns:
        FastAPI dependency function
    """
    async def role_checker(
        current_user: UserDB = Depends(get_current_user_required)
    ) -> UserDB:
        if not has_any_role(current_user, roles):
            role_names = [role.value for role in roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {', '.join(role_names)}"
            )
        return current_user

    return role_checker


def require_admin():
    """
    Decorator to require admin role.

    Returns:
        FastAPI dependency function
    """
    return require_role(Role.ADMIN)


def require_user_or_admin():
    """
    Decorator to require user or admin role.

    Returns:
        FastAPI dependency function
    """
    return require_any_role([Role.USER, Role.ADMIN])


# Convenience dependencies for common use cases
CurrentUserOptional = Depends(get_current_user_optional)
CurrentUserRequired = Depends(get_current_user_required)
CurrentUserFromAPIKey = Depends(get_current_user_from_api_key)

# Permission-based dependencies
RequirePipelineRead = require_permission(Permission.PIPELINE_READ)
RequirePipelineWrite = require_permission(Permission.PIPELINE_WRITE)
RequireSettingsRead = require_permission(Permission.SETTINGS_READ)
RequireSettingsWrite = require_permission(Permission.SETTINGS_WRITE)
RequireUserManagement = require_permission(Permission.USER_CREATE)
RequireAuditAccess = require_permission(Permission.AUDIT_READ)

# Role-based dependencies
RequireAdmin = require_admin()
RequireUserOrAdmin = require_user_or_admin()


def check_resource_access(user: UserDB, resource_user_id: UUID) -> bool:
    """
    Check if user can access a resource owned by another user.

    Args:
        user: Current user
        resource_user_id: User ID who owns the resource

    Returns:
        True if user can access the resource
    """
    # Users can only access their own resources
    # Admins can access all resources
    if user.role == Role.ADMIN:
        return True

    return user.id == resource_user_id


def require_resource_access(resource_user_id: UUID):
    """
    Decorator to require access to a resource owned by a specific user.

    Args:
        resource_user_id: User ID who owns the resource

    Returns:
        FastAPI dependency function
    """
    async def resource_checker(
        current_user: UserDB = Depends(get_current_user_required)
    ) -> UserDB:
        if not check_resource_access(current_user, resource_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this resource"
            )
        return current_user

    return resource_checker


def log_permission_denied(
    user: UserDB | None,
    permission: Permission,
    request: Request
) -> None:
    """
    Log a permission denied event.

    Args:
        user: User who was denied access (None if not authenticated)
        permission: Permission that was denied
        request: FastAPI request object
    """
    try:
        db = next(get_session())
        audit_repo = AuditLogRepository(db)

        audit_repo.create_log(
            user_id=user.id if user else None,
            action="PERMISSION_DENIED",
            resource_type="permission",
            resource_id=permission.value,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"permission": permission.value}
        )
    except Exception as e:
        logger.error(f"Error logging permission denied: {e}")


def log_auth_failure(
    email: str | None,
    request: Request,
    reason: str = "invalid_credentials"
) -> None:
    """
    Log an authentication failure.

    Args:
        email: Email that failed authentication
        request: FastAPI request object
        reason: Reason for failure
    """
    try:
        db = next(get_session())
        audit_repo = AuditLogRepository(db)

        audit_repo.create_log(
            user_id=None,
            action="AUTH_FAILURE",
            resource_type="authentication",
            resource_id=email or "unknown",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"email": email, "reason": reason}
        )
    except Exception as e:
        logger.error(f"Error logging auth failure: {e}")
