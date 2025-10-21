"""
Feature Flags Repository

Provides access to feature flag configuration.
"""

import logging

from sqlalchemy.orm import Session

from app.database.feature_flags_models import FeatureFlag
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class FeatureFlagsRepository(BaseRepository[FeatureFlag]):
    """Repository for feature flags."""

    def __init__(self, db: Session):
        super().__init__(db, FeatureFlag)

    def get_by_name(self, name: str) -> FeatureFlag | None:
        """Get feature flag by name."""
        return self.get_one({"name": name})

    def is_enabled(self, name: str, default: bool = False) -> bool:
        """
        Check if feature flag is enabled.

        Args:
            name: Feature flag name
            default: Default value if flag doesn't exist

        Returns:
            True if enabled, False otherwise
        """
        flag = self.get_by_name(name)
        if not flag:
            return default
        return flag.enabled

    def set_flag(
        self, name: str, enabled: bool, description: str = "", rollout_percentage: int = 100
    ) -> FeatureFlag:
        """
        Set feature flag (create or update).

        Args:
            name: Feature flag name
            enabled: Whether flag is enabled
            description: Flag description
            rollout_percentage: Percentage rollout (0-100)
        """
        flag = self.get_by_name(name)

        if flag:
            # Update existing
            flag.enabled = enabled
            flag.rollout_percentage = rollout_percentage
            if description:
                flag.description = description
            self.db.commit()
            self.db.refresh(flag)
            logger.info(f"Updated feature flag '{name}' = {enabled}")
        else:
            # Create new
            flag = self.create(
                name=name,
                enabled=enabled,
                description=description,
                rollout_percentage=rollout_percentage,
            )
            logger.info(f"Created feature flag '{name}' = {enabled}")

        return flag

    def get_all_enabled(self) -> list[FeatureFlag]:
        """Get all enabled feature flags."""
        return self.get_all(filters={"enabled": True}, limit=1000)

    def get_all_flags_dict(self) -> dict:
        """
        Get all feature flags as dictionary.

        Returns:
            Dict of name:enabled pairs
        """
        flags = self.get_all(limit=1000)
        return {flag.name: flag.enabled for flag in flags}
