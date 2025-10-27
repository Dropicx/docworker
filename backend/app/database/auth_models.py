"""
Authentication Database Models

This module contains database models for user authentication, authorization,
and audit logging. These models support the enterprise-grade security system
with JWT tokens, role-based access control, and comprehensive audit trails.
"""

from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, Enum):
    """User role enumeration for RBAC"""
    USER = "user"    # Can manage pipeline configurations
    ADMIN = "admin"  # Can manage users and all configurations


class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"  # For future email verification


class UserDB(Base):
    """
    User accounts with role-based access control.

    Supports both USER and ADMIN roles with different permission levels.
    Users are created by admins only (no public registration).
    """

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # User information
    full_name = Column(String(255), nullable=False)

    # Role and status (use values_callable to store enum values, not names)
    role = Column(SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]), nullable=False, default=UserRole.USER)
    status = Column(SQLEnum(UserStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=UserStatus.ACTIVE)

    # Account tracking
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)  # Skip email verification for now

    # Account lockout (brute force prevention)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Admin tracking
    created_by_admin_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Relationships
    created_by_admin = relationship("UserDB", remote_side=[id], backref="created_users")
    refresh_tokens = relationship("RefreshTokenDB", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKeyDB", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogDB", back_populates="user")

    # Indexes
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_status", "status"),
        Index("idx_users_created_by", "created_by_admin_id"),
        Index("idx_users_locked_until", "locked_until"),
    )

    def __repr__(self):
        return f"<UserDB(id='{self.id}', email='{self.email}', role='{self.role}')>"


class RefreshTokenDB(Base):
    """
    Refresh token storage for JWT token management.

    Stores hashed refresh tokens with expiration and revocation support.
    Used for secure token refresh without re-authentication.
    """

    __tablename__ = "refresh_tokens"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Token information
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Expiration and status
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("UserDB", back_populates="refresh_tokens")

    # Indexes
    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
        Index("idx_refresh_tokens_expires", "expires_at"),
        Index("idx_refresh_tokens_revoked", "is_revoked"),
    )

    def __repr__(self):
        return f"<RefreshTokenDB(id='{self.id}', user_id='{self.user_id}', expires='{self.expires_at}')>"


class APIKeyDB(Base):
    """
    API key management for programmatic access.

    Supports HMAC-hashed storage, expiration, and usage tracking.
    Can be used for both public and authenticated endpoints.
    """

    __tablename__ = "api_keys"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Key information
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)  # User-friendly name for identification
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status and expiration
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)  # NULL means no expiration

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True, index=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("UserDB", back_populates="api_keys")

    # Indexes
    __table_args__ = (
        Index("idx_api_keys_user", "user_id"),
        Index("idx_api_keys_active", "is_active"),
        Index("idx_api_keys_expires", "expires_at"),
        Index("idx_api_keys_last_used", "last_used_at"),
    )

    def __repr__(self):
        return f"<APIKeyDB(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"


class AuditAction(str, Enum):
    """Audit action types for comprehensive logging"""
    # Authentication actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_UPDATED = "user_updated"
    PASSWORD_CHANGED = "password_changed"

    # Pipeline configuration actions
    PIPELINE_CONFIG_CHANGED = "pipeline_config_changed"
    PROMPT_UPDATED = "prompt_updated"
    OCR_CONFIG_CHANGED = "ocr_config_changed"
    MODEL_CONFIG_CHANGED = "model_config_changed"

    # API key actions
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_USED = "api_key_used"

    # System actions
    SETTINGS_UPDATE = "settings_update"
    FEATURE_FLAG_CHANGED = "feature_flag_changed"

    # Security actions
    PERMISSION_DENIED = "permission_denied"
    AUTH_FAILURE = "auth_failure"
    ACCOUNT_LOCKED = "account_locked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Note: Public document uploads are NOT logged for privacy


class AuditLogDB(Base):
    """
    Comprehensive audit trail for security and compliance.

    Logs all admin and user actions (not public actions) for:
    - Security monitoring
    - Compliance requirements
    - Debugging and troubleshooting
    - User activity tracking
    """

    __tablename__ = "audit_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # User information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True, index=True)  # e.g., "pipeline_step", "user", "api_key"
    resource_id = Column(String(255), nullable=True, index=True)  # ID of the affected resource

    # Request context
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)

    # Additional context
    details = Column(Text, nullable=True)  # JSON string with additional context

    # Timestamp
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    user = relationship("UserDB", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_logs_user", "user_id"),
        Index("idx_audit_logs_action", "action"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_ip", "ip_address"),
    )

    def __repr__(self):
        return f"<AuditLogDB(id='{self.id}', action='{self.action}', user_id='{self.user_id}')>"
