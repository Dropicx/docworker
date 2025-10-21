"""
Core application configuration and dependencies.

This module provides centralized configuration management and dependency injection
for the DocTranslator application.

Note: feature_flags is NOT imported here to avoid circular imports.
Import it directly when needed:
    from app.core.feature_flags import feature_flags
"""

from app.core.config import Settings, get_settings, settings

__all__ = [
    "settings",
    "Settings",
    "get_settings",
]
