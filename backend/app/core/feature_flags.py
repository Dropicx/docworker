"""
Feature flags service for runtime feature toggles.

Usage:
    from app.core.feature_flags import feature_flags

    if feature_flags.is_enabled("new_feature"):
        use_new_feature()
    else:
        use_old_feature()
"""

import logging

from sqlalchemy.orm import Session

from app.database.connection import get_session
from app.database.feature_flags_models import FeatureFlag

logger = logging.getLogger(__name__)


class FeatureFlagsService:
    """
    Service for checking feature flags.

    Features can be enabled/disabled without deployment.
    Supports gradual rollout with percentage-based rollout.
    """

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 60  # Cache for 60 seconds

    def is_enabled(
        self, feature_name: str, user_id: str | None = None, default: bool = False
    ) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            feature_name: Name of the feature flag
            user_id: Optional user ID for gradual rollout
            default: Default value if flag doesn't exist

        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            # Get feature flag from database
            with next(get_session()) as db:
                feature = db.query(FeatureFlag).filter(FeatureFlag.name == feature_name).first()

                if not feature:
                    logger.warning(
                        f"Feature flag '{feature_name}' not found, using default={default}"
                    )
                    return default

                # If fully enabled or disabled
                if feature.rollout_percentage == 100:
                    return feature.enabled
                if feature.rollout_percentage == 0:
                    return False

                # Gradual rollout: use user_id hash to determine if enabled
                if user_id:
                    # Simple deterministic rollout based on user_id hash
                    user_hash = hash(user_id) % 100
                    return user_hash < feature.rollout_percentage

                # No user_id provided, use enabled flag
                return feature.enabled

        except Exception as e:
            logger.error(f"Error checking feature flag '{feature_name}': {e}")
            return default

    def get_all_flags(self, db: Session) -> list[FeatureFlag]:
        """Get all feature flags."""
        try:
            return db.query(FeatureFlag).all()
        except Exception as e:
            logger.error(f"Error fetching feature flags: {e}")
            return []

    def set_flag(
        self, db: Session, feature_name: str, enabled: bool, rollout_percentage: int | None = None
    ) -> FeatureFlag:
        """
        Set a feature flag value.

        Args:
            db: Database session
            feature_name: Name of the feature flag
            enabled: Whether the feature is enabled
            rollout_percentage: Optional rollout percentage (0-100)

        Returns:
            Updated feature flag
        """
        feature = db.query(FeatureFlag).filter(FeatureFlag.name == feature_name).first()

        if not feature:
            # Create new feature flag
            feature = FeatureFlag(
                name=feature_name,
                enabled=enabled,
                rollout_percentage=rollout_percentage or (100 if enabled else 0),
            )
            db.add(feature)
        else:
            # Update existing flag
            feature.enabled = enabled
            if rollout_percentage is not None:
                feature.rollout_percentage = rollout_percentage

        db.commit()
        db.refresh(feature)

        logger.info(
            f"Feature flag '{feature_name}' set to enabled={enabled}, rollout={feature.rollout_percentage}%"
        )
        return feature


# Global feature flags instance
feature_flags = FeatureFlagsService()
