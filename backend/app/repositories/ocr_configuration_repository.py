"""
OCR Configuration Repository

Handles database operations for OCR engine configuration.
"""

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.repositories.base_repository import BaseRepository


class OCRConfigurationRepository(BaseRepository[OCRConfigurationDB]):
    """
    Repository for OCR Configuration operations.

    Manages global OCR engine settings (singleton pattern).
    """

    def __init__(self, db: Session):
        """
        Initialize OCR configuration repository.

        Args:
            db: Database session
        """
        super().__init__(db, OCRConfigurationDB)

    def get_config(self) -> OCRConfigurationDB | None:
        """
        Get the current OCR configuration.

        There should only be one configuration record (singleton).

        Returns:
            Current OCR configuration or None if not found
        """
        return self.db.query(self.model).first()

    def get_or_create_config(self) -> OCRConfigurationDB:
        """
        Get existing config or create default if not exists.

        Returns:
            OCR configuration instance
        """
        config = self.get_config()
        if not config:
            config = self.create(selected_engine=OCREngineEnum.MISTRAL_OCR, pii_removal_enabled=True)
        return config

    def update_selected_engine(self, engine: OCREngineEnum) -> OCRConfigurationDB | None:
        """
        Update the selected OCR engine.

        Args:
            engine: OCR engine to use

        Returns:
            Updated configuration or None if not found
        """
        config = self.get_config()
        if not config:
            return None

        return self.update(config.id, selected_engine=engine)

    def update_engine_config(
        self, engine: OCREngineEnum, config_data: dict
    ) -> OCRConfigurationDB | None:
        """
        Update configuration for a specific OCR engine.

        Args:
            engine: OCR engine to configure
            config_data: Engine-specific configuration

        Returns:
            Updated configuration or None if not found
        """
        config = self.get_config()
        if not config:
            return None

        config_field_map = {
            OCREngineEnum.PADDLEOCR: "paddleocr_config",
            OCREngineEnum.VISION_LLM: "vision_llm_config",
            OCREngineEnum.HYBRID: "hybrid_config",
            OCREngineEnum.MISTRAL_OCR: "mistral_ocr_config",
        }

        field_name = config_field_map.get(engine)
        if not field_name:
            return None

        return self.update(config.id, **{field_name: config_data})

    def toggle_pii_removal(self, enabled: bool) -> OCRConfigurationDB | None:
        """
        Enable or disable PII removal.

        Args:
            enabled: True to enable PII removal, False to disable

        Returns:
            Updated configuration or None if not found
        """
        config = self.get_config()
        if not config:
            return None

        return self.update(config.id, pii_removal_enabled=enabled)

    def get_selected_engine(self) -> OCREngineEnum:
        """
        Get the currently selected OCR engine.

        Returns:
            Selected engine, defaults to HYBRID if config not found
        """
        config = self.get_config()
        if not config:
            return OCREngineEnum.HYBRID

        return config.selected_engine

    def is_pii_removal_enabled(self) -> bool:
        """
        Check if PII removal is enabled.

        Returns:
            True if enabled, False otherwise (defaults to True)
        """
        config = self.get_config()
        if not config:
            return True  # Default to enabled for privacy

        return config.pii_removal_enabled
