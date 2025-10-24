"""
API Key Repository

Provides data access methods for API key management including creation,
validation, usage tracking, and cleanup operations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database.auth_models import APIKeyDB
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class APIKeyRepository(BaseRepository[APIKeyDB]):
    """Repository for API key data access operations."""

    def __init__(self, db: Session):
        super().__init__(db, APIKeyDB)

    def create_api_key(
        self,
        user_id: UUID,
        key_hash: str,
        name: str,
        expires_at: Optional[datetime] = None
    ) -> APIKeyDB:
        """
        Create a new API key.
        
        Args:
            user_id: User who owns the API key
            key_hash: Hashed API key value
            name: User-friendly name for the key
            expires_at: Optional expiration date
            
        Returns:
            Created API key instance
        """
        try:
            api_key = self.create(
                user_id=user_id,
                key_hash=key_hash,
                name=name,
                expires_at=expires_at,
                is_active=True,
                usage_count=0
            )
            
            logger.info(f"Created API key '{name}' for user {user_id}")
            return api_key
        except Exception as e:
            logger.error(f"Error creating API key for user {user_id}: {e}")
            raise

    def get_by_hash(self, key_hash: str) -> Optional[APIKeyDB]:
        """
        Get API key by its hash.
        
        Args:
            key_hash: Hashed API key value
            
        Returns:
            API key instance or None if not found
        """
        try:
            return self.db.query(APIKeyDB).filter(APIKeyDB.key_hash == key_hash).first()
        except Exception as e:
            logger.error(f"Error getting API key by hash: {e}")
            raise

    def get_by_user(self, user_id: UUID) -> List[APIKeyDB]:
        """
        Get all API keys for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of user's API keys
        """
        try:
            return self.db.query(APIKeyDB).filter(APIKeyDB.user_id == user_id).all()
        except Exception as e:
            logger.error(f"Error getting API keys for user {user_id}: {e}")
            raise

    def get_active_by_user(self, user_id: UUID) -> List[APIKeyDB]:
        """
        Get active API keys for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of active API keys
        """
        try:
            return self.db.query(APIKeyDB).filter(
                and_(
                    APIKeyDB.user_id == user_id,
                    APIKeyDB.is_active == True
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting active API keys for user {user_id}: {e}")
            raise

    def get_all_active(self, skip: int = 0, limit: int = 100) -> List[APIKeyDB]:
        """
        Get all active API keys across all users.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active API keys
        """
        try:
            return self.db.query(APIKeyDB).filter(
                APIKeyDB.is_active == True
            ).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all active API keys: {e}")
            raise

    def update_usage(self, key_id: UUID) -> bool:
        """
        Update API key usage statistics.
        
        Args:
            key_id: API key UUID
            
        Returns:
            True if updated successfully
        """
        try:
            api_key = self.get_by_id(key_id)
            if not api_key:
                return False
            
            api_key.last_used_at = datetime.utcnow()
            api_key.usage_count += 1
            self.db.commit()
            
            logger.debug(f"Updated usage for API key {key_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating usage for API key {key_id}: {e}")
            raise

    def revoke_key(self, key_id: UUID) -> bool:
        """
        Revoke an API key (soft delete).
        
        Args:
            key_id: API key UUID
            
        Returns:
            True if revoked successfully
        """
        try:
            api_key = self.get_by_id(key_id)
            if not api_key:
                return False
            
            api_key.is_active = False
            self.db.commit()
            
            logger.info(f"Revoked API key {key_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revoking API key {key_id}: {e}")
            raise

    def activate_key(self, key_id: UUID) -> bool:
        """
        Reactivate a revoked API key.
        
        Args:
            key_id: API key UUID
            
        Returns:
            True if activated successfully
        """
        try:
            api_key = self.get_by_id(key_id)
            if not api_key:
                return False
            
            api_key.is_active = True
            self.db.commit()
            
            logger.info(f"Activated API key {key_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error activating API key {key_id}: {e}")
            raise

    def update_expiration(self, key_id: UUID, expires_at: Optional[datetime]) -> bool:
        """
        Update API key expiration date.
        
        Args:
            key_id: API key UUID
            expires_at: New expiration date (None for no expiration)
            
        Returns:
            True if updated successfully
        """
        try:
            api_key = self.get_by_id(key_id)
            if not api_key:
                return False
            
            api_key.expires_at = expires_at
            self.db.commit()
            
            logger.info(f"Updated expiration for API key {key_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating expiration for API key {key_id}: {e}")
            raise

    def get_expired_keys(self) -> List[APIKeyDB]:
        """
        Get all expired API keys.
        
        Returns:
            List of expired API keys
        """
        try:
            now = datetime.utcnow()
            return self.db.query(APIKeyDB).filter(
                and_(
                    APIKeyDB.expires_at.isnot(None),
                    APIKeyDB.expires_at < now,
                    APIKeyDB.is_active == True
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting expired API keys: {e}")
            raise

    def cleanup_expired_keys(self) -> int:
        """
        Deactivate all expired API keys.
        
        Returns:
            Number of keys deactivated
        """
        try:
            expired_keys = self.get_expired_keys()
            count = 0
            
            for key in expired_keys:
                key.is_active = False
                count += 1
            
            if count > 0:
                self.db.commit()
                logger.info(f"Deactivated {count} expired API keys")
            
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up expired API keys: {e}")
            raise

    def get_keys_by_name(self, user_id: UUID, name: str) -> List[APIKeyDB]:
        """
        Get API keys by name for a user.
        
        Args:
            user_id: User's UUID
            name: Key name to search for
            
        Returns:
            List of matching API keys
        """
        try:
            return self.db.query(APIKeyDB).filter(
                and_(
                    APIKeyDB.user_id == user_id,
                    APIKeyDB.name == name
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting API keys by name '{name}' for user {user_id}: {e}")
            raise

    def count_by_user(self, user_id: UUID) -> int:
        """
        Count API keys for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of API keys
        """
        try:
            return self.db.query(APIKeyDB).filter(APIKeyDB.user_id == user_id).count()
        except Exception as e:
            logger.error(f"Error counting API keys for user {user_id}: {e}")
            raise

    def count_active_by_user(self, user_id: UUID) -> int:
        """
        Count active API keys for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of active API keys
        """
        try:
            return self.db.query(APIKeyDB).filter(
                and_(
                    APIKeyDB.user_id == user_id,
                    APIKeyDB.is_active == True
                )
            ).count()
        except Exception as e:
            logger.error(f"Error counting active API keys for user {user_id}: {e}")
            raise

    def get_recently_used(self, user_id: UUID, days: int = 30) -> List[APIKeyDB]:
        """
        Get recently used API keys for a user.
        
        Args:
            user_id: User's UUID
            days: Number of days to look back
            
        Returns:
            List of recently used API keys
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return self.db.query(APIKeyDB).filter(
                and_(
                    APIKeyDB.user_id == user_id,
                    APIKeyDB.last_used_at >= cutoff_date
                )
            ).order_by(APIKeyDB.last_used_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting recently used API keys for user {user_id}: {e}")
            raise

    def search_keys(self, search_term: str, limit: int = 50) -> List[APIKeyDB]:
        """
        Search API keys by name across all users.
        
        Args:
            search_term: Search term
            limit: Maximum number of results
            
        Returns:
            List of matching API keys
        """
        try:
            search_pattern = f"%{search_term}%"
            return self.db.query(APIKeyDB).filter(
                APIKeyDB.name.ilike(search_pattern)
            ).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching API keys with term '{search_term}': {e}")
            raise

    def delete_keys_by_user(self, user_id: UUID) -> int:
        """
        Delete all API keys for a user (hard delete).
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.get_by_user(user_id)
            count = len(keys)
            
            for key in keys:
                self.db.delete(key)
            
            if count > 0:
                self.db.commit()
                logger.info(f"Deleted {count} API keys for user {user_id}")
            
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting API keys for user {user_id}: {e}")
            raise
