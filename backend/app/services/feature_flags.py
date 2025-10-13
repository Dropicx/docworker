"""
Feature Flag Service

Provides centralized feature flag management for gradual rollout and A/B testing.
Checks environment variables first, then falls back to database configuration.

**Supported Features:**
- vision_llm_fallback_enabled: Allow fallback to Vision LLM when local OCR fails
- multi_file_processing_enabled: Enable multi-file document processing
- advanced_privacy_filter_enabled: Use advanced privacy filtering
- cost_tracking_enabled: Enable AI cost tracking and logging
- parallel_step_execution_enabled: Execute independent pipeline steps in parallel

**Usage Example:**
    >>> from app.services.feature_flags import FeatureFlags, Feature
    >>>
    >>> flags = FeatureFlags(db_session)
    >>> if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
    ...     # Use Vision LLM fallback
    ...     result = await ovh_client.extract_text_with_vision(image)
"""

import os
import logging
from enum import Enum
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class Feature(str, Enum):
    """
    Available feature flags.

    Each feature can be controlled via environment variables or database configuration.
    Environment variables take precedence over database settings.
    """
    # OCR and Text Extraction
    VISION_LLM_FALLBACK = "vision_llm_fallback_enabled"
    MULTI_FILE_PROCESSING = "multi_file_processing_enabled"

    # Privacy and Security
    ADVANCED_PRIVACY_FILTER = "advanced_privacy_filter_enabled"
    PII_REMOVAL_ENABLED = "pii_removal_enabled"

    # Performance and Monitoring
    COST_TRACKING = "cost_tracking_enabled"
    AI_LOGGING = "ai_logging_enabled"
    PARALLEL_STEP_EXECUTION = "parallel_step_execution_enabled"

    # Pipeline Features
    DYNAMIC_BRANCHING = "dynamic_branching_enabled"
    STOP_CONDITIONS = "stop_conditions_enabled"
    RETRY_ON_FAILURE = "retry_on_failure_enabled"

    # Experimental Features
    HYBRID_OCR_STRATEGY = "hybrid_ocr_strategy_enabled"
    AUTO_QUALITY_DETECTION = "auto_quality_detection_enabled"


class FeatureFlags:
    """
    Feature flag service for controlling feature availability.

    **Priority Order:**
    1. Environment variable (FEATURE_FLAG_{FEATURE_NAME})
    2. Database configuration (system_settings table)
    3. Default value (feature-specific)

    **Default Values:**
    Most features default to True (enabled) for production readiness.
    Experimental features default to False.

    Attributes:
        session: SQLAlchemy database session for configuration lookup
        _cache: In-memory cache of feature states (refreshed every 60 seconds)

    Example:
        >>> flags = FeatureFlags(db_session)
        >>>
        >>> # Check single feature
        >>> if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
        ...     logger.info("Vision LLM fallback enabled")
        >>>
        >>> # Get all enabled features
        >>> enabled = flags.get_enabled_features()
        >>> print(f"Enabled features: {enabled}")
        >>>
        >>> # Override feature via environment
        >>> os.environ['FEATURE_FLAG_VISION_LLM_FALLBACK'] = 'false'
        >>> assert not flags.is_enabled(Feature.VISION_LLM_FALLBACK)
    """

    # Default values for each feature
    DEFAULTS = {
        # OCR - enabled by default
        Feature.VISION_LLM_FALLBACK: True,
        Feature.MULTI_FILE_PROCESSING: True,

        # Privacy - enabled by default for GDPR compliance
        Feature.ADVANCED_PRIVACY_FILTER: True,
        Feature.PII_REMOVAL_ENABLED: True,

        # Monitoring - enabled by default
        Feature.COST_TRACKING: True,
        Feature.AI_LOGGING: True,
        Feature.PARALLEL_STEP_EXECUTION: False,  # Disabled until thoroughly tested

        # Pipeline features - enabled by default
        Feature.DYNAMIC_BRANCHING: True,
        Feature.STOP_CONDITIONS: True,
        Feature.RETRY_ON_FAILURE: True,

        # Experimental - disabled by default
        Feature.HYBRID_OCR_STRATEGY: False,
        Feature.AUTO_QUALITY_DETECTION: False,
    }

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize feature flag service.

        Args:
            session: Optional SQLAlchemy session for database lookup.
                     If None, only environment variables and defaults will be used.
        """
        self.session = session
        logger.debug("🚩 Feature Flags service initialized")

    def is_enabled(self, feature: Feature) -> bool:
        """
        Check if a feature is enabled.

        Priority order:
        1. Environment variable: FEATURE_FLAG_{FEATURE_NAME}
        2. Database configuration (system_settings table)
        3. Default value from DEFAULTS dict

        Args:
            feature: Feature to check

        Returns:
            bool: True if feature is enabled, False otherwise

        Example:
            >>> flags = FeatureFlags(db_session)
            >>> if flags.is_enabled(Feature.VISION_LLM_FALLBACK):
            ...     print("Vision LLM fallback is enabled")
        """
        # 1. Check environment variable first
        env_var_name = f"FEATURE_FLAG_{feature.value.upper()}"
        env_value = os.getenv(env_var_name)

        if env_value is not None:
            is_enabled = env_value.lower() in ("true", "1", "yes", "on")
            logger.debug(f"🚩 Feature '{feature.value}' from env: {is_enabled}")
            return is_enabled

        # 2. Check database if session available
        if self.session:
            try:
                from app.database.unified_models import SystemSettingsDB

                setting = self.session.query(SystemSettingsDB).filter_by(
                    key=feature.value
                ).first()

                if setting:
                    is_enabled = setting.value.lower() in ("true", "1", "yes", "on")
                    logger.debug(f"🚩 Feature '{feature.value}' from DB: {is_enabled}")
                    return is_enabled

            except Exception as e:
                logger.warning(f"⚠️ Failed to check feature '{feature.value}' in DB: {e}")

        # 3. Fall back to default
        default_value = self.DEFAULTS.get(feature, False)
        logger.debug(f"🚩 Feature '{feature.value}' using default: {default_value}")
        return default_value

    def is_disabled(self, feature: Feature) -> bool:
        """
        Check if a feature is disabled (inverse of is_enabled).

        Args:
            feature: Feature to check

        Returns:
            bool: True if feature is disabled, False if enabled

        Example:
            >>> if flags.is_disabled(Feature.EXPERIMENTAL_FEATURE):
            ...     logger.info("Experimental feature is disabled")
        """
        return not self.is_enabled(feature)

    def get_enabled_features(self) -> list[str]:
        """
        Get list of all enabled features.

        Returns:
            List of enabled feature names

        Example:
            >>> flags = FeatureFlags(db_session)
            >>> enabled = flags.get_enabled_features()
            >>> print(f"Enabled: {', '.join(enabled)}")
            Enabled: vision_llm_fallback_enabled, cost_tracking_enabled, ...
        """
        enabled = []

        for feature in Feature:
            if self.is_enabled(feature):
                enabled.append(feature.value)

        return enabled

    def get_feature_status(self) -> dict[str, bool]:
        """
        Get status of all features as a dictionary.

        Returns:
            Dictionary mapping feature names to their enabled status

        Example:
            >>> flags = FeatureFlags(db_session)
            >>> status = flags.get_feature_status()
            >>> print(status)
            {
                'vision_llm_fallback_enabled': True,
                'cost_tracking_enabled': True,
                'experimental_feature_enabled': False,
                ...
            }
        """
        status = {}

        for feature in Feature:
            status[feature.value] = self.is_enabled(feature)

        return status

    def require_feature(self, feature: Feature) -> None:
        """
        Require a feature to be enabled, raise exception if disabled.

        Args:
            feature: Feature that must be enabled

        Raises:
            RuntimeError: If feature is disabled

        Example:
            >>> flags = FeatureFlags(db_session)
            >>> flags.require_feature(Feature.VISION_LLM_FALLBACK)
            >>> # Continues if enabled, raises RuntimeError if disabled
        """
        if not self.is_enabled(feature):
            raise RuntimeError(
                f"Feature '{feature.value}' is required but currently disabled. "
                f"Enable it via environment variable FEATURE_FLAG_{feature.value.upper()}=true "
                f"or database configuration."
            )


# Global helper functions for convenience

def is_feature_enabled(feature: Feature, session: Optional[Session] = None) -> bool:
    """
    Global helper function to check if a feature is enabled.

    Args:
        feature: Feature to check
        session: Optional database session

    Returns:
        bool: True if enabled, False otherwise

    Example:
        >>> from app.services.feature_flags import is_feature_enabled, Feature
        >>> if is_feature_enabled(Feature.VISION_LLM_FALLBACK):
        ...     print("Vision LLM fallback enabled")
    """
    flags = FeatureFlags(session=session)
    return flags.is_enabled(feature)


def get_enabled_features(session: Optional[Session] = None) -> list[str]:
    """
    Global helper function to get all enabled features.

    Args:
        session: Optional database session

    Returns:
        List of enabled feature names

    Example:
        >>> from app.services.feature_flags import get_enabled_features
        >>> enabled = get_enabled_features()
        >>> print(f"Enabled features: {enabled}")
    """
    flags = FeatureFlags(session=session)
    return flags.get_enabled_features()
