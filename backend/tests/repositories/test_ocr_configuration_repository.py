"""
Tests for OCRConfigurationRepository

Tests singleton OCR configuration management including engine selection,
engine-specific configurations, and PII removal settings.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import OCRConfigurationDB, OCREngineEnum
from app.repositories.ocr_configuration_repository import OCRConfigurationRepository


class TestOCRConfigurationRepository:
    """Test suite for OCRConfigurationRepository singleton pattern."""

    @pytest.fixture
    def repository(self, db_session):
        """Create OCRConfigurationRepository instance."""
        return OCRConfigurationRepository(db_session)

    # ==================== GET CONFIG TESTS ====================

    def test_get_config_when_exists(self, repository, create_ocr_configuration):
        """Test retrieving existing OCR configuration."""
        created_config = create_ocr_configuration(
            selected_engine=OCREngineEnum.PADDLEOCR, pii_removal_enabled=True
        )

        config = repository.get_config()

        assert config is not None
        assert config.id == created_config.id
        assert config.selected_engine == OCREngineEnum.PADDLEOCR
        assert config.pii_removal_enabled is True

    def test_get_config_when_not_exists(self, repository):
        """Test get_config returns None when no configuration exists."""
        config = repository.get_config()
        assert config is None

    def test_get_config_returns_singleton(self, repository, create_ocr_configuration):
        """Test that get_config returns the same singleton instance."""
        create_ocr_configuration(selected_engine=OCREngineEnum.MISTRAL_OCR)

        config1 = repository.get_config()
        config2 = repository.get_config()

        assert config1 is not None
        assert config2 is not None
        assert config1.id == config2.id

    # ==================== GET OR CREATE CONFIG TESTS ====================

    def test_get_or_create_config_when_exists(self, repository, create_ocr_configuration):
        """Test get_or_create_config returns existing configuration."""
        existing = create_ocr_configuration(
            selected_engine=OCREngineEnum.PADDLEOCR, pii_removal_enabled=False
        )

        config = repository.get_or_create_config()

        assert config.id == existing.id
        assert config.selected_engine == OCREngineEnum.PADDLEOCR
        assert config.pii_removal_enabled is False

    def test_get_or_create_config_creates_default(self, repository):
        """Test get_or_create_config creates default configuration when none exists."""
        config = repository.get_or_create_config()

        assert config is not None
        assert config.id is not None
        assert config.selected_engine == OCREngineEnum.MISTRAL_OCR
        assert config.pii_removal_enabled is True

    def test_get_or_create_config_idempotent(self, repository):
        """Test that calling get_or_create_config multiple times returns same instance."""
        config1 = repository.get_or_create_config()
        config2 = repository.get_or_create_config()

        assert config1.id == config2.id

    # ==================== UPDATE SELECTED ENGINE TESTS ====================

    def test_update_selected_engine_success(self, repository, create_ocr_configuration):
        """Test updating the selected OCR engine."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        updated = repository.update_selected_engine(OCREngineEnum.MISTRAL_OCR)

        assert updated is not None
        assert updated.selected_engine == OCREngineEnum.MISTRAL_OCR

    def test_update_selected_engine_all_types(self, repository, create_ocr_configuration):
        """Test updating to all available OCR engine types."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        # Test each engine type
        for engine in [OCREngineEnum.MISTRAL_OCR, OCREngineEnum.PADDLEOCR]:
            updated = repository.update_selected_engine(engine)
            assert updated.selected_engine == engine

    def test_update_selected_engine_when_no_config(self, repository):
        """Test update_selected_engine returns None when no configuration exists."""
        result = repository.update_selected_engine(OCREngineEnum.MISTRAL_OCR)
        assert result is None

    def test_update_selected_engine_persists(self, repository, create_ocr_configuration):
        """Test that engine update persists across queries."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        repository.update_selected_engine(OCREngineEnum.MISTRAL_OCR)
        reloaded = repository.get_config()

        assert reloaded.selected_engine == OCREngineEnum.MISTRAL_OCR

    # ==================== UPDATE ENGINE CONFIG TESTS ====================

    def test_update_paddleocr_config(self, repository, create_ocr_configuration):
        """Test updating PaddleOCR engine-specific configuration."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        paddle_config = {"use_gpu": True, "lang": "german"}
        updated = repository.update_engine_config(OCREngineEnum.PADDLEOCR, paddle_config)

        assert updated is not None
        assert updated.paddleocr_config == paddle_config

    def test_update_mistral_ocr_config(self, repository, create_ocr_configuration):
        """Test updating Mistral OCR engine-specific configuration."""
        create_ocr_configuration(selected_engine=OCREngineEnum.MISTRAL_OCR)

        mistral_config = {"model": "mistral-ocr-latest", "timeout": 60}
        updated = repository.update_engine_config(OCREngineEnum.MISTRAL_OCR, mistral_config)

        assert updated is not None
        assert updated.mistral_ocr_config == mistral_config

    def test_update_engine_config_when_no_config(self, repository):
        """Test update_engine_config returns None when no configuration exists."""
        result = repository.update_engine_config(OCREngineEnum.PADDLEOCR, {"use_gpu": True})
        assert result is None

    def test_update_engine_config_persists(self, repository, create_ocr_configuration):
        """Test that engine config updates persist across queries."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        paddle_config = {"use_gpu": True, "lang": "german"}
        repository.update_engine_config(OCREngineEnum.PADDLEOCR, paddle_config)
        reloaded = repository.get_config()

        assert reloaded.paddleocr_config == paddle_config

    def test_update_engine_config_multiple_engines(self, repository, create_ocr_configuration):
        """Test updating configurations for multiple engines independently."""
        create_ocr_configuration(selected_engine=OCREngineEnum.MISTRAL_OCR)

        paddle_config = {"use_gpu": True}
        mistral_config = {"model": "mistral-ocr-latest"}

        repository.update_engine_config(OCREngineEnum.PADDLEOCR, paddle_config)
        repository.update_engine_config(OCREngineEnum.MISTRAL_OCR, mistral_config)

        config = repository.get_config()
        assert config.paddleocr_config == paddle_config
        assert config.mistral_ocr_config == mistral_config

    def test_update_engine_config_overwrites_previous(self, repository, create_ocr_configuration):
        """Test that updating engine config overwrites previous configuration."""
        create_ocr_configuration(
            selected_engine=OCREngineEnum.PADDLEOCR,
            paddleocr_config={"use_gpu": False, "lang": "english"},
        )

        new_config = {"use_gpu": True, "lang": "german"}
        updated = repository.update_engine_config(OCREngineEnum.PADDLEOCR, new_config)

        assert updated.paddleocr_config == new_config

    # ==================== TOGGLE PII REMOVAL TESTS ====================

    def test_toggle_pii_removal_enable(self, repository, create_ocr_configuration):
        """Test enabling PII removal."""
        create_ocr_configuration(pii_removal_enabled=False)

        updated = repository.toggle_pii_removal(True)

        assert updated is not None
        assert updated.pii_removal_enabled is True

    def test_toggle_pii_removal_disable(self, repository, create_ocr_configuration):
        """Test disabling PII removal."""
        create_ocr_configuration(pii_removal_enabled=True)

        updated = repository.toggle_pii_removal(False)

        assert updated is not None
        assert updated.pii_removal_enabled is False

    def test_toggle_pii_removal_when_no_config(self, repository):
        """Test toggle_pii_removal returns None when no configuration exists."""
        result = repository.toggle_pii_removal(True)
        assert result is None

    def test_toggle_pii_removal_persists(self, repository, create_ocr_configuration):
        """Test that PII removal toggle persists across queries."""
        create_ocr_configuration(pii_removal_enabled=False)

        repository.toggle_pii_removal(True)
        reloaded = repository.get_config()

        assert reloaded.pii_removal_enabled is True

    def test_toggle_pii_removal_multiple_times(self, repository, create_ocr_configuration):
        """Test toggling PII removal multiple times."""
        create_ocr_configuration(pii_removal_enabled=True)

        # Toggle off
        repository.toggle_pii_removal(False)
        assert repository.get_config().pii_removal_enabled is False

        # Toggle on
        repository.toggle_pii_removal(True)
        assert repository.get_config().pii_removal_enabled is True

        # Toggle off again
        repository.toggle_pii_removal(False)
        assert repository.get_config().pii_removal_enabled is False

    # ==================== GET SELECTED ENGINE TESTS ====================

    def test_get_selected_engine_when_exists(self, repository, create_ocr_configuration):
        """Test getting selected engine when configuration exists."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        engine = repository.get_selected_engine()

        assert engine == OCREngineEnum.PADDLEOCR

    def test_get_selected_engine_default_when_no_config(self, repository):
        """Test get_selected_engine returns MISTRAL_OCR default when no configuration exists."""
        engine = repository.get_selected_engine()
        assert engine == OCREngineEnum.MISTRAL_OCR

    def test_get_selected_engine_all_types(self, repository, create_ocr_configuration):
        """Test getting all engine types."""
        for engine_type in [
            OCREngineEnum.PADDLEOCR,
            OCREngineEnum.MISTRAL_OCR,
        ]:
            create_ocr_configuration(selected_engine=engine_type)

            engine = repository.get_selected_engine()
            assert engine == engine_type

            # Clean up for next iteration
            config = repository.get_config()
            repository.delete(config.id)

    # ==================== IS PII REMOVAL ENABLED TESTS ====================

    def test_is_pii_removal_enabled_true(self, repository, create_ocr_configuration):
        """Test checking PII removal when enabled."""
        create_ocr_configuration(pii_removal_enabled=True)

        result = repository.is_pii_removal_enabled()

        assert result is True

    def test_is_pii_removal_enabled_false(self, repository, create_ocr_configuration):
        """Test checking PII removal when disabled."""
        create_ocr_configuration(pii_removal_enabled=False)

        result = repository.is_pii_removal_enabled()

        assert result is False

    def test_is_pii_removal_enabled_default_when_no_config(self, repository):
        """Test is_pii_removal_enabled returns True (safe default) when no configuration exists."""
        result = repository.is_pii_removal_enabled()
        assert result is True

    # ==================== INTEGRATION TESTS ====================

    def test_complete_ocr_configuration_workflow(self, repository):
        """Test complete OCR configuration management workflow."""
        # Start with no config
        assert repository.get_config() is None

        # Create default config
        config = repository.get_or_create_config()
        assert config.selected_engine == OCREngineEnum.MISTRAL_OCR
        assert config.pii_removal_enabled is True

        # Update engine
        repository.update_selected_engine(OCREngineEnum.PADDLEOCR)
        assert repository.get_selected_engine() == OCREngineEnum.PADDLEOCR

        # Configure PaddleOCR
        paddle_config = {"use_gpu": True, "lang": "german"}
        repository.update_engine_config(OCREngineEnum.PADDLEOCR, paddle_config)
        assert repository.get_config().paddleocr_config == paddle_config

        # Disable PII removal
        repository.toggle_pii_removal(False)
        assert repository.is_pii_removal_enabled() is False

        # Switch to Mistral OCR
        repository.update_selected_engine(OCREngineEnum.MISTRAL_OCR)
        mistral_config = {"model": "mistral-ocr-latest"}
        repository.update_engine_config(OCREngineEnum.MISTRAL_OCR, mistral_config)

        # Verify final state
        final_config = repository.get_config()
        assert final_config.selected_engine == OCREngineEnum.MISTRAL_OCR
        assert final_config.mistral_ocr_config == mistral_config
        assert final_config.paddleocr_config == paddle_config  # Previous config preserved
        assert final_config.pii_removal_enabled is False

    def test_singleton_pattern_enforcement(self, repository, create_ocr_configuration):
        """Test that repository enforces singleton pattern for OCR configuration."""
        # Create first config
        config1 = create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        # Get config should return the same instance
        config2 = repository.get_config()
        assert config1.id == config2.id

        # Count total configs (should be exactly 1)
        all_configs = repository.get_all()
        assert len(all_configs) == 1

    def test_engine_config_independence(self, repository, create_ocr_configuration):
        """Test that each engine's configuration is independent."""
        create_ocr_configuration(selected_engine=OCREngineEnum.MISTRAL_OCR)

        # Configure both engines differently
        repository.update_engine_config(OCREngineEnum.PADDLEOCR, {"setting": "paddle"})
        repository.update_engine_config(OCREngineEnum.MISTRAL_OCR, {"setting": "mistral"})

        config = repository.get_config()

        # Verify each engine has its own config
        assert config.paddleocr_config["setting"] == "paddle"
        assert config.mistral_ocr_config["setting"] == "mistral"

    def test_updates_preserve_other_fields(self, repository, create_ocr_configuration):
        """Test that updating one field doesn't affect others."""
        create_ocr_configuration(
            selected_engine=OCREngineEnum.PADDLEOCR,
            pii_removal_enabled=True,
            paddleocr_config={"use_gpu": False},
        )

        # Update engine
        repository.update_selected_engine(OCREngineEnum.MISTRAL_OCR)
        config = repository.get_config()
        assert config.pii_removal_enabled is True
        assert config.paddleocr_config == {"use_gpu": False}

        # Update PII removal
        repository.toggle_pii_removal(False)
        config = repository.get_config()
        assert config.selected_engine == OCREngineEnum.MISTRAL_OCR
        assert config.paddleocr_config == {"use_gpu": False}

        # Update engine config
        repository.update_engine_config(OCREngineEnum.MISTRAL_OCR, {"model": "latest"})
        config = repository.get_config()
        assert config.selected_engine == OCREngineEnum.MISTRAL_OCR
        assert config.pii_removal_enabled is False
        assert config.paddleocr_config == {"use_gpu": False}

    # ==================== EDGE CASE TESTS ====================

    def test_update_with_empty_config_dict(self, repository, create_ocr_configuration):
        """Test updating engine config with empty dictionary."""
        create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)

        updated = repository.update_engine_config(OCREngineEnum.PADDLEOCR, {})

        assert updated is not None
        assert updated.paddleocr_config == {}

    def test_update_with_complex_config_structure(self, repository, create_ocr_configuration):
        """Test updating engine config with nested/complex structures."""
        create_ocr_configuration(selected_engine=OCREngineEnum.MISTRAL_OCR)

        complex_config = {
            "model": "mistral-ocr-latest",
            "options": {"include_image_base64": False, "page_limit": 50},
            "timeouts": [30, 60, 120],
            "enabled": True,
        }

        updated = repository.update_engine_config(OCREngineEnum.MISTRAL_OCR, complex_config)

        assert updated is not None
        assert updated.mistral_ocr_config == complex_config

    def test_get_or_create_only_creates_once(self, repository):
        """Test that get_or_create_config doesn't create duplicates."""
        # Call multiple times
        config1 = repository.get_or_create_config()
        config2 = repository.get_or_create_config()
        config3 = repository.get_or_create_config()

        # All should be the same instance
        assert config1.id == config2.id == config3.id

        # Only one config should exist
        all_configs = repository.get_all()
        assert len(all_configs) == 1
