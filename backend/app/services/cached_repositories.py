"""
Cached Repository Wrappers

Provides caching layer over existing repositories using cache-aside pattern.
Caches are populated on first read and invalidated on write operations.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.modular_pipeline_models import (
    AvailableModelDB,
    DocumentClassDB,
    DynamicPipelineStepDB,
    OCRConfigurationDB,
)
from app.database.unified_models import SystemSettingsDB
from app.repositories.available_model_repository import AvailableModelRepository
from app.repositories.document_class_repository import DocumentClassRepository
from app.repositories.ocr_configuration_repository import OCRConfigurationRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)


class CachedPipelineStepRepository:
    """
    Pipeline step repository with caching layer.

    Caches enabled steps and all ordered steps for fast access.
    Automatically invalidates cache on write operations.
    """

    def __init__(self, db: Session, cache: CacheService):
        """
        Initialize cached pipeline step repository.

        Args:
            db: Database session
            cache: Cache service instance
        """
        self._repo = PipelineStepRepository(db)
        self._cache = cache
        self._ttl = settings.cache_pipeline_ttl_seconds

    async def get_enabled_steps(self) -> list[DynamicPipelineStepDB]:
        """Get enabled steps (cached)."""
        cached = await self._cache.get(CacheService.NS_PIPELINE_STEPS, "enabled")
        if cached is not None:
            return self._deserialize_steps(cached)

        steps = self._repo.get_enabled_steps()
        await self._cache.set(
            CacheService.NS_PIPELINE_STEPS,
            "enabled",
            steps,
            ttl=self._ttl,
        )
        return steps

    async def get_all_ordered(self) -> list[DynamicPipelineStepDB]:
        """Get all steps ordered (cached)."""
        cached = await self._cache.get(CacheService.NS_PIPELINE_STEPS, "all_ordered")
        if cached is not None:
            return self._deserialize_steps(cached)

        steps = self._repo.get_all_ordered()
        await self._cache.set(
            CacheService.NS_PIPELINE_STEPS,
            "all_ordered",
            steps,
            ttl=self._ttl,
        )
        return steps

    def _deserialize_steps(self, cached: list[dict]) -> list[dict]:
        """Deserialize cached steps (returns dicts, not ORM objects)."""
        return cached

    # Delegate non-cached operations to base repo
    def get(self, step_id: int) -> DynamicPipelineStepDB | None:
        """Get step by ID (not cached)."""
        return self._repo.get(step_id)

    def get_step_by_name(self, name: str) -> DynamicPipelineStepDB | None:
        """Get step by name (not cached)."""
        return self._repo.get_step_by_name(name)

    def get_branching_step(self) -> DynamicPipelineStepDB | None:
        """Get branching step (not cached)."""
        return self._repo.get_branching_step()

    def get_universal_steps(self) -> list[DynamicPipelineStepDB]:
        """Get universal steps (not cached - use get_enabled_steps)."""
        return self._repo.get_universal_steps()

    def get_post_branching_steps(self) -> list[DynamicPipelineStepDB]:
        """Get post-branching steps (not cached)."""
        return self._repo.get_post_branching_steps()

    def get_steps_by_document_class(self, class_id: int) -> list[DynamicPipelineStepDB]:
        """Get steps by document class (not cached)."""
        return self._repo.get_steps_by_document_class(class_id)

    # Write operations with cache invalidation
    async def create(self, **kwargs) -> DynamicPipelineStepDB:
        """Create step and invalidate cache."""
        result = self._repo.create(**kwargs)
        await self._cache.delete_namespace(CacheService.NS_PIPELINE_STEPS)
        logger.debug("Pipeline step cache invalidated after create")
        return result

    async def update(self, step_id: int, **kwargs) -> DynamicPipelineStepDB | None:
        """Update step and invalidate cache."""
        result = self._repo.update(step_id, **kwargs)
        await self._cache.delete_namespace(CacheService.NS_PIPELINE_STEPS)
        logger.debug("Pipeline step cache invalidated after update")
        return result

    async def delete(self, step_id: int) -> bool:
        """Delete step and invalidate cache."""
        result = self._repo.delete(step_id)
        await self._cache.delete_namespace(CacheService.NS_PIPELINE_STEPS)
        logger.debug("Pipeline step cache invalidated after delete")
        return result

    async def enable_step(self, step_id: int) -> DynamicPipelineStepDB | None:
        """Enable step and invalidate cache."""
        result = self._repo.enable_step(step_id)
        await self._cache.delete_namespace(CacheService.NS_PIPELINE_STEPS)
        return result

    async def disable_step(self, step_id: int) -> DynamicPipelineStepDB | None:
        """Disable step and invalidate cache."""
        result = self._repo.disable_step(step_id)
        await self._cache.delete_namespace(CacheService.NS_PIPELINE_STEPS)
        return result

    async def reorder_steps(self, step_order: list[int]) -> bool:
        """Reorder steps and invalidate cache."""
        result = self._repo.reorder_steps(step_order)
        await self._cache.delete_namespace(CacheService.NS_PIPELINE_STEPS)
        return result


class CachedDocumentClassRepository:
    """
    Document class repository with caching layer.

    Caches enabled classes for fast classification lookups.
    """

    def __init__(self, db: Session, cache: CacheService):
        """
        Initialize cached document class repository.

        Args:
            db: Database session
            cache: Cache service instance
        """
        self._repo = DocumentClassRepository(db)
        self._cache = cache
        self._ttl = settings.cache_pipeline_ttl_seconds

    async def get_enabled_classes(self) -> list[DocumentClassDB]:
        """Get enabled classes (cached)."""
        cached = await self._cache.get(CacheService.NS_DOCUMENT_CLASSES, "enabled")
        if cached is not None:
            return cached

        classes = self._repo.get_enabled_classes()
        await self._cache.set(
            CacheService.NS_DOCUMENT_CLASSES,
            "enabled",
            classes,
            ttl=self._ttl,
        )
        return classes

    async def get_all(self) -> list[DocumentClassDB]:
        """Get all classes (cached)."""
        cached = await self._cache.get(CacheService.NS_DOCUMENT_CLASSES, "all")
        if cached is not None:
            return cached

        classes = self._repo.get_all()
        await self._cache.set(
            CacheService.NS_DOCUMENT_CLASSES,
            "all",
            classes,
            ttl=self._ttl,
        )
        return classes

    # Delegate non-cached operations
    def get(self, class_id: int) -> DocumentClassDB | None:
        """Get class by ID (not cached)."""
        return self._repo.get(class_id)

    def get_by_class_key(self, class_key: str) -> DocumentClassDB | None:
        """Get class by key (not cached)."""
        return self._repo.get_by_class_key(class_key)

    def class_key_exists(self, class_key: str, exclude_id: int | None = None) -> bool:
        """Check if class key exists (not cached)."""
        return self._repo.class_key_exists(class_key, exclude_id)

    def has_associated_steps(self, class_id: int) -> bool:
        """Check if class has steps (not cached)."""
        return self._repo.has_associated_steps(class_id)

    # Write operations with cache invalidation
    async def create(self, **kwargs) -> DocumentClassDB:
        """Create class and invalidate cache."""
        result = self._repo.create(**kwargs)
        await self._cache.delete_namespace(CacheService.NS_DOCUMENT_CLASSES)
        logger.debug("Document class cache invalidated after create")
        return result

    async def update(self, class_id: int, **kwargs) -> DocumentClassDB | None:
        """Update class and invalidate cache."""
        result = self._repo.update(class_id, **kwargs)
        await self._cache.delete_namespace(CacheService.NS_DOCUMENT_CLASSES)
        logger.debug("Document class cache invalidated after update")
        return result

    async def delete(self, class_id: int) -> bool:
        """Delete class and invalidate cache."""
        result = self._repo.delete(class_id)
        await self._cache.delete_namespace(CacheService.NS_DOCUMENT_CLASSES)
        logger.debug("Document class cache invalidated after delete")
        return result

    async def enable_class(self, class_id: int) -> DocumentClassDB | None:
        """Enable class and invalidate cache."""
        result = self._repo.enable_class(class_id)
        await self._cache.delete_namespace(CacheService.NS_DOCUMENT_CLASSES)
        return result

    async def disable_class(self, class_id: int) -> DocumentClassDB | None:
        """Disable class and invalidate cache."""
        result = self._repo.disable_class(class_id)
        await self._cache.delete_namespace(CacheService.NS_DOCUMENT_CLASSES)
        return result


class CachedAvailableModelRepository:
    """
    Available model repository with caching layer.

    Caches enabled models for fast AI service lookups.
    """

    def __init__(self, db: Session, cache: CacheService):
        """
        Initialize cached available model repository.

        Args:
            db: Database session
            cache: Cache service instance
        """
        self._repo = AvailableModelRepository(db)
        self._cache = cache
        self._ttl = settings.cache_pipeline_ttl_seconds

    async def get_enabled_models(self) -> list[AvailableModelDB]:
        """Get enabled models (cached)."""
        cached = await self._cache.get(CacheService.NS_AVAILABLE_MODELS, "enabled")
        if cached is not None:
            return cached

        models = self._repo.get_enabled_models()
        await self._cache.set(
            CacheService.NS_AVAILABLE_MODELS,
            "enabled",
            models,
            ttl=self._ttl,
        )
        return models

    async def get_all(self) -> list[AvailableModelDB]:
        """Get all models (cached)."""
        cached = await self._cache.get(CacheService.NS_AVAILABLE_MODELS, "all")
        if cached is not None:
            return cached

        models = self._repo.get_all()
        await self._cache.set(
            CacheService.NS_AVAILABLE_MODELS,
            "all",
            models,
            ttl=self._ttl,
        )
        return models

    # Delegate non-cached operations
    def get(self, model_id: int) -> AvailableModelDB | None:
        """Get model by ID (not cached)."""
        return self._repo.get(model_id)

    def get_by_name(self, name: str) -> AvailableModelDB | None:
        """Get model by name (not cached)."""
        return self._repo.get_by_name(name)

    def get_enabled_model_by_id(self, model_id: int) -> AvailableModelDB | None:
        """Get enabled model by ID (not cached)."""
        return self._repo.get_enabled_model_by_id(model_id)

    def model_name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        """Check if model name exists (not cached)."""
        return self._repo.model_name_exists(name, exclude_id)

    # Write operations with cache invalidation
    async def create(self, **kwargs) -> AvailableModelDB:
        """Create model and invalidate cache."""
        result = self._repo.create(**kwargs)
        await self._cache.delete_namespace(CacheService.NS_AVAILABLE_MODELS)
        logger.debug("Available model cache invalidated after create")
        return result

    async def update(self, model_id: int, **kwargs) -> AvailableModelDB | None:
        """Update model and invalidate cache."""
        result = self._repo.update(model_id, **kwargs)
        await self._cache.delete_namespace(CacheService.NS_AVAILABLE_MODELS)
        logger.debug("Available model cache invalidated after update")
        return result

    async def delete(self, model_id: int) -> bool:
        """Delete model and invalidate cache."""
        result = self._repo.delete(model_id)
        await self._cache.delete_namespace(CacheService.NS_AVAILABLE_MODELS)
        logger.debug("Available model cache invalidated after delete")
        return result

    async def enable_model(self, model_id: int) -> AvailableModelDB | None:
        """Enable model and invalidate cache."""
        result = self._repo.enable_model(model_id)
        await self._cache.delete_namespace(CacheService.NS_AVAILABLE_MODELS)
        return result

    async def disable_model(self, model_id: int) -> AvailableModelDB | None:
        """Disable model and invalidate cache."""
        result = self._repo.disable_model(model_id)
        await self._cache.delete_namespace(CacheService.NS_AVAILABLE_MODELS)
        return result


class CachedSystemSettingsRepository:
    """
    System settings repository with caching layer.

    Caches all settings and feature flags for fast lookups.
    """

    def __init__(self, db: Session, cache: CacheService):
        """
        Initialize cached system settings repository.

        Args:
            db: Database session
            cache: Cache service instance
        """
        self._repo = SystemSettingsRepository(db)
        self._cache = cache
        self._ttl = settings.cache_default_ttl_seconds

    async def get_all_settings(self) -> dict[str, str]:
        """Get all settings as dict (cached)."""
        cached = await self._cache.get(CacheService.NS_SYSTEM_SETTINGS, "all")
        if cached is not None:
            return cached

        all_settings = self._repo.get_all_settings()
        await self._cache.set(
            CacheService.NS_SYSTEM_SETTINGS,
            "all",
            all_settings,
            ttl=self._ttl,
        )
        return all_settings

    async def get_feature_flags(self) -> dict[str, bool]:
        """Get feature flags (cached)."""
        cached = await self._cache.get(CacheService.NS_SYSTEM_SETTINGS, "feature_flags")
        if cached is not None:
            return cached

        flags = self._repo.get_feature_flags()
        await self._cache.set(
            CacheService.NS_SYSTEM_SETTINGS,
            "feature_flags",
            flags,
            ttl=self._ttl,
        )
        return flags

    # Delegate non-cached read operations
    def get_by_key(self, key: str) -> SystemSettingsDB | None:
        """Get setting by key (not cached - use get_all_settings)."""
        return self._repo.get_by_key(key)

    def get_value(self, key: str, default: str | None = None) -> str | None:
        """Get setting value (not cached)."""
        return self._repo.get_value(key, default)

    def get_bool_value(self, key: str, default: bool = False) -> bool:
        """Get bool setting (not cached)."""
        return self._repo.get_bool_value(key, default)

    def get_int_value(self, key: str, default: int = 0) -> int:
        """Get int setting (not cached)."""
        return self._repo.get_int_value(key, default)

    def key_exists(self, key: str) -> bool:
        """Check if key exists (not cached)."""
        return self._repo.key_exists(key)

    # Write operations with cache invalidation
    async def set_value(
        self,
        key: str,
        value: str,
        description: str | None = None,
        is_encrypted: bool = False,
    ) -> SystemSettingsDB:
        """Set value and invalidate cache."""
        result = self._repo.set_value(key, value, description, is_encrypted)
        await self._cache.delete_namespace(CacheService.NS_SYSTEM_SETTINGS)
        logger.debug("System settings cache invalidated after set")
        return result

    async def set_bool_value(
        self, key: str, value: bool, description: str | None = None
    ) -> SystemSettingsDB:
        """Set bool value and invalidate cache."""
        result = self._repo.set_bool_value(key, value, description)
        await self._cache.delete_namespace(CacheService.NS_SYSTEM_SETTINGS)
        return result

    async def delete_by_key(self, key: str) -> bool:
        """Delete setting and invalidate cache."""
        result = self._repo.delete_by_key(key)
        await self._cache.delete_namespace(CacheService.NS_SYSTEM_SETTINGS)
        logger.debug("System settings cache invalidated after delete")
        return result

    async def bulk_update(self, settings_dict: dict[str, str]) -> int:
        """Bulk update settings and invalidate cache."""
        result = self._repo.bulk_update(settings_dict)
        await self._cache.delete_namespace(CacheService.NS_SYSTEM_SETTINGS)
        logger.debug("System settings cache invalidated after bulk update")
        return result


class CachedOCRConfigurationRepository:
    """
    OCR configuration repository with caching layer.

    Caches the singleton OCR config for fast access.
    """

    def __init__(self, db: Session, cache: CacheService):
        """
        Initialize cached OCR configuration repository.

        Args:
            db: Database session
            cache: Cache service instance
        """
        self._repo = OCRConfigurationRepository(db)
        self._cache = cache
        self._ttl = settings.cache_default_ttl_seconds

    async def get_config(self) -> OCRConfigurationDB | None:
        """Get OCR config (cached)."""
        cached = await self._cache.get(CacheService.NS_OCR_CONFIG, "current")
        if cached is not None:
            return cached

        config = self._repo.get_config()
        if config:
            await self._cache.set(
                CacheService.NS_OCR_CONFIG,
                "current",
                config,
                ttl=self._ttl,
            )
        return config

    async def get_or_create_config(self) -> OCRConfigurationDB:
        """Get or create OCR config (cached after creation)."""
        cached = await self._cache.get(CacheService.NS_OCR_CONFIG, "current")
        if cached is not None:
            return cached

        config = self._repo.get_or_create_config()
        await self._cache.set(
            CacheService.NS_OCR_CONFIG,
            "current",
            config,
            ttl=self._ttl,
        )
        return config

    def get_selected_engine(self) -> Any:
        """Get selected engine (delegates to base)."""
        return self._repo.get_selected_engine()

    def is_pii_removal_enabled(self) -> bool:
        """Check if PII removal enabled (delegates to base)."""
        return self._repo.is_pii_removal_enabled()

    # Write operations with cache invalidation
    async def update_selected_engine(self, engine: Any) -> OCRConfigurationDB | None:
        """Update engine and invalidate cache."""
        result = self._repo.update_selected_engine(engine)
        await self._cache.delete_namespace(CacheService.NS_OCR_CONFIG)
        logger.debug("OCR config cache invalidated after engine update")
        return result

    async def update_engine_config(
        self, engine: Any, config_data: dict
    ) -> OCRConfigurationDB | None:
        """Update engine config and invalidate cache."""
        result = self._repo.update_engine_config(engine, config_data)
        await self._cache.delete_namespace(CacheService.NS_OCR_CONFIG)
        logger.debug("OCR config cache invalidated after config update")
        return result

    async def toggle_pii_removal(self, enabled: bool) -> OCRConfigurationDB | None:
        """Toggle PII removal and invalidate cache."""
        result = self._repo.toggle_pii_removal(enabled)
        await self._cache.delete_namespace(CacheService.NS_OCR_CONFIG)
        logger.debug("OCR config cache invalidated after PII toggle")
        return result
