"""
System Settings Repository

Handles database operations for system-wide configuration settings.
Supports conditional encryption based on is_encrypted flag.
"""

import logging
from sqlalchemy.orm import Session

from app.core.encryption import encryptor
from app.database.unified_models import SystemSettingsDB
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SystemSettingsRepository(BaseRepository[SystemSettingsDB]):
    """
    Repository for System Settings operations.

    Provides specialized queries for managing system-wide configuration
    settings stored in the database.
    """

    def __init__(self, db: Session):
        """
        Initialize system settings repository.

        Args:
            db: Database session
        """
        super().__init__(db, SystemSettingsDB)

    def get_by_key(self, key: str) -> SystemSettingsDB | None:
        """
        Get a setting by its unique key with automatic decryption.

        Args:
            key: Setting key (e.g., 'enable_privacy_filter')

        Returns:
            Setting instance with decrypted value or None if not found
        """
        setting = self.db.query(self.model).filter_by(key=key).first()

        # Decrypt if marked as encrypted
        if setting and setting.is_encrypted and encryptor.is_enabled():
            try:
                setting.value = encryptor.decrypt_field(setting.value)
                logger.debug(f"Decrypted setting: {key}")
            except Exception as e:
                logger.error(f"Failed to decrypt setting {key}: {e}")
                # Return encrypted value for debugging
                logger.warning(f"Returning encrypted value for {key}")

        return setting

    def get_value(self, key: str, default: str | None = None) -> str | None:
        """
        Get a setting value by key with optional default.

        Args:
            key: Setting key
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        setting = self.get_by_key(key)
        return setting.value if setting else default

    def get_bool_value(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean setting value.

        Args:
            key: Setting key
            default: Default value if setting not found

        Returns:
            Boolean value
        """
        value = self.get_value(key)
        if value is None:
            return default

        return value.lower() in ("true", "1", "yes", "on")

    def get_int_value(self, key: str, default: int = 0) -> int:
        """
        Get an integer setting value.

        Args:
            key: Setting key
            default: Default value if setting not found or invalid

        Returns:
            Integer value
        """
        value = self.get_value(key)
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float_value(self, key: str, default: float = 0.0) -> float:
        """
        Get a float setting value.

        Args:
            key: Setting key
            default: Default value if setting not found or invalid

        Returns:
            Float value
        """
        value = self.get_value(key)
        if value is None:
            return default

        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def set_value(self, key: str, value: str, description: str | None = None, is_encrypted: bool = False) -> SystemSettingsDB:
        """
        Set a setting value with optional encryption, creating if it doesn't exist.

        Args:
            key: Setting key
            value: Setting value
            description: Optional description
            is_encrypted: Whether to encrypt this value

        Returns:
            Setting instance with decrypted value
        """
        # Get existing setting (will be decrypted)
        setting = self.get_by_key(key)

        # Encrypt value if requested
        value_to_store = value
        if is_encrypted and encryptor.is_enabled():
            try:
                value_to_store = encryptor.encrypt_field(value)
                logger.debug(f"Encrypted setting: {key}")
            except Exception as e:
                logger.error(f"Failed to encrypt setting {key}: {e}")
                raise

        if setting:
            # Update existing
            setting.value = value_to_store
            setting.is_encrypted = is_encrypted
            if description:
                setting.description = description
            self.db.commit()
            self.db.refresh(setting)

            # Return with decrypted value for service layer
            if is_encrypted and encryptor.is_enabled():
                setting.value = value
        else:
            # Create new
            setting = self.create(
                key=key,
                value=value_to_store,
                value_type="string",
                description=description or "",
                is_encrypted=is_encrypted
            )

            # Return with decrypted value for service layer
            if is_encrypted and encryptor.is_enabled():
                setting.value = value

        return setting

    def set_bool_value(
        self, key: str, value: bool, description: str | None = None
    ) -> SystemSettingsDB:
        """
        Set a boolean setting value.

        Args:
            key: Setting key
            value: Boolean value
            description: Optional description

        Returns:
            Setting instance
        """
        return self.set_value(key, "true" if value else "false", description)

    def set_int_value(
        self, key: str, value: int, description: str | None = None
    ) -> SystemSettingsDB:
        """
        Set an integer setting value.

        Args:
            key: Setting key
            value: Integer value
            description: Optional description

        Returns:
            Setting instance
        """
        return self.set_value(key, str(value), description)

    def set_float_value(
        self, key: str, value: float, description: str | None = None
    ) -> SystemSettingsDB:
        """
        Set a float setting value.

        Args:
            key: Setting key
            value: Float value
            description: Optional description

        Returns:
            Setting instance
        """
        return self.set_value(key, str(value), description)

    def key_exists(self, key: str) -> bool:
        """
        Check if a setting key exists.

        Args:
            key: Setting key to check

        Returns:
            True if key exists, False otherwise
        """
        return self.db.query(self.model).filter_by(key=key).count() > 0

    def get_all_settings(self) -> dict[str, str]:
        """
        Get all settings as a key-value dictionary.

        Returns:
            Dictionary mapping keys to values
        """
        settings = self.get_all()
        return {setting.key: setting.value for setting in settings}

    def get_settings_by_prefix(self, prefix: str) -> list[SystemSettingsDB]:
        """
        Get all settings with keys starting with a prefix.

        Args:
            prefix: Key prefix to filter by (e.g., 'enable_')

        Returns:
            List of matching settings
        """
        return self.db.query(self.model).filter(self.model.key.like(f"{prefix}%")).all()

    def get_feature_flags(self) -> dict[str, bool]:
        """
        Get all feature flag settings.

        Returns:
            Dictionary mapping feature flag keys to boolean values
        """
        flags = self.get_settings_by_prefix("enable_")
        return {flag.key: flag.value.lower() in ("true", "1", "yes", "on") for flag in flags}

    def delete_by_key(self, key: str) -> bool:
        """
        Delete a setting by key.

        Args:
            key: Setting key to delete

        Returns:
            True if deleted, False if not found
        """
        setting = self.get_by_key(key)
        if not setting:
            return False

        self.db.delete(setting)
        self.db.commit()
        return True

    def bulk_update(self, settings: dict[str, str]) -> int:
        """
        Update multiple settings at once.

        Args:
            settings: Dictionary mapping keys to values

        Returns:
            Number of settings updated
        """
        count = 0

        for key, value in settings.items():
            self.set_value(key, value)
            count += 1

        return count

    def get_settings_for_export(self) -> dict[str, dict]:
        """
        Get all settings in export format with metadata.

        Returns:
            Dictionary with setting details
        """
        settings = self.get_all()
        return {
            setting.key: {
                "value": setting.value,
                "description": setting.description,
                "created_at": setting.created_at.isoformat() if setting.created_at else None,
                "last_modified": setting.updated_at.isoformat() if setting.updated_at else None,
            }
            for setting in settings
        }

    def import_settings(self, settings: dict[str, str], overwrite: bool = False) -> dict:
        """
        Import settings from a dictionary.

        Args:
            settings: Dictionary mapping keys to values
            overwrite: Whether to overwrite existing settings

        Returns:
            Dictionary with import statistics
        """
        stats = {"imported": 0, "skipped": 0, "updated": 0}

        for key, value in settings.items():
            if self.key_exists(key):
                if overwrite:
                    self.set_value(key, value)
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
            else:
                self.set_value(key, value)
                stats["imported"] += 1

        return stats

    def search_settings(self, search_term: str) -> list[SystemSettingsDB]:
        """
        Search settings by key or description.

        Args:
            search_term: Text to search for (case-insensitive)

        Returns:
            List of matching settings
        """
        return (
            self.db.query(self.model)
            .filter(
                (self.model.key.ilike(f"%{search_term}%"))
                | (self.model.description.ilike(f"%{search_term}%"))
            )
            .all()
        )

    def get_settings_statistics(self) -> dict:
        """
        Get aggregate statistics about system settings.

        Returns:
            Dictionary with statistics
        """
        settings = self.get_all()
        feature_flags = [s for s in settings if s.key.startswith("enable_")]

        return {
            "total_settings": len(settings),
            "feature_flags": len(feature_flags),
            "enabled_features": sum(
                1 for f in feature_flags if f.value.lower() in ("true", "1", "yes", "on")
            ),
            "boolean_settings": sum(
                1 for s in settings if s.value.lower() in ("true", "false", "1", "0", "yes", "no")
            ),
            "numeric_settings": sum(1 for s in settings if s.value.isdigit()),
        }
