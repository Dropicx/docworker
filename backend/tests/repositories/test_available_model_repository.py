"""
Tests for AvailableModelRepository

Tests AI model registry operations including model management,
provider filtering, and enable/disable functionality.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import AvailableModelDB, ModelProvider
from app.repositories.available_model_repository import AvailableModelRepository


class TestAvailableModelRepository:
    """Test suite for AvailableModelRepository operations."""

    @pytest.fixture
    def repository(self, db_session):
        """Create AvailableModelRepository instance."""
        return AvailableModelRepository(db_session)

    # ==================== GET BY NAME TESTS ====================

    def test_get_by_name_existing(self, repository, create_available_model):
        """Test retrieving model by name."""
        create_available_model(name="Meta-Llama-3_3-70B-Instruct", display_name="Llama 3.3 70B")

        model = repository.get_by_name("Meta-Llama-3_3-70B-Instruct")

        assert model is not None
        assert model.name == "Meta-Llama-3_3-70B-Instruct"
        assert model.display_name == "Llama 3.3 70B"

    def test_get_by_name_nonexistent(self, repository):
        """Test get_by_name returns None for non-existent model."""
        result = repository.get_by_name("Nonexistent-Model")
        assert result is None

    def test_get_by_name_case_sensitive(self, repository, create_available_model):
        """Test that name matching is case-sensitive."""
        create_available_model(name="Meta-Llama-3_3-70B-Instruct")

        assert repository.get_by_name("Meta-Llama-3_3-70B-Instruct") is not None
        assert repository.get_by_name("meta-llama-3_3-70b-instruct") is None

    # ==================== GET ENABLED/DISABLED MODELS TESTS ====================

    def test_get_enabled_models(self, repository, create_available_model):
        """Test retrieving only enabled models."""
        create_available_model(name="Enabled-1", display_name="Enabled Model 1", is_enabled=True)
        create_available_model(name="Disabled-1", display_name="Disabled Model", is_enabled=False)
        create_available_model(name="Enabled-2", display_name="Enabled Model 2", is_enabled=True)

        enabled_models = repository.get_enabled_models()

        assert len(enabled_models) == 2
        assert all(model.is_enabled for model in enabled_models)

    def test_get_enabled_models_ordered_by_display_name(self, repository, create_available_model):
        """Test that enabled models are ordered by display name."""
        create_available_model(name="M3", display_name="Zebra Model", is_enabled=True)
        create_available_model(name="M1", display_name="Alpha Model", is_enabled=True)
        create_available_model(name="M2", display_name="Beta Model", is_enabled=True)

        enabled_models = repository.get_enabled_models()

        assert enabled_models[0].display_name == "Alpha Model"
        assert enabled_models[1].display_name == "Beta Model"
        assert enabled_models[2].display_name == "Zebra Model"

    def test_get_enabled_models_empty(self, repository, create_available_model):
        """Test get_enabled_models when all models are disabled."""
        create_available_model(name="Disabled-1", is_enabled=False)
        create_available_model(name="Disabled-2", is_enabled=False)

        enabled_models = repository.get_enabled_models()

        assert len(enabled_models) == 0

    def test_get_disabled_models(self, repository, create_available_model):
        """Test retrieving only disabled models."""
        create_available_model(name="Enabled", is_enabled=True)
        create_available_model(name="Disabled-1", display_name="Disabled 1", is_enabled=False)
        create_available_model(name="Disabled-2", display_name="Disabled 2", is_enabled=False)

        disabled_models = repository.get_disabled_models()

        assert len(disabled_models) == 2
        assert all(not model.is_enabled for model in disabled_models)

    def test_get_disabled_models_ordered_by_display_name(self, repository, create_available_model):
        """Test that disabled models are ordered by display name."""
        create_available_model(name="M3", display_name="Zebra", is_enabled=False)
        create_available_model(name="M1", display_name="Alpha", is_enabled=False)
        create_available_model(name="M2", display_name="Beta", is_enabled=False)

        disabled_models = repository.get_disabled_models()

        assert disabled_models[0].display_name == "Alpha"
        assert disabled_models[1].display_name == "Beta"
        assert disabled_models[2].display_name == "Zebra"

    # ==================== GET ENABLED MODEL BY ID TESTS ====================

    def test_get_enabled_model_by_id_success(self, repository, create_available_model):
        """Test retrieving enabled model by ID."""
        enabled_model = create_available_model(name="Enabled-Model", is_enabled=True)

        result = repository.get_enabled_model_by_id(enabled_model.id)

        assert result is not None
        assert result.id == enabled_model.id
        assert result.is_enabled is True

    def test_get_enabled_model_by_id_disabled_returns_none(
        self, repository, create_available_model
    ):
        """Test that disabled model returns None even if ID exists."""
        disabled_model = create_available_model(name="Disabled-Model", is_enabled=False)

        result = repository.get_enabled_model_by_id(disabled_model.id)

        assert result is None

    def test_get_enabled_model_by_id_nonexistent(self, repository):
        """Test get_enabled_model_by_id returns None for non-existent ID."""
        result = repository.get_enabled_model_by_id(999999)
        assert result is None

    # ==================== GET MODELS BY PROVIDER TESTS ====================

    def test_get_models_by_provider_ovh(self, repository, create_available_model):
        """Test retrieving models by OVH provider."""
        create_available_model(name="OVH-1", display_name="OVH Model 1", provider=ModelProvider.OVH)
        create_available_model(
            name="OpenAI-1", display_name="OpenAI Model", provider=ModelProvider.OPENAI
        )
        create_available_model(name="OVH-2", display_name="OVH Model 2", provider=ModelProvider.OVH)

        ovh_models = repository.get_models_by_provider(ModelProvider.OVH)

        assert len(ovh_models) == 2
        assert all(model.provider == ModelProvider.OVH for model in ovh_models)

    def test_get_models_by_provider_ordered_by_display_name(
        self, repository, create_available_model
    ):
        """Test that models by provider are ordered by display name."""
        create_available_model(name="M3", display_name="Zebra", provider=ModelProvider.OVH)
        create_available_model(name="M1", display_name="Alpha", provider=ModelProvider.OVH)
        create_available_model(name="M2", display_name="Beta", provider=ModelProvider.OVH)

        models = repository.get_models_by_provider(ModelProvider.OVH)

        assert models[0].display_name == "Alpha"
        assert models[1].display_name == "Beta"
        assert models[2].display_name == "Zebra"

    def test_get_models_by_provider_includes_disabled(self, repository, create_available_model):
        """Test that get_models_by_provider includes both enabled and disabled models."""
        create_available_model(name="Enabled", provider=ModelProvider.OVH, is_enabled=True)
        create_available_model(name="Disabled", provider=ModelProvider.OVH, is_enabled=False)

        models = repository.get_models_by_provider(ModelProvider.OVH)

        assert len(models) == 2

    def test_get_models_by_provider_empty(self, repository, create_available_model):
        """Test get_models_by_provider when no models exist for provider."""
        create_available_model(name="OVH-Model", provider=ModelProvider.OVH)

        anthropic_models = repository.get_models_by_provider(ModelProvider.ANTHROPIC)

        assert len(anthropic_models) == 0

    def test_get_models_by_provider_all_types(self, repository, create_available_model):
        """Test retrieving models for all provider types."""
        providers = [
            ModelProvider.OVH,
            ModelProvider.OPENAI,
            ModelProvider.ANTHROPIC,
            ModelProvider.LOCAL,
        ]

        for provider in providers:
            create_available_model(name=f"{provider.value}-Model", provider=provider)

        for provider in providers:
            models = repository.get_models_by_provider(provider)
            assert len(models) == 1
            assert models[0].provider == provider

    # ==================== ENABLE/DISABLE MODEL TESTS ====================

    def test_enable_model(self, repository, create_available_model):
        """Test enabling a disabled model."""
        model = create_available_model(name="Test-Model", is_enabled=False)

        updated = repository.enable_model(model.id)

        assert updated is not None
        assert updated.is_enabled is True

    def test_enable_already_enabled_model(self, repository, create_available_model):
        """Test enabling an already enabled model."""
        model = create_available_model(name="Test-Model", is_enabled=True)

        updated = repository.enable_model(model.id)

        assert updated is not None
        assert updated.is_enabled is True

    def test_enable_nonexistent_model(self, repository):
        """Test enabling non-existent model returns None."""
        result = repository.enable_model(999999)
        assert result is None

    def test_disable_model(self, repository, create_available_model):
        """Test disabling an enabled model."""
        model = create_available_model(name="Test-Model", is_enabled=True)

        updated = repository.disable_model(model.id)

        assert updated is not None
        assert updated.is_enabled is False

    def test_disable_already_disabled_model(self, repository, create_available_model):
        """Test disabling an already disabled model."""
        model = create_available_model(name="Test-Model", is_enabled=False)

        updated = repository.disable_model(model.id)

        assert updated is not None
        assert updated.is_enabled is False

    def test_disable_nonexistent_model(self, repository):
        """Test disabling non-existent model returns None."""
        result = repository.disable_model(999999)
        assert result is None

    def test_enable_disable_workflow(self, repository, create_available_model):
        """Test complete enable/disable workflow."""
        model = create_available_model(name="Test-Model", is_enabled=True)

        # Initially enabled
        assert repository.get_by_id(model.id).is_enabled is True
        assert len(repository.get_enabled_models()) == 1
        assert len(repository.get_disabled_models()) == 0

        # Disable
        repository.disable_model(model.id)
        assert repository.get_by_id(model.id).is_enabled is False
        assert len(repository.get_enabled_models()) == 0
        assert len(repository.get_disabled_models()) == 1

        # Re-enable
        repository.enable_model(model.id)
        assert repository.get_by_id(model.id).is_enabled is True
        assert len(repository.get_enabled_models()) == 1
        assert len(repository.get_disabled_models()) == 0

    # ==================== MODEL NAME EXISTS TESTS ====================

    def test_model_name_exists_true(self, repository, create_available_model):
        """Test model_name_exists returns True for existing name."""
        create_available_model(name="Existing-Model")

        assert repository.model_name_exists("Existing-Model") is True

    def test_model_name_exists_false(self, repository):
        """Test model_name_exists returns False for non-existent name."""
        assert repository.model_name_exists("Nonexistent-Model") is False

    def test_model_name_exists_case_sensitive(self, repository, create_available_model):
        """Test that model_name_exists is case-sensitive."""
        create_available_model(name="CaseSensitive-Model")

        assert repository.model_name_exists("CaseSensitive-Model") is True
        assert repository.model_name_exists("casesensitive-model") is False

    def test_model_name_exists_with_exclusion(self, repository, create_available_model):
        """Test model_name_exists with exclude_id parameter."""
        model = create_available_model(name="Test-Model")

        # Without exclusion
        assert repository.model_name_exists("Test-Model") is True

        # With exclusion of the model itself
        assert repository.model_name_exists("Test-Model", exclude_id=model.id) is False

    def test_model_name_exists_with_exclusion_multiple_records(
        self, repository, create_available_model
    ):
        """Test model_name_exists with exclusion when multiple records exist."""
        model1 = create_available_model(name="Model-1")
        model2 = create_available_model(name="Model-2")

        # Excluding model1 should still not find "Model-1"
        assert repository.model_name_exists("Model-1", exclude_id=model1.id) is False

        # But excluding model2 should still find "Model-1"
        assert repository.model_name_exists("Model-1", exclude_id=model2.id) is True

    # ==================== STATISTICS TESTS ====================

    def test_get_model_statistics_comprehensive(self, repository, create_available_model):
        """Test getting comprehensive model statistics."""
        create_available_model(name="Enabled-1", is_enabled=True)
        create_available_model(name="Enabled-2", is_enabled=True)
        create_available_model(name="Enabled-3", is_enabled=True)
        create_available_model(name="Disabled-1", is_enabled=False)
        create_available_model(name="Disabled-2", is_enabled=False)

        stats = repository.get_model_statistics()

        assert stats["total_models"] == 5
        assert stats["enabled_models"] == 3
        assert stats["disabled_models"] == 2

    def test_get_model_statistics_empty_database(self, repository):
        """Test statistics on empty database."""
        stats = repository.get_model_statistics()

        assert stats["total_models"] == 0
        assert stats["enabled_models"] == 0
        assert stats["disabled_models"] == 0

    def test_get_model_statistics_all_enabled(self, repository, create_available_model):
        """Test statistics when all models are enabled."""
        create_available_model(name="Model-1", is_enabled=True)
        create_available_model(name="Model-2", is_enabled=True)
        create_available_model(name="Model-3", is_enabled=True)

        stats = repository.get_model_statistics()

        assert stats["total_models"] == 3
        assert stats["enabled_models"] == 3
        assert stats["disabled_models"] == 0

    def test_get_model_statistics_all_disabled(self, repository, create_available_model):
        """Test statistics when all models are disabled."""
        create_available_model(name="Model-1", is_enabled=False)
        create_available_model(name="Model-2", is_enabled=False)

        stats = repository.get_model_statistics()

        assert stats["total_models"] == 2
        assert stats["enabled_models"] == 0
        assert stats["disabled_models"] == 2

    # ==================== INTEGRATION TESTS ====================

    def test_complete_model_lifecycle(self, repository):
        """Test complete model management lifecycle."""
        # Create model
        model = repository.create(
            name="Test-Lifecycle-Model",
            display_name="Test Lifecycle Model",
            provider=ModelProvider.OVH,
            description="Test model for lifecycle",
            max_tokens=8192,
            supports_vision=False,
            price_input_per_1m_tokens=0.54,
            price_output_per_1m_tokens=0.81,
            is_enabled=True,
        )

        # Verify created
        assert model.id is not None
        assert repository.model_name_exists("Test-Lifecycle-Model") is True

        # Retrieve by name
        retrieved = repository.get_by_name("Test-Lifecycle-Model")
        assert retrieved.id == model.id

        # Check it's in enabled models
        assert model in repository.get_enabled_models()

        # Disable
        repository.disable_model(model.id)
        assert repository.get_enabled_model_by_id(model.id) is None
        assert model.id not in [m.id for m in repository.get_enabled_models()]

        # Re-enable
        repository.enable_model(model.id)
        assert repository.get_enabled_model_by_id(model.id) is not None

        # Delete
        repository.delete(model.id)
        assert repository.get_by_name("Test-Lifecycle-Model") is None
        assert not repository.model_name_exists("Test-Lifecycle-Model")

    def test_multi_provider_filtering(self, repository, create_available_model):
        """Test filtering models by multiple providers."""
        # Create models for different providers
        create_available_model(name="OVH-1", provider=ModelProvider.OVH)
        create_available_model(name="OVH-2", provider=ModelProvider.OVH)
        create_available_model(name="OpenAI-1", provider=ModelProvider.OPENAI)
        create_available_model(name="Anthropic-1", provider=ModelProvider.ANTHROPIC)
        create_available_model(name="Local-1", provider=ModelProvider.LOCAL)

        # Verify counts per provider
        assert len(repository.get_models_by_provider(ModelProvider.OVH)) == 2
        assert len(repository.get_models_by_provider(ModelProvider.OPENAI)) == 1
        assert len(repository.get_models_by_provider(ModelProvider.ANTHROPIC)) == 1
        assert len(repository.get_models_by_provider(ModelProvider.LOCAL)) == 1

        # Total should be 5
        assert len(repository.get_all()) == 5

    def test_enabled_status_persists_across_queries(self, repository, create_available_model):
        """Test that enabled status persists correctly."""
        model = create_available_model(name="Persist-Test", is_enabled=True)

        # Disable
        repository.disable_model(model.id)

        # Query in different ways
        assert repository.get_by_id(model.id).is_enabled is False
        assert repository.get_by_name("Persist-Test").is_enabled is False
        assert model.id not in [m.id for m in repository.get_enabled_models()]

    # ==================== EDGE CASE TESTS ====================

    def test_model_with_all_optional_fields(self, repository):
        """Test creating model with all optional fields populated."""
        model = repository.create(
            name="Full-Model",
            display_name="Full Model",
            provider=ModelProvider.OVH,
            description="Model with all fields",
            max_tokens=16384,
            supports_vision=True,
            price_input_per_1m_tokens=1.0,
            price_output_per_1m_tokens=2.0,
            model_config={"temperature": 0.7, "top_p": 0.9},
            is_enabled=True,
        )

        retrieved = repository.get_by_name("Full-Model")
        assert retrieved.description == "Model with all fields"
        assert retrieved.max_tokens == 16384
        assert retrieved.supports_vision is True
        assert retrieved.model_config == {"temperature": 0.7, "top_p": 0.9}

    def test_model_with_minimal_fields(self, repository):
        """Test creating model with only required fields."""
        model = repository.create(
            name="Minimal-Model", display_name="Minimal Model", provider=ModelProvider.LOCAL
        )

        assert model.id is not None
        assert model.name == "Minimal-Model"
        assert model.is_enabled is True  # Default value

    def test_operations_preserve_other_fields(self, repository, create_available_model):
        """Test that enable/disable operations preserve other fields."""
        model = create_available_model(
            name="Preserve-Test",
            display_name="Original Display",
            provider=ModelProvider.OVH,
            description="Original description",
            max_tokens=8192,
            is_enabled=True,
        )

        # Disable model
        repository.disable_model(model.id)

        # Verify other fields unchanged
        reloaded = repository.get_by_id(model.id)
        assert reloaded.display_name == "Original Display"
        assert reloaded.provider == ModelProvider.OVH
        assert reloaded.description == "Original description"
        assert reloaded.max_tokens == 8192
