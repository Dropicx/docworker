"""
Authentication Service

This service provides business logic for user authentication, authorization,
and token management. It handles user creation, login, token refresh, and
password management with proper security measures.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_api_key,
    hash_api_key,
    verify_api_key
)
from app.core.config import settings
from app.database.auth_models import UserDB, UserRole, UserStatus, AuditAction
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.api_key_repository import APIKeyRepository
from app.repositories.audit_log_repository import AuditLogRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and user management operations."""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_token_repo = RefreshTokenRepository(db)
        self.api_key_repo = APIKeyRepository(db)
        self.audit_log_repo = AuditLogRepository(db)

    def create_user_by_admin(
        self,
        email: str,
        password: str,
        full_name: str,
        role: UserRole,
        created_by_admin_id: UUID
    ) -> UserDB:
        """
        Create a new user (admin-only operation).

        Args:
            email: User's email address
            password: Plain text password
            full_name: User's full name
            role: User role (USER or ADMIN)
            created_by_admin_id: ID of admin creating the user

        Returns:
            Created user instance

        Raises:
            ValueError: If email already exists or password is weak
        """
        try:
            # Validate email format
            if not email or "@" not in email:
                raise ValueError("Invalid email format")

            # Check if email already exists
            if self.user_repo.is_email_taken(email):
                raise ValueError(f"User with email {email} already exists")

            # Hash password
            password_hash = hash_password(password)

            # Create user
            user = self.user_repo.create_user(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                created_by_admin_id=created_by_admin_id
            )

            # Log user creation
            self.audit_log_repo.create_log(
                user_id=created_by_admin_id,
                action=AuditAction.USER_CREATED,
                resource_type="user",
                resource_id=str(user.id),
                details={"created_user_email": email, "role": role.value}
            )

            logger.info(f"Created user {email} with role {role} by admin {created_by_admin_id}")
            return user

        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise

    def authenticate_user(self, email: str, password: str, ip_address: str | None = None) -> UserDB | None:
        """
        Authenticate a user with email and password.

        Implements account lockout protection against brute force attacks.

        Args:
            email: User's email address
            password: Plain text password
            ip_address: IP address for audit logging

        Returns:
            User instance if authentication successful, None otherwise
        """
        try:
            # Get user by email
            user = self.user_repo.get_by_email(email)
            if not user:
                logger.warning(f"Authentication failed: user {email} not found")
                return None

            # Check if user is active
            if not user.is_active or user.status != UserStatus.ACTIVE:
                logger.warning(f"Authentication failed: user {email} is inactive")
                return None

            # Check if account is locked
            if self.user_repo.is_account_locked(user.id):
                logger.warning(f"Authentication failed: account {email} is locked")

                # Log lockout attempt
                self.audit_log_repo.create_log(
                    user_id=user.id,
                    action=AuditAction.AUTH_FAILURE,
                    resource_type="user",
                    resource_id=str(user.id),
                    ip_address=ip_address,
                    details={"reason": "account_locked", "locked_until": user.locked_until.isoformat() if user.locked_until else None}
                )

                return None

            # Verify password
            if not verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for {email}")

                # Increment failed login attempts
                failed_attempts = self.user_repo.increment_failed_attempts(user.id)

                # Log authentication failure
                self.audit_log_repo.create_log(
                    user_id=user.id,
                    action=AuditAction.AUTH_FAILURE,
                    resource_type="user",
                    resource_id=str(user.id),
                    ip_address=ip_address,
                    details={"reason": "invalid_password", "failed_attempts": failed_attempts}
                )

                # Check if should lock account
                if failed_attempts >= settings.max_login_attempts:
                    self.user_repo.lock_account(user.id, settings.account_lockout_minutes)

                    # Log account lockout
                    self.audit_log_repo.create_log(
                        user_id=user.id,
                        action=AuditAction.ACCOUNT_LOCKED,
                        resource_type="user",
                        resource_id=str(user.id),
                        ip_address=ip_address,
                        details={
                            "reason": "max_failed_attempts",
                            "failed_attempts": failed_attempts,
                            "lockout_minutes": settings.account_lockout_minutes
                        }
                    )

                    logger.warning(
                        f"Account {email} locked after {failed_attempts} failed attempts "
                        f"for {settings.account_lockout_minutes} minutes"
                    )

                return None

            # Password correct - reset failed attempts
            self.user_repo.reset_failed_attempts(user.id)

            # Update last login
            self.user_repo.update_last_login(user.id)

            # Log successful authentication
            self.audit_log_repo.create_log(
                user_id=user.id,
                action=AuditAction.USER_LOGIN,
                resource_type="user",
                resource_id=str(user.id),
                ip_address=ip_address
            )

            logger.info(f"User {email} authenticated successfully")
            return user

        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            return None

    def create_tokens(self, user: UserDB) -> dict[str, str]:
        """
        Create access and refresh tokens for a user.

        Args:
            user: User instance

        Returns:
            Dictionary with access_token and refresh_token
        """
        try:
            # Create access token
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role.value}
            )

            # Create refresh token
            refresh_token = create_refresh_token(str(user.id))

            # Hash refresh token for storage
            from app.core.security import hash_api_key
            refresh_token_hash = hash_api_key(refresh_token)

            # Store refresh token in database
            expires_at = datetime.now(datetime.UTC) + timedelta(days=7)  # 7 days
            self.refresh_token_repo.create_token(
                user_id=user.id,
                token_hash=refresh_token_hash,
                expires_at=expires_at
            )

            logger.debug(f"Created tokens for user {user.email}")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token
            }

        except Exception as e:
            logger.error(f"Error creating tokens for user {user.id}: {e}")
            raise

    def refresh_access_token(self, refresh_token: str) -> str | None:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            New access token if refresh successful, None otherwise
        """
        try:
            # Hash the refresh token to look it up
            from app.core.security import hash_api_key
            refresh_token_hash = hash_api_key(refresh_token)

            # Get refresh token from database
            stored_token = self.refresh_token_repo.get_by_hash(refresh_token_hash)
            if not stored_token:
                logger.warning("Refresh token not found in database")
                return None

            # Check if token is valid
            if not self.refresh_token_repo.is_token_valid(refresh_token_hash):
                logger.warning("Refresh token is revoked or expired")
                return None

            # Get user
            user = self.user_repo.get_by_id(stored_token.user_id)
            if not user or not user.is_active or user.status != UserStatus.ACTIVE:
                logger.warning("User not found or inactive")
                return None

            # Update last used timestamp
            self.refresh_token_repo.update_last_used(stored_token.id)

            # Create new access token
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email, "role": user.role.value}
            )

            logger.debug(f"Refreshed access token for user {user.email}")
            return access_token

        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """
        Revoke a refresh token (logout).

        Args:
            refresh_token: Refresh token string to revoke

        Returns:
            True if revoked successfully
        """
        try:
            # Hash the refresh token to look it up
            from app.core.security import hash_api_key
            refresh_token_hash = hash_api_key(refresh_token)

            # Revoke token
            success = self.refresh_token_repo.revoke_token_by_hash(refresh_token_hash)

            if success:
                logger.info("Refresh token revoked successfully")
            else:
                logger.warning("Refresh token not found for revocation")

            return success

        except Exception as e:
            logger.error(f"Error revoking refresh token: {e}")
            return False

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of tokens revoked
        """
        try:
            count = self.refresh_token_repo.revoke_all_user_tokens(user_id)
            logger.info(f"Revoked {count} refresh tokens for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error revoking all tokens for user {user_id}: {e}")
            raise

    def get_user_from_token(self, token: str) -> UserDB | None:
        """
        Get user from JWT access token.

        Args:
            token: JWT access token

        Returns:
            User instance if token is valid, None otherwise
        """
        try:
            # Verify token
            payload = verify_token(token, "access")
            user_id = payload.get("sub")

            if not user_id:
                return None

            # Get user
            user = self.user_repo.get_by_id(UUID(user_id))
            if not user or not user.is_active or user.status != UserStatus.ACTIVE:
                return None

            return user

        except Exception as e:
            logger.debug(f"Error getting user from token: {e}")
            return None

    def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        """
        Change user's password.

        Args:
            user_id: User's UUID
            old_password: Current password
            new_password: New password

        Returns:
            True if changed successfully
        """
        try:
            # Get user
            user = self.user_repo.get_by_id(user_id)
            if not user:
                return False

            # Verify old password
            if not verify_password(old_password, user.password_hash):
                logger.warning(f"Password change failed: invalid old password for user {user_id}")
                return False

            # Hash new password
            new_password_hash = hash_password(new_password)

            # Update password
            success = self.user_repo.change_password(user_id, new_password_hash)

            if success:
                # Revoke all refresh tokens for security
                self.revoke_all_user_tokens(user_id)

                # Log password change
                self.audit_log_repo.create_log(
                    user_id=user_id,
                    action=AuditAction.PASSWORD_CHANGED,
                    resource_type="user",
                    resource_id=str(user_id)
                )

                logger.info(f"Password changed for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            return False

    def create_api_key(
        self,
        user_id: UUID,
        name: str,
        expires_days: int | None = None
    ) -> tuple[str, str]:
        """
        Create an API key for a user.

        Args:
            user_id: User's UUID
            name: User-friendly name for the key
            expires_days: Days until expiration (None for no expiration)

        Returns:
            Tuple of (plain_key, key_id)
        """
        try:
            # Generate API key
            plain_key, key_hash = generate_api_key()

            # Set expiration
            expires_at = None
            if expires_days:
                expires_at = datetime.now(datetime.UTC) + timedelta(days=expires_days)

            # Create API key record
            api_key = self.api_key_repo.create_api_key(
                user_id=user_id,
                key_hash=key_hash,
                name=name,
                expires_at=expires_at
            )

            # Log API key creation
            self.audit_log_repo.create_log(
                user_id=user_id,
                action=AuditAction.API_KEY_CREATED,
                resource_type="api_key",
                resource_id=str(api_key.id),
                details={"key_name": name}
            )

            logger.info(f"Created API key '{name}' for user {user_id}")
            return plain_key, str(api_key.id)

        except Exception as e:
            logger.error(f"Error creating API key for user {user_id}: {e}")
            raise

    def verify_api_key(self, api_key: str) -> UserDB | None:
        """
        Verify an API key and return the associated user.

        Args:
            api_key: Plain API key string

        Returns:
            User instance if key is valid, None otherwise
        """
        try:
            # Hash the API key to look it up
            key_hash = hash_api_key(api_key)

            # Get API key record
            stored_key = self.api_key_repo.get_by_hash(key_hash)
            if not stored_key:
                return None

            # Check if key is active and not expired
            if not stored_key.is_active:
                return None

            if stored_key.expires_at and stored_key.expires_at < datetime.now(datetime.UTC):
                return None

            # Get user
            user = self.user_repo.get_by_id(stored_key.user_id)
            if not user or not user.is_active or user.status != UserStatus.ACTIVE:
                return None

            # Update usage statistics
            self.api_key_repo.update_usage(stored_key.id)

            return user

        except Exception as e:
            logger.error(f"Error verifying API key: {e}")
            return None

    def revoke_api_key(self, key_id: str, user_id: UUID) -> bool:
        """
        Revoke an API key.

        Args:
            key_id: API key UUID
            user_id: User's UUID (for authorization)

        Returns:
            True if revoked successfully
        """
        try:
            # Get API key
            api_key = self.api_key_repo.get_by_id(UUID(key_id))
            if not api_key or api_key.user_id != user_id:
                return False

            # Revoke key
            success = self.api_key_repo.revoke_key(UUID(key_id))

            if success:
                # Log API key revocation
                self.audit_log_repo.create_log(
                    user_id=user_id,
                    action=AuditAction.API_KEY_REVOKED,
                    resource_type="api_key",
                    resource_id=key_id
                )

                logger.info(f"Revoked API key {key_id} for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error revoking API key {key_id}: {e}")
            return False

    def get_user_api_keys(self, user_id: UUID) -> list:
        """
        Get all API keys for a user.

        Args:
            user_id: User's UUID

        Returns:
            List of API key records (without key values)
        """
        try:
            return self.api_key_repo.get_by_user(user_id)
        except Exception as e:
            logger.error(f"Error getting API keys for user {user_id}: {e}")
            raise

    def cleanup_expired_tokens(self) -> int:
        """
        Clean up expired refresh tokens.

        Returns:
            Number of tokens cleaned up
        """
        try:
            return self.refresh_token_repo.cleanup_expired_tokens()
        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")
            raise

    def cleanup_expired_api_keys(self) -> int:
        """
        Clean up expired API keys.

        Returns:
            Number of keys cleaned up
        """
        try:
            return self.api_key_repo.cleanup_expired_keys()
        except Exception as e:
            logger.error(f"Error cleaning up expired API keys: {e}")
            raise
