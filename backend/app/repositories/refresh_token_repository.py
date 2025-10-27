"""
Refresh Token Repository

Provides data access methods for refresh token management including creation,
validation, cleanup, and revocation operations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database.auth_models import RefreshTokenDB
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class RefreshTokenRepository(BaseRepository[RefreshTokenDB]):
    """Repository for refresh token data access operations."""

    def __init__(self, db: Session):
        super().__init__(db, RefreshTokenDB)

    def create_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime
    ) -> RefreshTokenDB:
        """
        Create a new refresh token.
        
        Args:
            user_id: User who owns the token
            token_hash: Hashed token value
            expires_at: Token expiration date
            
        Returns:
            Created refresh token instance
        """
        try:
            refresh_token = self.create(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                is_revoked=False
            )
            
            logger.debug(f"Created refresh token for user {user_id}")
            return refresh_token
        except Exception as e:
            logger.error(f"Error creating refresh token for user {user_id}: {e}")
            raise

    def get_by_hash(self, token_hash: str) -> Optional[RefreshTokenDB]:
        """
        Get refresh token by its hash.
        
        Args:
            token_hash: Hashed token value
            
        Returns:
            Refresh token instance or None if not found
        """
        try:
            return self.db.query(RefreshTokenDB).filter(
                RefreshTokenDB.token_hash == token_hash
            ).first()
        except Exception as e:
            logger.error(f"Error getting refresh token by hash: {e}")
            raise

    def get_by_user(self, user_id: UUID) -> List[RefreshTokenDB]:
        """
        Get all refresh tokens for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of user's refresh tokens
        """
        try:
            return self.db.query(RefreshTokenDB).filter(
                RefreshTokenDB.user_id == user_id
            ).all()
        except Exception as e:
            logger.error(f"Error getting refresh tokens for user {user_id}: {e}")
            raise

    def get_active_by_user(self, user_id: UUID) -> List[RefreshTokenDB]:
        """
        Get active (non-revoked, non-expired) refresh tokens for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of active refresh tokens
        """
        try:
            now = datetime.now(timezone.utc)
            return self.db.query(RefreshTokenDB).filter(
                and_(
                    RefreshTokenDB.user_id == user_id,
                    RefreshTokenDB.is_revoked == False,
                    RefreshTokenDB.expires_at > now
                )
            ).all()
        except Exception as e:
            logger.error(f"Error getting active refresh tokens for user {user_id}: {e}")
            raise

    def revoke_token(self, token_id: UUID) -> bool:
        """
        Revoke a refresh token.
        
        Args:
            token_id: Token UUID
            
        Returns:
            True if revoked successfully
        """
        try:
            token = self.get_by_id(token_id)
            if not token:
                return False
            
            token.is_revoked = True
            self.db.commit()
            
            logger.info(f"Revoked refresh token {token_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revoking refresh token {token_id}: {e}")
            raise

    def revoke_token_by_hash(self, token_hash: str) -> bool:
        """
        Revoke a refresh token by its hash.
        
        Args:
            token_hash: Hashed token value
            
        Returns:
            True if revoked successfully
        """
        try:
            token = self.get_by_hash(token_hash)
            if not token:
                return False
            
            token.is_revoked = True
            self.db.commit()
            
            logger.info(f"Revoked refresh token by hash")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revoking refresh token by hash: {e}")
            raise

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of tokens revoked
        """
        try:
            tokens = self.get_active_by_user(user_id)
            count = 0
            
            for token in tokens:
                token.is_revoked = True
                count += 1
            
            if count > 0:
                self.db.commit()
                logger.info(f"Revoked {count} refresh tokens for user {user_id}")
            
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error revoking all tokens for user {user_id}: {e}")
            raise

    def update_last_used(self, token_id: UUID) -> bool:
        """
        Update token's last used timestamp.
        
        Args:
            token_id: Token UUID
            
        Returns:
            True if updated successfully
        """
        try:
            token = self.get_by_id(token_id)
            if not token:
                return False
            
            token.last_used_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.debug(f"Updated last used for refresh token {token_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last used for refresh token {token_id}: {e}")
            raise

    def get_expired_tokens(self) -> List[RefreshTokenDB]:
        """
        Get all expired refresh tokens.
        
        Returns:
            List of expired tokens
        """
        try:
            now = datetime.now(timezone.utc)
            return self.db.query(RefreshTokenDB).filter(
                RefreshTokenDB.expires_at < now
            ).all()
        except Exception as e:
            logger.error(f"Error getting expired refresh tokens: {e}")
            raise

    def cleanup_expired_tokens(self) -> int:
        """
        Delete expired refresh tokens.
        
        Returns:
            Number of tokens deleted
        """
        try:
            expired_tokens = self.get_expired_tokens()
            count = len(expired_tokens)
            
            for token in expired_tokens:
                self.db.delete(token)
            
            if count > 0:
                self.db.commit()
                logger.info(f"Cleaned up {count} expired refresh tokens")
            
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up expired refresh tokens: {e}")
            raise

    def cleanup_old_tokens(self, days: int = 30) -> int:
        """
        Delete old refresh tokens (for security).
        
        Args:
            days: Number of days to keep tokens
            
        Returns:
            Number of tokens deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            old_tokens = self.db.query(RefreshTokenDB).filter(
                RefreshTokenDB.created_at < cutoff_date
            ).all()
            
            count = len(old_tokens)
            for token in old_tokens:
                self.db.delete(token)
            
            if count > 0:
                self.db.commit()
                logger.info(f"Cleaned up {count} old refresh tokens")
            
            return count
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cleaning up old refresh tokens: {e}")
            raise

    def is_token_valid(self, token_hash: str) -> bool:
        """
        Check if a refresh token is valid (not revoked and not expired).
        
        Args:
            token_hash: Hashed token value
            
        Returns:
            True if token is valid
        """
        try:
            token = self.get_by_hash(token_hash)
            if not token:
                return False
            
            now = datetime.now(timezone.utc)
            return not token.is_revoked and token.expires_at > now
        except Exception as e:
            logger.error(f"Error checking token validity: {e}")
            return False

    def count_by_user(self, user_id: UUID) -> int:
        """
        Count refresh tokens for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of refresh tokens
        """
        try:
            return self.db.query(RefreshTokenDB).filter(
                RefreshTokenDB.user_id == user_id
            ).count()
        except Exception as e:
            logger.error(f"Error counting refresh tokens for user {user_id}: {e}")
            raise

    def count_active_by_user(self, user_id: UUID) -> int:
        """
        Count active refresh tokens for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Number of active refresh tokens
        """
        try:
            now = datetime.now(timezone.utc)
            return self.db.query(RefreshTokenDB).filter(
                and_(
                    RefreshTokenDB.user_id == user_id,
                    RefreshTokenDB.is_revoked == False,
                    RefreshTokenDB.expires_at > now
                )
            ).count()
        except Exception as e:
            logger.error(f"Error counting active refresh tokens for user {user_id}: {e}")
            raise

    def get_recently_used(self, user_id: UUID, hours: int = 24) -> List[RefreshTokenDB]:
        """
        Get recently used refresh tokens for a user.
        
        Args:
            user_id: User's UUID
            hours: Number of hours to look back
            
        Returns:
            List of recently used tokens
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            return self.db.query(RefreshTokenDB).filter(
                and_(
                    RefreshTokenDB.user_id == user_id,
                    RefreshTokenDB.last_used_at >= cutoff_time
                )
            ).order_by(RefreshTokenDB.last_used_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting recently used tokens for user {user_id}: {e}")
            raise
