"""
User Repository

Provides data access methods for user management including CRUD operations,
authentication queries, and user status management.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.auth_models import UserDB, UserRole, UserStatus
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[UserDB]):
    """Repository for user data access operations."""

    def __init__(self, db: Session):
        super().__init__(db, UserDB)

    def get_by_email(self, email: str) -> Optional[UserDB]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User instance or None if not found
        """
        try:
            return self.db.query(UserDB).filter(UserDB.email == email).first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            raise

    def get_by_id(self, user_id: UUID) -> Optional[UserDB]:
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
        created_by_admin_id: Optional[UUID] = None
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
                is_verified=True
            )
            
            logger.info(f"Created user {email} with role {role}")
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
            user = self.get_by_id(user_id)
            if not user:
                return False
            
            user.last_login_at = datetime.utcnow()
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
            user = self.get_by_id(user_id)
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
            user = self.get_by_id(user_id)
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
            user = self.get_by_id(user_id)
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
            user = self.get_by_id(user_id)
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
        role_filter: Optional[UserRole] = None,
        status_filter: Optional[UserStatus] = None
    ) -> List[UserDB]:
        """
        List all users with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role_filter: Filter by user role
            status_filter: Filter by user status
            
        Returns:
            List of user instances
        """
        try:
            query = self.db.query(UserDB)
            
            if role_filter:
                query = query.filter(UserDB.role == role_filter)
            
            if status_filter:
                query = query.filter(UserDB.status == status_filter)
            
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise

    def get_active_users(self) -> List[UserDB]:
        """
        Get all active users.
        
        Returns:
            List of active user instances
        """
        try:
            return self.db.query(UserDB).filter(
                and_(UserDB.is_active == True, UserDB.status == UserStatus.ACTIVE)
            ).all()
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            raise

    def get_admins(self) -> List[UserDB]:
        """
        Get all admin users.
        
        Returns:
            List of admin user instances
        """
        try:
            return self.db.query(UserDB).filter(
                and_(
                    UserDB.role == UserRole.ADMIN,
                    UserDB.is_active == True,
                    UserDB.status == UserStatus.ACTIVE
                )
            ).all()
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
            return self.db.query(UserDB).filter(
                and_(
                    UserDB.role == UserRole.ADMIN,
                    UserDB.is_active == True,
                    UserDB.status == UserStatus.ACTIVE
                )
            ).count()
        except Exception as e:
            logger.error(f"Error counting admin users: {e}")
            raise

    def search_users(self, search_term: str, limit: int = 50) -> List[UserDB]:
        """
        Search users by email or full name.
        
        Args:
            search_term: Search term
            limit: Maximum number of results
            
        Returns:
            List of matching user instances
        """
        try:
            search_pattern = f"%{search_term}%"
            return self.db.query(UserDB).filter(
                or_(
                    UserDB.email.ilike(search_pattern),
                    UserDB.full_name.ilike(search_pattern)
                )
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching users with term '{search_term}': {e}")
            raise

    def get_users_created_by_admin(self, admin_id: UUID) -> List[UserDB]:
        """
        Get all users created by a specific admin.
        
        Args:
            admin_id: Admin's UUID
            
        Returns:
            List of users created by the admin
        """
        try:
            return self.db.query(UserDB).filter(
                UserDB.created_by_admin_id == admin_id
            ).all()
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
            user = self.get_by_id(user_id)
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

    def is_email_taken(self, email: str, exclude_user_id: Optional[UUID] = None) -> bool:
        """
        Check if email is already taken by another user.
        
        Args:
            email: Email to check
            exclude_user_id: User ID to exclude from check (for updates)
            
        Returns:
            True if email is taken by another user
        """
        try:
            query = self.db.query(UserDB).filter(UserDB.email == email)
            
            if exclude_user_id:
                query = query.filter(UserDB.id != exclude_user_id)
            
            return query.first() is not None
        except Exception as e:
            logger.error(f"Error checking if email {email} is taken: {e}")
            raise
