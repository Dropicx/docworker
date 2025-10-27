"""
Audit Logger Service

This service provides comprehensive audit logging for security events,
user actions, and system activities. It ensures compliance and security
monitoring by logging all significant events in the system.

Features:
- Structured logging with consistent format
- User action tracking
- Security event monitoring
- Performance metrics
- Compliance reporting
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.auth_models import AuditAction
from app.repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Centralized audit logging service for security and compliance.

    This service provides methods to log various types of events including
    authentication, authorization, data access, and system changes.
    """

    def __init__(self, db: Session):
        self.db = db
        self.audit_repo = AuditLogRepository(db)

    def log_auth_event(
        self,
        user_id: UUID | None,
        action: AuditAction,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any | None] = None
    ) -> None:
        """
        Log authentication-related events.

        Args:
            user_id: User ID (None for failed authentication)
            action: Authentication action type
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        if not settings.enable_audit_logging:
            return

        try:
            self.audit_repo.create_log(
                user_id=user_id,
                action=action,
                resource_type="authentication",
                resource_id=str(user_id) if user_id else "unknown",
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )

            logger.debug(f"Logged auth event: {action.value} for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log auth event {action.value}: {e}")

    def log_user_action(
        self,
        user_id: UUID,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any | None] = None
    ) -> None:
        """
        Log user actions and changes.

        Args:
            user_id: User performing the action
            action: Action type
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        if not settings.enable_audit_logging:
            return

        try:
            self.audit_repo.create_log(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )

            logger.debug(f"Logged user action: {action.value} by user {user_id}")
        except Exception as e:
            logger.error(f"Failed to log user action {action.value}: {e}")

    def log_security_event(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any | None] = None
    ) -> None:
        """
        Log security-related events.

        Args:
            action: Security action type
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            user_id: User involved (if any)
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        if not settings.enable_audit_logging:
            return

        try:
            self.audit_repo.create_log(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )

            logger.warning(f"Logged security event: {action.value}")
        except Exception as e:
            logger.error(f"Failed to log security event {action.value}: {e}")

    def log_system_event(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: str,
        details: dict[str, Any | None] = None
    ) -> None:
        """
        Log system-level events.

        Args:
            action: System action type
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            details: Additional event details
        """
        if not settings.enable_audit_logging:
            return

        try:
            self.audit_repo.create_log(
                user_id=None,  # System events have no user
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details
            )

            logger.info(f"Logged system event: {action.value}")
        except Exception as e:
            logger.error(f"Failed to log system event {action.value}: {e}")

    def log_permission_denied(
        self,
        user_id: UUID | None,
        permission: str,
        resource_type: str,
        resource_id: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log permission denied events.

        Args:
            user_id: User who was denied access
            permission: Permission that was denied
            resource_type: Type of resource
            resource_id: ID of resource
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_security_event(
            action=AuditAction.PERMISSION_DENIED,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"permission": permission}
        )

    def log_auth_failure(
        self,
        email: str | None,
        reason: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log authentication failure events.

        Args:
            email: Email that failed authentication
            reason: Reason for failure
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_security_event(
            action=AuditAction.AUTH_FAILURE,
            resource_type="authentication",
            resource_id=email or "unknown",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email, "reason": reason}
        )

    def log_rate_limit_exceeded(
        self,
        user_id: UUID | None,
        endpoint: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log rate limit exceeded events.

        Args:
            user_id: User who exceeded rate limit
            endpoint: Endpoint that was rate limited
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_security_event(
            action=AuditAction.RATE_LIMIT_EXCEEDED,
            resource_type="endpoint",
            resource_id=endpoint,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"endpoint": endpoint}
        )

    def log_user_login(
        self,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        login_method: str = "password"
    ) -> None:
        """
        Log user login events.

        Args:
            user_id: User who logged in
            ip_address: Client IP address
            user_agent: Client user agent
            login_method: Method used for login (password, api_key, etc.)
        """
        self.log_auth_event(
            user_id=user_id,
            action=AuditAction.USER_LOGIN,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"login_method": login_method}
        )

    def log_user_logout(
        self,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
        logout_all: bool = False
    ) -> None:
        """
        Log user logout events.

        Args:
            user_id: User who logged out
            ip_address: Client IP address
            user_agent: Client user agent
            logout_all: Whether all devices were logged out
        """
        self.log_auth_event(
            user_id=user_id,
            action=AuditAction.USER_LOGOUT,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"logout_all": logout_all}
        )

    def log_user_created(
        self,
        admin_user_id: UUID,
        created_user_id: UUID,
        created_user_email: str,
        role: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log user creation events.

        Args:
            admin_user_id: Admin who created the user
            created_user_id: ID of created user
            created_user_email: Email of created user
            role: Role assigned to created user
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=admin_user_id,
            action=AuditAction.USER_CREATED,
            resource_type="user",
            resource_id=str(created_user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "created_user_email": created_user_email,
                "role": role
            }
        )

    def log_user_updated(
        self,
        admin_user_id: UUID,
        updated_user_id: UUID,
        changes: dict[str, Any],
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log user update events.

        Args:
            admin_user_id: Admin who updated the user
            updated_user_id: ID of updated user
            changes: Dictionary of changes made
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=admin_user_id,
            action=AuditAction.USER_UPDATED,
            resource_type="user",
            resource_id=str(updated_user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details=changes
        )

    def log_user_deleted(
        self,
        admin_user_id: UUID,
        deleted_user_id: UUID,
        deleted_user_email: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log user deletion events.

        Args:
            admin_user_id: Admin who deleted the user
            deleted_user_id: ID of deleted user
            deleted_user_email: Email of deleted user
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=admin_user_id,
            action=AuditAction.USER_DELETED,
            resource_type="user",
            resource_id=str(deleted_user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"deleted_user_email": deleted_user_email}
        )

    def log_password_changed(
        self,
        user_id: UUID,
        changed_by_admin: bool = False,
        admin_user_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log password change events.

        Args:
            user_id: User whose password was changed
            changed_by_admin: Whether changed by admin
            admin_user_id: Admin who changed password (if applicable)
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=admin_user_id or user_id,
            action=AuditAction.PASSWORD_CHANGED,
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
            user_agent=user_agent,
            details={"changed_by_admin": changed_by_admin}
        )

    def log_api_key_created(
        self,
        user_id: UUID,
        key_id: str,
        key_name: str,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log API key creation events.

        Args:
            user_id: User who created the key
            key_id: ID of created key
            key_name: Name of created key
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=user_id,
            action=AuditAction.API_KEY_CREATED,
            resource_type="api_key",
            resource_id=key_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"key_name": key_name}
        )

    def log_api_key_revoked(
        self,
        user_id: UUID,
        key_id: str,
        revoked_by_admin: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log API key revocation events.

        Args:
            user_id: User who revoked the key (or admin)
            key_id: ID of revoked key
            revoked_by_admin: Whether revoked by admin
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=user_id,
            action=AuditAction.API_KEY_REVOKED,
            resource_type="api_key",
            resource_id=key_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"revoked_by_admin": revoked_by_admin}
        )

    def log_pipeline_config_changed(
        self,
        user_id: UUID,
        config_type: str,
        config_id: str,
        changes: dict[str, Any],
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log pipeline configuration changes.

        Args:
            user_id: User who made the change
            config_type: Type of configuration changed
            config_id: ID of configuration
            changes: Dictionary of changes made
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=user_id,
            action=AuditAction.PIPELINE_CONFIG_CHANGED,
            resource_type=config_type,
            resource_id=config_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=changes
        )

    def log_settings_update(
        self,
        user_id: UUID,
        setting_name: str,
        old_value: Any,
        new_value: Any,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Log settings update events.

        Args:
            user_id: User who updated the setting
            setting_name: Name of setting updated
            old_value: Previous value
            new_value: New value
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.log_user_action(
            user_id=user_id,
            action=AuditAction.SETTINGS_UPDATE,
            resource_type="setting",
            resource_id=setting_name,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "setting_name": setting_name,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )

    def get_audit_summary(
        self,
        hours: int = 24
    ) -> dict[str, Any]:
        """
        Get audit log summary for a time period.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with audit summary
        """
        try:
            return self.audit_repo.get_activity_summary(hours=hours)
        except Exception as e:
            logger.error(f"Failed to get audit summary: {e}")
            return {}

    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Clean up old audit logs.

        Args:
            days: Number of days to keep logs

        Returns:
            Number of logs cleaned up
        """
        try:
            return self.audit_repo.cleanup_old_logs(days=days)
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
            return 0


# Global audit logger instance (will be initialized with database session)
audit_logger: AuditLogger | None = None


def get_audit_logger(db: Session) -> AuditLogger:
    """
    Get audit logger instance.

    Args:
        db: Database session

    Returns:
        Audit logger instance
    """
    return AuditLogger(db)
