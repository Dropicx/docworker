"""
User Repository

Provides data access methods for user management including CRUD operations,
authentication queries, and user status management.

Includes transparent encryption for email and full_name fields.
"""

from datetime import datetime, timezone
import logging
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database.auth_models import UserDB, UserRole, UserStatus
from app.repositories.base_repository import BaseRepository, EncryptedRepositoryMixin

logger = logging.getLogger(__name__)


class UserRepository(EncryptedRepositoryMixin, BaseRepository[UserDB]):
    """
    Repository for user data access operations.

    Encrypted fields: email, full_name
    Note: get_by_email() will need email_searchable hash field in Phase 3.

    IMPORTANT: EncryptedRepositoryMixin must come FIRST in inheritance order
    so that its create()/update()/get*() methods override BaseRepository methods.
    """

    # Define fields to encrypt
    encrypted_fields = ["email", "full_name"]

    def __init__(self, db: Session):
        super().__init__(db, UserDB)

    def get_by_email(self, email: str) -> UserDB | None:
        """
        Get user by email address using searchable hash for efficient lookup.

        Uses email_searchable hash column to find user without decrypting
        all emails in the database. Falls back to plaintext search for legacy users.

        Args:
            email: User's email address (plaintext)

        Returns:
            User instance with decrypted fields, or None if not found
        """
        from app.core.encryption import encryptor

        try:
            # Generate hash from plaintext email for lookup
            email_hash = encryptor.generate_searchable_hash(email)

            # Query using searchable hash (much faster than decrypting all emails)
            user = self.db.query(UserDB).filter(UserDB.email_searchable == email_hash).first()

            if user:
                # Decrypt and return (handled by EncryptedRepositoryMixin)
                return self._decrypt_entity(user)

            # FALLBACK: Search by plaintext email for legacy users (backward compatibility)
            # This handles users created before encryption was enabled
            logger.info(f"Hash lookup failed for {email}, trying plaintext fallback")
            user = self.db.query(UserDB).filter(UserDB.email == email).first()

            if user:
                logger.info(f"Found legacy user {user.id}, migrating to encrypted storage")
                # Auto-migrate: Encrypt the user's data on login
                try:
                    encrypted_email = encryptor.encrypt_field(email)
                    encrypted_full_name = encryptor.encrypt_field(user.full_name)

                    user.email = encrypted_email
                    user.full_name = encrypted_full_name
                    user.email_searchable = email_hash
                    user.full_name_searchable = encryptor.generate_searchable_hash(user.full_name)
                    user.encryption_version = 1

                    self.db.commit()
                    logger.info(f"Successfully migrated user {user.id} to encrypted storage")
                except Exception as encrypt_error:
                    logger.error(f"Failed to auto-migrate user {user.id}: {encrypt_error}")
                    self.db.rollback()
                    # Still return the user even if migration fails (don't block login)

            # Decrypt and return (handled by EncryptedRepositoryMixin)
            return self._decrypt_entity(user)

        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            raise

    def get_by_id(self, user_id: UUID) -> UserDB | None:
        """
        Get user by UUID.

        Args:
            user_id: User's UUID

        Returns:
            User instance or None if not found
        """
        return super().get_by_id(user_id)

    def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        role: UserRole = UserRole.USER,
        created_by_admin_id: UUID | None = None,
    ) -> UserDB:
        """
        Create a new user.

        Args:
            email: User's email address
            password_hash: Hashed password
            full_name: User's full name
            role: User role (USER or ADMIN)
            created_by_admin_id: ID of admin who created this user

        Returns:
            Created user instance

        Raises:
            ValueError: If email already exists
        """
        try:
            # Check if email already exists
            if self.get_by_email(email):
                raise ValueError(f"User with email {email} already exists")

            user = self.create(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                created_by_admin_id=created_by_admin_id,
                status=UserStatus.ACTIVE,
                is_active=True,
                is_verified=True,
            )

            logger.info("Created user {email} with role {role}")
            return user
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise

    def update_last_login(self, user_id: UUID) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User's UUID

        Returns:
            True if updated successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            user.last_login_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.debug(f"Updated last login for user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last login for user {user_id}: {e}")
            raise

    def activate_user(self, user_id: UUID) -> bool:
        """
        Activate a user account.

        Args:
            user_id: User's UUID

        Returns:
            True if activated successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            user.is_active = True
            user.status = UserStatus.ACTIVE
            self.db.commit()

            logger.info(f"Activated user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error activating user {user_id}: {e}")
            raise

    def deactivate_user(self, user_id: UUID) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User's UUID

        Returns:
            True if deactivated successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            user.is_active = False
            user.status = UserStatus.INACTIVE
            self.db.commit()

            logger.info(f"Deactivated user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deactivating user {user_id}: {e}")
            raise

    def change_password(self, user_id: UUID, new_password_hash: str) -> bool:
        """
        Change user's password.

        Args:
            user_id: User's UUID
            new_password_hash: New hashed password

        Returns:
            True if changed successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            user.password_hash = new_password_hash
            self.db.commit()

            logger.info(f"Changed password for user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error changing password for user {user_id}: {e}")
            raise

    def update_role(self, user_id: UUID, new_role: UserRole) -> bool:
        """
        Update user's role.

        Args:
            user_id: User's UUID
            new_role: New user role

        Returns:
            True if updated successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            user.role = new_role
            self.db.commit()

            logger.info(f"Updated role for user {user_id} to {new_role}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating role for user {user_id}: {e}")
            raise

    def list_all_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role_filter: UserRole | None = None,
        status_filter: UserStatus | None = None,
    ) -> list[UserDB]:
        """
        List all users with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role_filter: Filter by user role
            status_filter: Filter by user status

        Returns:
            List of user instances with decrypted fields
        """
        try:
            query = self.db.query(UserDB)

            if role_filter:
                query = query.filter(UserDB.role == role_filter)

            if status_filter:
                query = query.filter(UserDB.status == status_filter)

            users = query.offset(skip).limit(limit).all()
            # Decrypt encrypted fields before returning
            return self._decrypt_entities(users)
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise

    def get_active_users(self) -> list[UserDB]:
        """
        Get all active users.

        Returns:
            List of active user instances with decrypted fields
        """
        try:
            users = (
                self.db.query(UserDB)
                .filter(and_(UserDB.is_active, UserDB.status == UserStatus.ACTIVE))
                .all()
            )
            # Decrypt encrypted fields before returning
            return self._decrypt_entities(users)
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            raise

    def get_admins(self) -> list[UserDB]:
        """
        Get all admin users.

        Returns:
            List of admin user instances with decrypted fields
        """
        try:
            users = (
                self.db.query(UserDB)
                .filter(
                    and_(
                        UserDB.role == UserRole.ADMIN,
                        UserDB.is_active,
                        UserDB.status == UserStatus.ACTIVE,
                    )
                )
                .all()
            )
            # Decrypt encrypted fields before returning
            return self._decrypt_entities(users)
        except Exception as e:
            logger.error(f"Error getting admin users: {e}")
            raise

    def count_admins(self) -> int:
        """
        Count active admin users.

        Returns:
            Number of active admin users
        """
        try:
            return (
                self.db.query(UserDB)
                .filter(
                    and_(
                        UserDB.role == UserRole.ADMIN,
                        UserDB.is_active,
                        UserDB.status == UserStatus.ACTIVE,
                    )
                )
                .count()
            )
        except Exception as e:
            logger.error(f"Error counting admin users: {e}")
            raise

    def search_users(self, search_term: str, limit: int = 50) -> list[UserDB]:
        """
        Search users by email or full name.

        Note: With encrypted fields, LIKE search doesn't work on encrypted data.
        This method returns all users and filters in-memory after decryption.
        For large user bases, consider implementing hash-based search.

        Args:
            search_term: Search term
            limit: Maximum number of results

        Returns:
            List of matching user instances with decrypted fields
        """
        try:
            # Get all users (with decryption)
            all_users = self.db.query(UserDB).all()
            decrypted_users = self._decrypt_entities(all_users)

            # Filter in-memory after decryption
            search_lower = search_term.lower()
            matching_users = [
                user for user in decrypted_users
                if (user.email and search_lower in user.email.lower()) or
                   (user.full_name and search_lower in user.full_name.lower())
            ]

            return matching_users[:limit]
        except Exception as e:
            logger.error(f"Error searching users with term '{search_term}': {e}")
            raise

    def get_users_created_by_admin(self, admin_id: UUID) -> list[UserDB]:
        """
        Get all users created by a specific admin.

        Args:
            admin_id: Admin's UUID

        Returns:
            List of users created by the admin with decrypted fields
        """
        try:
            users = self.db.query(UserDB).filter(UserDB.created_by_admin_id == admin_id).all()
            # Decrypt encrypted fields before returning
            return self._decrypt_entities(users)
        except Exception as e:
            logger.error(f"Error getting users created by admin {admin_id}: {e}")
            raise

    def soft_delete_user(self, user_id: UUID) -> bool:
        """
        Soft delete a user (deactivate instead of hard delete).

        Args:
            user_id: User's UUID

        Returns:
            True if deactivated successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            # Soft delete by deactivating
            user.is_active = False
            user.status = UserStatus.INACTIVE
            self.db.commit()

            logger.info(f"Soft deleted user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error soft deleting user {user_id}: {e}")
            raise

    def is_email_taken(self, email: str, exclude_user_id: UUID | None = None) -> bool:
        """
        Check if email is already taken by another user.

        Uses searchable hash for encrypted email lookup.

        Args:
            email: Email to check
            exclude_user_id: User ID to exclude from check (for updates)

        Returns:
            True if email is taken by another user
        """
        from app.core.encryption import encryptor

        try:
            # Generate hash from plaintext email for lookup
            email_hash = encryptor.generate_searchable_hash(email)

            # Query using searchable hash
            query = self.db.query(UserDB).filter(UserDB.email_searchable == email_hash)

            if exclude_user_id:
                query = query.filter(UserDB.id != exclude_user_id)

            result = query.first()
            if result:
                return True

            # FALLBACK: Check plaintext email for legacy users without searchable hash
            query = self.db.query(UserDB).filter(UserDB.email == email)

            if exclude_user_id:
                query = query.filter(UserDB.id != exclude_user_id)

            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking if email {email} is taken: {e}")
            raise

    # Account lockout methods for brute force prevention

    def increment_failed_attempts(self, user_id: UUID) -> int:
        """
        Increment failed login attempts counter.

        Args:
            user_id: User's UUID

        Returns:
            New failed attempts count
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return 0

            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            self.db.commit()

            logger.warning(f"Failed login attempt #{user.failed_login_attempts} for user {user_id}")
            return user.failed_login_attempts
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error incrementing failed attempts for user {user_id}: {e}")
            raise

    def reset_failed_attempts(self, user_id: UUID) -> bool:
        """
        Reset failed login attempts counter.

        Args:
            user_id: User's UUID

        Returns:
            True if reset successfully
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            user.failed_login_attempts = 0
            user.locked_until = None
            self.db.commit()

            logger.debug(f"Reset failed attempts for user {user_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error resetting failed attempts for user {user_id}: {e}")
            raise

    def lock_account(self, user_id: UUID, minutes: int = 15) -> bool:
        """
        Lock user account for specified duration.

        Args:
            user_id: User's UUID
            minutes: Lockout duration in minutes

        Returns:
            True if locked successfully
        """
        try:
            from datetime import timedelta

            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                return False

            lockout_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
            user.locked_until = lockout_time
            self.db.commit()

            logger.warning(f"Locked account {user_id} until {lockout_time}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error locking account {user_id}: {e}")
            raise

    def is_account_locked(self, user_id: UUID) -> bool:
        """
        Check if account is currently locked.

        Args:
            user_id: User's UUID

        Returns:
            True if account is locked
        """
        try:
            # Query directly to get session-attached entity (no decryption needed)
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user or not user.locked_until:
                return False

            # Check if lockout has expired
            if user.locked_until <= datetime.now(timezone.utc):
                # Lockout expired, reset it
                user.locked_until = None
                user.failed_login_attempts = 0
                self.db.commit()
                logger.info(f"Lockout expired for user {user_id}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error checking if account {user_id} is locked: {e}")
            raise
