"""
Unit Tests for ModularPipelineExecutor

Tests dynamic pipeline execution with branching logic and stop conditions.
Mocks database and AI calls to ensure fast, isolated unit tests.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.modular_pipeline_executor import ModularPipelineExecutor, ModularPipelineManager
from app.database.modular_pipeline_models import (
    DynamicPipelineStepDB,
    AvailableModelDB,
    OCRConfigurationDB,
    PipelineJobDB,
    StepExecutionStatus,
    DocumentClassDB,
)


class TestModularPipelineExecutorInitialization:
    """Test suite for ModularPipelineExecutor initialization"""

    def test_initialization(self):
        """Test executor initializes with database session"""
        mock_session = Mock()

        with (
            patch("app.services.modular_pipeline_executor.OVHClient"),
            patch("app.services.modular_pipeline_executor.DocumentClassManager"),
            patch("app.services.modular_pipeline_executor.AICostTracker"),
        ):
            executor = ModularPipelineExecutor(session=mock_session)

            assert executor is not None
            assert executor.session == mock_session
            assert executor.ovh_client is not None
            assert executor.doc_class_manager is not None
            assert executor.cost_tracker is not None


class TestConfigurationLoading:
    """Test suite for configuration loading methods"""

    @pytest.fixture
    def executor(self):
        """Create executor instance for testing"""
        mock_session = Mock()
        with (
            patch("app.services.modular_pipeline_executor.OVHClient"),
            patch("app.services.modular_pipeline_executor.DocumentClassManager"),
            patch("app.services.modular_pipeline_executor.AICostTracker"),
        ):
            return ModularPipelineExecutor(session=mock_session)

    @pytest.fixture
    def mock_step(self):
        """Create a mock pipeline step"""
        step = Mock(spec=DynamicPipelineStepDB)
        step.id = 1
        step.name = "Test Step"
        step.order = 1
        step.enabled = True
        step.is_branching_step = False
        step.document_class_id = None
        step.post_branching = False
        return step

    def test_load_pipeline_steps_success(self, executor, mock_step):
        """Test loading all enabled pipeline steps"""
        mock_query = Mock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_step]
        executor.session.query.return_value = mock_query

        steps = executor.load_pipeline_steps()

        assert len(steps) == 1
        assert steps[0] == mock_step
        executor.session.query.assert_called_once()

    def test_load_pipeline_steps_empty(self, executor):
        """Test loading steps returns empty list when none found"""
        mock_query = Mock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = []
        executor.session.query.return_value = mock_query

        steps = executor.load_pipeline_steps()

        assert steps == []

    def test_load_pipeline_steps_error(self, executor):
        """Test loading steps handles errors gracefully"""
        executor.session.query.side_effect = Exception("Database error")

        steps = executor.load_pipeline_steps()

        assert steps == []

    def test_load_universal_steps(self, executor, mock_step):
        """Test loading pre-branching universal steps"""
        mock_step.post_branching = False
        mock_step.document_class_id = None

        # Mock step_repository instead of session.query
        executor.step_repository = Mock()
        executor.step_repository.get_universal_steps.return_value = [mock_step]

        steps = executor.load_universal_steps()

        assert len(steps) == 1
        # Verify repository was called
        executor.step_repository.get_universal_steps.assert_called_once()

    def test_load_post_branching_steps(self, executor, mock_step):
        """Test loading post-branching universal steps"""
        mock_step.post_branching = True
        mock_step.document_class_id = None

        # Mock step_repository instead of session.query
        executor.step_repository = Mock()
        executor.step_repository.get_post_branching_steps.return_value = [mock_step]

        steps = executor.load_post_branching_steps()

        assert len(steps) == 1
        # Verify repository was called
        executor.step_repository.get_post_branching_steps.assert_called_once()

    def test_load_steps_by_document_class(self, executor, mock_step):
        """Test loading document class-specific steps"""
        mock_step.document_class_id = 3

        mock_query = Mock()
        mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_step]
        executor.session.query.return_value = mock_query

        steps = executor.load_steps_by_document_class(document_class_id=3)

        assert len(steps) == 1
        executor.session.query.return_value.filter_by.assert_called_with(
            enabled=True, document_class_id=3
        )

    def test_find_branching_step(self, executor, mock_step):
        """Test finding branching step in pipeline"""
        regular_step = Mock(spec=DynamicPipelineStepDB)
        regular_step.is_branching_step = False

        branching_step = Mock(spec=DynamicPipelineStepDB)
        branching_step.is_branching_step = True
        branching_step.name = "Classification"
        branching_step.order = 2

        steps = [regular_step, branching_step]

        result = executor.find_branching_step(steps)

        assert result == branching_step

    def test_find_branching_step_not_found(self, executor, mock_step):
        """Test finding branching step when none exists"""
        mock_step.is_branching_step = False
        steps = [mock_step]

        result = executor.find_branching_step(steps)

        assert result is None

    def test_load_ocr_configuration(self, executor):
        """Test loading OCR configuration"""
        mock_config = Mock(spec=OCRConfigurationDB)
        mock_config.selected_engine = "PADDLEOCR"

        mock_query = Mock()
        mock_query.first.return_value = mock_config
        executor.session.query.return_value = mock_query

        config = executor.load_ocr_configuration()

        assert config == mock_config

    def test_get_model_info(self, executor):
        """Test getting model information"""
        mock_model = Mock(spec=AvailableModelDB)
        mock_model.id = 1
        mock_model.name = "Meta-Llama-3.3-70B"
        mock_model.is_enabled = True

        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = mock_model
        executor.session.query.return_value = mock_query

        model = executor.get_model_info(model_id=1)

        assert model == mock_model


class TestStopConditions:
    """Test suite for stop condition checking"""

    @pytest.fixture
    def executor(self):
        """Create executor instance for testing"""
        mock_session = Mock()
        with (
            patch("app.services.modular_pipeline_executor.OVHClient"),
            patch("app.services.modular_pipeline_executor.DocumentClassManager"),
            patch("app.services.modular_pipeline_executor.AICostTracker"),
        ):
            return ModularPipelineExecutor(session=mock_session)

    @pytest.fixture
    def mock_step(self):
        """Create a mock pipeline step with stop conditions"""
        step = Mock(spec=DynamicPipelineStepDB)
        step.name = "Medical Validation"
        step.order = 1
        step.stop_conditions = {
            "stop_on_values": ["NICHT_MEDIZINISCH"],
            "termination_reason": "Non-medical content detected",
            "termination_message": "Document contains non-medical content",
        }
        return step

    def test_check_stop_condition_match(self, executor, mock_step):
        """Test stop condition matches correctly"""
        output_text = "NICHT_MEDIZINISCH - This is not medical"

        result = executor.check_stop_condition(mock_step, output_text)

        assert result is not None
        assert result["should_stop"] is True
        assert result["matched_value"] == "NICHT_MEDIZINISCH"
        assert result["termination_reason"] == "Non-medical content detected"
        assert result["step_name"] == "Medical Validation"

    def test_check_stop_condition_no_match(self, executor, mock_step):
        """Test stop condition does not match"""
        output_text = "MEDIZINISCH - This is medical content"

        result = executor.check_stop_condition(mock_step, output_text)

        assert result is None

    def test_check_stop_condition_case_insensitive(self, executor, mock_step):
        """Test stop condition matching is case-insensitive"""
        output_text = "nicht_medizinisch - lowercase"

        result = executor.check_stop_condition(mock_step, output_text)

        assert result is not None
        assert result["matched_value"] == "NICHT_MEDIZINISCH"

    def test_check_stop_condition_no_conditions(self, executor):
        """Test step without stop conditions returns None"""
        step = Mock(spec=DynamicPipelineStepDB)
        step.stop_conditions = None

        result = executor.check_stop_condition(step, "Any output")

        assert result is None

    def test_check_stop_condition_empty_values(self, executor):
        """Test stop condition with empty stop_on_values"""
        step = Mock(spec=DynamicPipelineStepDB)
        step.stop_conditions = {"stop_on_values": []}

        result = executor.check_stop_condition(step, "Any output")

        assert result is None

    def test_check_stop_condition_first_word_only(self, executor, mock_step):
        """Test stop condition only matches first word"""
        # Should NOT match because NICHT_MEDIZINISCH is not the first word
        output_text = "Das Dokument ist NICHT_MEDIZINISCH"

        result = executor.check_stop_condition(mock_step, output_text)

        assert result is None


class TestBranchExtraction:
    """Test suite for branch value extraction"""

    @pytest.fixture
    def executor(self):
        """Create executor instance for testing"""
        mock_session = Mock()
        with (
            patch("app.services.modular_pipeline_executor.OVHClient"),
            patch(
                "app.services.modular_pipeline_executor.DocumentClassManager"
            ) as MockDocClassManager,
            patch("app.services.modular_pipeline_executor.AICostTracker"),
        ):
            # Setup mock document class manager
            mock_doc_class = Mock(spec=DocumentClassDB)
            mock_doc_class.id = 3
            mock_doc_class.class_key = "ARZTBRIEF"
            mock_doc_class.display_name = "Arztbrief"

            mock_manager = MockDocClassManager.return_value
            mock_manager.get_class_by_key.return_value = mock_doc_class

            executor = ModularPipelineExecutor(session=mock_session)
            return executor

    def test_extract_branch_value_document_type_success(self, executor):
        """Test extracting document type branch value"""
        output_text = "ARZTBRIEF"

        result = executor.extract_branch_value(output_text, branching_field="document_type")

        assert result is not None
        assert result["field"] == "document_type"
        assert result["value"] == "ARZTBRIEF"
        assert result["type"] == "document_class"
        assert result["target_id"] == 3
        assert result["target_key"] == "ARZTBRIEF"
        assert result["target_display_name"] == "Arztbrief"

    def test_extract_branch_value_unknown_document_class(self, executor):
        """Test extracting unknown document class"""
        executor.doc_class_manager.get_class_by_key.return_value = None
        output_text = "UNKNOWN_TYPE"

        result = executor.extract_branch_value(output_text, branching_field="document_type")

        assert result is not None
        assert result["type"] == "document_class"
        assert result["target_id"] is None
        assert result["target_key"] == "UNKNOWN_TYPE"
        assert result["target_display_name"] == "Unknown"

    def test_extract_branch_value_boolean(self, executor):
        """Test extracting boolean branch value"""
        output_text = "MEDIZINISCH"

        result = executor.extract_branch_value(output_text, branching_field="medical_validation")

        assert result is not None
        assert result["field"] == "medical_validation"
        assert result["value"] == "MEDIZINISCH"
        assert result["type"] == "boolean"
        assert result["target_id"] is None

    def test_extract_branch_value_enum(self, executor):
        """Test extracting enum branch value (quality level)"""
        output_text = "HIGH"

        result = executor.extract_branch_value(output_text, branching_field="quality_level")

        assert result is not None
        assert result["field"] == "quality_level"
        assert result["value"] == "HIGH"
        assert result["type"] == "enum"

    def test_extract_branch_value_removes_prefix(self, executor):
        """Test branch extraction removes common prefixes"""
        output_text = "CLASSIFICATION: ARZTBRIEF"

        result = executor.extract_branch_value(output_text, branching_field="document_type")

        assert result is not None
        assert result["value"] == "ARZTBRIEF"

    def test_extract_branch_value_empty_output(self, executor):
        """Test branch extraction with empty output"""
        result = executor.extract_branch_value("", branching_field="document_type")

        assert result is None


@pytest.mark.asyncio
class TestStepExecution:
    """Test suite for single step execution"""

    @pytest.fixture
    def executor(self):
        """Create executor instance for testing"""
        mock_session = Mock()
        with (
            patch("app.services.modular_pipeline_executor.OVHClient") as MockOVH,
            patch("app.services.modular_pipeline_executor.DocumentClassManager"),
            patch("app.services.modular_pipeline_executor.AICostTracker") as MockCostTracker,
        ):
            # Mock OVH client response
            mock_ovh = MockOVH.return_value
            mock_ovh.process_medical_text_with_prompt = AsyncMock(
                return_value={
                    "text": "Processed output",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "model": "Meta-Llama-3.3-70B",
                }
            )

            # Mock cost tracker
            mock_tracker = MockCostTracker.return_value
            mock_tracker.log_ai_call = Mock()

            executor = ModularPipelineExecutor(session=mock_session)
            return executor

    @pytest.fixture
    def mock_step(self):
        """Create a mock pipeline step"""
        step = Mock(spec=DynamicPipelineStepDB)
        step.id = 1
        step.name = "Translation"
        step.prompt_template = "Translate: {input_text}"
        step.selected_model_id = 1
        step.temperature = 0.7
        step.max_tokens = 4096
        step.retry_on_failure = False
        step.max_retries = 1
        return step

    @pytest.fixture
    def mock_model(self):
        """Create a mock AI model"""
        model = Mock(spec=AvailableModelDB)
        model.id = 1
        model.name = "Meta-Llama-3.3-70B"
        model.max_tokens = 8192
        return model

    @pytest.mark.asyncio
    async def test_execute_step_success(self, executor, mock_step, mock_model):
        """Test successful step execution"""
        executor.get_model_info = Mock(return_value=mock_model)

        success, output, error = await executor.execute_step(
            step=mock_step, input_text="Test input", context={}, processing_id="test123"
        )

        assert success is True
        assert output == "Processed output"
        assert error is None

    @pytest.mark.asyncio
    async def test_execute_step_model_not_found(self, executor, mock_step):
        """Test step execution when model not found"""
        executor.get_model_info = Mock(return_value=None)

        success, output, error = await executor.execute_step(
            step=mock_step, input_text="Test input"
        )

        assert success is False
        assert output == ""
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    async def test_execute_step_missing_variable(self, executor, mock_step, mock_model):
        """Test step execution with missing template variable"""
        executor.get_model_info = Mock(return_value=mock_model)
        mock_step.prompt_template = "Translate to {target_language}: {input_text}"

        success, output, error = await executor.execute_step(
            step=mock_step,
            input_text="Test",
            context={},  # Missing target_language
        )

        assert success is False
        assert "Missing required variable" in error

    @pytest.mark.asyncio
    async def test_execute_step_with_retries(self, executor, mock_step, mock_model):
        """Test step execution with retries on failure"""
        executor.get_model_info = Mock(return_value=mock_model)
        mock_step.retry_on_failure = True
        mock_step.max_retries = 3

        # First two attempts fail, third succeeds
        executor.ovh_client.process_medical_text_with_prompt = AsyncMock(
            side_effect=[
                {"text": "Error: API timeout", "input_tokens": 0, "output_tokens": 0},
                {"text": "Error: Connection failed", "input_tokens": 0, "output_tokens": 0},
                {
                    "text": "Success!",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "model": "test",
                },
            ]
        )

        success, output, error = await executor.execute_step(step=mock_step, input_text="Test")

        assert success is True
        assert output == "Success!"
        assert executor.ovh_client.process_medical_text_with_prompt.call_count == 3


class TestModularPipelineManager:
    """Test suite for ModularPipelineManager CRUD operations"""

    @pytest.fixture
    def manager(self):
        """Create manager instance for testing"""
        mock_session = Mock()
        return ModularPipelineManager(session=mock_session)

    @pytest.fixture
    def mock_step(self):
        """Create a mock pipeline step"""
        step = Mock(spec=DynamicPipelineStepDB)
        step.id = 1
        step.name = "Test Step"
        step.order = 1
        return step

    def test_get_all_steps(self, manager, mock_step):
        """Test getting all pipeline steps"""
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = [mock_step]
        manager.session.query.return_value = mock_query

        steps = manager.get_all_steps()

        assert len(steps) == 1
        assert steps[0] == mock_step

    def test_get_step(self, manager, mock_step):
        """Test getting a single step by ID"""
        # Mock step_repository instead of session.query
        manager.step_repository = Mock()
        manager.step_repository.get.return_value = mock_step

        step = manager.get_step(step_id=1)

        assert step == mock_step
        manager.step_repository.get.assert_called_once_with(1)

    def test_create_step(self, manager):
        """Test creating a new pipeline step"""
        step_data = {"name": "New Step", "order": 5, "enabled": True}

        step = manager.create_step(step_data)

        manager.session.add.assert_called_once()
        manager.session.commit.assert_called_once()

    def test_update_step(self, manager, mock_step):
        """Test updating an existing step"""
        manager.get_step = Mock(return_value=mock_step)
        step_data = {"name": "Updated Name"}

        result = manager.update_step(step_id=1, step_data=step_data)

        assert result == mock_step
        assert mock_step.name == "Updated Name"
        manager.session.commit.assert_called_once()

    def test_update_step_not_found(self, manager):
        """Test updating non-existent step"""
        manager.get_step = Mock(return_value=None)

        result = manager.update_step(step_id=999, step_data={})

        assert result is None

    def test_delete_step(self, manager, mock_step):
        """Test deleting a pipeline step"""
        manager.get_step = Mock(return_value=mock_step)

        success = manager.delete_step(step_id=1)

        assert success is True
        manager.session.delete.assert_called_once_with(mock_step)
        manager.session.commit.assert_called_once()

    def test_delete_step_not_found(self, manager):
        """Test deleting non-existent step"""
        manager.get_step = Mock(return_value=None)

        success = manager.delete_step(step_id=999)

        assert success is False

    def test_reorder_steps(self, manager, mock_step):
        """Test reordering pipeline steps"""
        step1 = Mock(spec=DynamicPipelineStepDB)
        step1.id = 1
        step2 = Mock(spec=DynamicPipelineStepDB)
        step2.id = 2

        manager.get_step = Mock(side_effect=[step1, step2])
        step_order = [1, 2]

        success = manager.reorder_steps(step_order)

        assert success is True
        assert step1.order == 1
        assert step2.order == 2
        manager.session.commit.assert_called_once()

    def test_get_ocr_config(self, manager):
        """Test getting OCR configuration"""
        mock_config = Mock(spec=OCRConfigurationDB)
        mock_query = Mock()
        mock_query.first.return_value = mock_config
        manager.session.query.return_value = mock_query

        config = manager.get_ocr_config()

        assert config == mock_config

    def test_update_ocr_config_existing(self, manager):
        """Test updating existing OCR configuration"""
        mock_config = Mock(spec=OCRConfigurationDB)
        manager.get_ocr_config = Mock(return_value=mock_config)
        config_data = {"selected_engine": "MISTRAL_OCR"}

        result = manager.update_ocr_config(config_data)

        assert result == mock_config
        assert mock_config.selected_engine == "MISTRAL_OCR"

    def test_update_ocr_config_new(self, manager):
        """Test creating new OCR configuration"""
        manager.get_ocr_config = Mock(return_value=None)
        config_data = {"selected_engine": "PADDLEOCR"}

        manager.update_ocr_config(config_data)

        manager.session.add.assert_called_once()
        manager.session.commit.assert_called_once()

    def test_get_all_models(self, manager):
        """Test getting all available models"""
        mock_model = Mock(spec=AvailableModelDB)
        # Mock model_repository instead of session.query
        manager.model_repository = Mock()
        manager.model_repository.get_all.return_value = [mock_model]

        models = manager.get_all_models()

        assert len(models) == 1
        manager.model_repository.get_all.assert_called_once()

    def test_get_all_models_enabled_only(self, manager):
        """Test getting only enabled models"""
        mock_model = Mock(spec=AvailableModelDB)
        # Mock model_repository instead of session.query
        manager.model_repository = Mock()
        manager.model_repository.get_enabled_models.return_value = [mock_model]

        models = manager.get_all_models(enabled_only=True)

        assert len(models) == 1
        manager.model_repository.get_enabled_models.assert_called_once()


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
