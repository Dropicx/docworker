"""
Core application configuration and dependencies.

This module provides centralized configuration management and dependency injection
for the DocTranslator application.
"""

from app.core.config import settings, Settings, get_settings
from app.core.feature_flags import feature_flags, FeatureFlagsService

__all__ = [
    "settings",
    "Settings",
    "get_settings",
    "feature_flags",
    "FeatureFlagsService",
]
