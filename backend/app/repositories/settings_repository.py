"""
System Settings Repository

Provides type-safe access to system configuration stored in database.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.database.unified_models import SystemSettingsDB
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SettingsRepository(BaseRepository[SystemSettingsDB]):
    """Repository for system settings with type conversion."""

    def __init__(self, db: Session):
        super().__init__(db, SystemSettingsDB)

    def get_by_key(self, key: str) -> SystemSettingsDB | None:
        """Get setting by key."""
        return self.get_one({"key": key})

    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get setting value with type conversion.

        Args:
            key: Setting key
            default: Default value if setting doesn't exist

        Returns:
            Converted value based on value_type
        """
        setting = self.get_by_key(key)
        if not setting:
            logger.warning(f"Setting '{key}' not found, using default={default}")
            return default

        return self._convert_value(setting.value, setting.value_type)

    def set_value(self, key: str, value: Any, value_type: str = "string", description: str = "") -> SystemSettingsDB:
        """
        Set setting value (create or update).

        Args:
            key: Setting key
            value: Setting value
            value_type: Value type (string, int, float, bool, json)
            description: Setting description
        """
        setting = self.get_by_key(key)

        value_str = str(value).lower() if value_type == "bool" else str(value)

        if setting:
            # Update existing
            setting.value = value_str
            setting.value_type = value_type
            if description:
                setting.description = description
            self.db.commit()
            self.db.refresh(setting)
            logger.info(f"Updated setting '{key}' = {value}")
        else:
            # Create new
            setting = self.create(
                key=key,
                value=value_str,
                value_type=value_type,
                description=description,
                is_encrypted=False
            )
            logger.info(f"Created setting '{key}' = {value}")

        return setting

    def get_all_settings(self) -> dict:
        """
        Get all settings as a dictionary.

        Returns:
            Dict of key:value pairs with converted values
        """
        settings = self.get_all(limit=1000)
        return {
            setting.key: self._convert_value(setting.value, setting.value_type)
            for setting in settings
        }

    @staticmethod
    def _convert_value(value: str, value_type: str) -> Any:
        """
        Convert string value to appropriate type.

        Args:
            value: String value from database
            value_type: Type to convert to

        Returns:
            Converted value
        """
        if value_type == "int":
            return int(value)
        if value_type == "float":
            return float(value)
        if value_type == "bool":
            return value.lower() in ("true", "1", "yes", "on")
        if value_type == "json":
            import json
            return json.loads(value)
        # string
        return value
