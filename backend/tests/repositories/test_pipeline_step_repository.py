"""
Tests for PipelineStepRepository

Tests all specialized pipeline step operations including ordering, filtering,
branching, document-class associations, and pipeline management.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import DynamicPipelineStepDB
from app.repositories.pipeline_step_repository import PipelineStepRepository


class TestPipelineStepRepository:
    """Test suite for PipelineStepRepository specialized methods."""

    @pytest.fixture
    def repository(self, db_session):
        """Create PipelineStepRepository instance."""
        return PipelineStepRepository(db_session)

    # ==================== GET ALL ORDERED TESTS ====================

    def test_get_all_ordered(self, repository, create_pipeline_step):
        """Test retrieving all steps ordered by execution order."""
        create_pipeline_step(name="Third", order=3)
        create_pipeline_step(name="First", order=1)
        create_pipeline_step(name="Second", order=2)

        steps = repository.get_all_ordered()

        assert len(steps) == 3
        assert steps[0].name == "First"
        assert steps[1].name == "Second"
        assert steps[2].name == "Third"

    def test_get_all_ordered_empty_database(self, repository):
        """Test get_all_ordered returns empty list when no steps."""
        steps = repository.get_all_ordered()
        assert len(steps) == 0

    def test_get_all_ordered_includes_disabled_steps(self, repository, create_pipeline_step):
        """Test that get_all_ordered includes both enabled and disabled steps."""
        create_pipeline_step(name="Enabled", order=1, enabled=True)
        create_pipeline_step(name="Disabled", order=2, enabled=False)

        steps = repository.get_all_ordered()

        assert len(steps) == 2

    # ==================== GET ENABLED/DISABLED STEPS TESTS ====================

    def test_get_enabled_steps(self, repository, create_pipeline_step):
        """Test retrieving only enabled steps."""
        create_pipeline_step(name="Enabled 1", order=1, enabled=True)
        create_pipeline_step(name="Disabled", order=2, enabled=False)
        create_pipeline_step(name="Enabled 2", order=3, enabled=True)

        enabled_steps = repository.get_enabled_steps()

        assert len(enabled_steps) == 2
        assert all(step.enabled for step in enabled_steps)
        assert enabled_steps[0].name == "Enabled 1"
        assert enabled_steps[1].name == "Enabled 2"

    def test_get_enabled_steps_ordered(self, repository, create_pipeline_step):
        """Test that enabled steps are returned in order."""
        create_pipeline_step(name="Third", order=3, enabled=True)
        create_pipeline_step(name="First", order=1, enabled=True)
        create_pipeline_step(name="Second", order=2, enabled=True)

        enabled_steps = repository.get_enabled_steps()

        assert enabled_steps[0].order == 1
        assert enabled_steps[1].order == 2
        assert enabled_steps[2].order == 3

    def test_get_enabled_steps_empty(self, repository, create_pipeline_step):
        """Test get_enabled_steps when all steps are disabled."""
        create_pipeline_step(name="Disabled 1", order=1, enabled=False)
        create_pipeline_step(name="Disabled 2", order=2, enabled=False)

        enabled_steps = repository.get_enabled_steps()

        assert len(enabled_steps) == 0

    def test_get_disabled_steps(self, repository, create_pipeline_step):
        """Test retrieving only disabled steps."""
        create_pipeline_step(name="Enabled", order=1, enabled=True)
        create_pipeline_step(name="Disabled 1", order=2, enabled=False)
        create_pipeline_step(name="Disabled 2", order=3, enabled=False)

        disabled_steps = repository.get_disabled_steps()

        assert len(disabled_steps) == 2
        assert all(not step.enabled for step in disabled_steps)

    def test_get_disabled_steps_ordered(self, repository, create_pipeline_step):
        """Test that disabled steps are returned in order."""
        create_pipeline_step(name="Third", order=3, enabled=False)
        create_pipeline_step(name="First", order=1, enabled=False)
        create_pipeline_step(name="Second", order=2, enabled=False)

        disabled_steps = repository.get_disabled_steps()

        assert disabled_steps[0].order == 1
        assert disabled_steps[1].order == 2
        assert disabled_steps[2].order == 3

    # ==================== UNIVERSAL STEPS TESTS ====================

    def test_get_universal_steps(self, repository, create_pipeline_step, create_document_class):
        """Test retrieving universal steps (not tied to document class)."""
        doc_class = create_document_class(class_key="ARZTBRIEF")

        create_pipeline_step(name="Universal 1", order=1, document_class_id=None)
        create_pipeline_step(name="Class-Specific", order=2, document_class_id=doc_class.id)
        create_pipeline_step(name="Universal 2", order=3, document_class_id=None)

        universal_steps = repository.get_universal_steps()

        assert len(universal_steps) == 2
        assert all(step.document_class_id is None for step in universal_steps)
        assert universal_steps[0].name == "Universal 1"
        assert universal_steps[1].name == "Universal 2"

    def test_get_universal_steps_ordered(self, repository, create_pipeline_step):
        """Test that universal steps are returned in order."""
        create_pipeline_step(name="Third", order=3, document_class_id=None)
        create_pipeline_step(name="First", order=1, document_class_id=None)
        create_pipeline_step(name="Second", order=2, document_class_id=None)

        universal_steps = repository.get_universal_steps()

        assert universal_steps[0].order == 1
        assert universal_steps[1].order == 2
        assert universal_steps[2].order == 3

    def test_get_universal_steps_empty(
        self, repository, create_pipeline_step, create_document_class
    ):
        """Test get_universal_steps when all steps are class-specific."""
        doc_class = create_document_class(class_key="ARZTBRIEF")
        create_pipeline_step(name="Specific", order=1, document_class_id=doc_class.id)

        universal_steps = repository.get_universal_steps()

        assert len(universal_steps) == 0

    # ==================== DOCUMENT CLASS STEPS TESTS ====================

    def test_get_steps_by_document_class(
        self, repository, create_pipeline_step, create_document_class
    ):
        """Test retrieving steps for a specific document class."""
        arztbrief = create_document_class(class_key="ARZTBRIEF")
        befund = create_document_class(class_key="BEFUNDBERICHT")

        create_pipeline_step(name="Universal", order=1, document_class_id=None)
        create_pipeline_step(name="Arztbrief 1", order=2, document_class_id=arztbrief.id)
        create_pipeline_step(name="Befund 1", order=3, document_class_id=befund.id)
        create_pipeline_step(name="Arztbrief 2", order=4, document_class_id=arztbrief.id)

        arztbrief_steps = repository.get_steps_by_document_class(arztbrief.id)

        assert len(arztbrief_steps) == 2
        assert all(step.document_class_id == arztbrief.id for step in arztbrief_steps)
        assert arztbrief_steps[0].name == "Arztbrief 1"
        assert arztbrief_steps[1].name == "Arztbrief 2"

    def test_get_steps_by_document_class_ordered(
        self, repository, create_pipeline_step, create_document_class
    ):
        """Test that class-specific steps are returned in order."""
        doc_class = create_document_class(class_key="ARZTBRIEF")

        create_pipeline_step(name="Third", order=3, document_class_id=doc_class.id)
        create_pipeline_step(name="First", order=1, document_class_id=doc_class.id)
        create_pipeline_step(name="Second", order=2, document_class_id=doc_class.id)

        steps = repository.get_steps_by_document_class(doc_class.id)

        assert steps[0].order == 1
        assert steps[1].order == 2
        assert steps[2].order == 3

    def test_get_steps_by_document_class_empty(self, repository, create_document_class):
        """Test get_steps_by_document_class when class has no steps."""
        doc_class = create_document_class(class_key="ARZTBRIEF")

        steps = repository.get_steps_by_document_class(doc_class.id)

        assert len(steps) == 0

    # ==================== BRANCHING STEP TESTS ====================

    def test_get_branching_step(self, repository, create_pipeline_step):
        """Test retrieving the branching step."""
        create_pipeline_step(name="Regular Step", order=1, is_branching_step=False)
        create_pipeline_step(name="Classification", order=2, is_branching_step=True)
        create_pipeline_step(name="Another Step", order=3, is_branching_step=False)

        branching_step = repository.get_branching_step()

        assert branching_step is not None
        assert branching_step.name == "Classification"
        assert branching_step.is_branching_step is True

    def test_get_branching_step_none(self, repository, create_pipeline_step):
        """Test get_branching_step returns None when no branching step exists."""
        create_pipeline_step(name="Regular Step", order=1, is_branching_step=False)

        branching_step = repository.get_branching_step()

        assert branching_step is None

    def test_get_branching_step_returns_first_if_multiple(self, repository, create_pipeline_step):
        """Test that get_branching_step returns first branching step if multiple exist."""
        create_pipeline_step(name="First Branching", order=1, is_branching_step=True)
        create_pipeline_step(name="Second Branching", order=2, is_branching_step=True)

        branching_step = repository.get_branching_step()

        assert branching_step is not None
        # Should return first one found (implementation detail of SQLAlchemy .first())

    # ==================== POST-BRANCHING STEPS TESTS ====================

    def test_get_post_branching_steps(self, repository, create_pipeline_step):
        """Test retrieving post-branching steps."""
        create_pipeline_step(name="Regular Step", order=1, post_branching=False)
        create_pipeline_step(name="Post-Branch 1", order=2, post_branching=True)
        create_pipeline_step(name="Post-Branch 2", order=3, post_branching=True)

        post_steps = repository.get_post_branching_steps()

        assert len(post_steps) == 2
        assert all(step.post_branching for step in post_steps)

    def test_get_post_branching_steps_ordered(self, repository, create_pipeline_step):
        """Test that post-branching steps are returned in order."""
        create_pipeline_step(name="Third", order=3, post_branching=True)
        create_pipeline_step(name="First", order=1, post_branching=True)
        create_pipeline_step(name="Second", order=2, post_branching=True)

        post_steps = repository.get_post_branching_steps()

        assert post_steps[0].order == 1
        assert post_steps[1].order == 2
        assert post_steps[2].order == 3

    def test_get_post_branching_steps_empty(self, repository, create_pipeline_step):
        """Test get_post_branching_steps when no post-branching steps exist."""
        create_pipeline_step(name="Regular Step", order=1, post_branching=False)

        post_steps = repository.get_post_branching_steps()

        assert len(post_steps) == 0

    # ==================== GET STEP BY NAME TESTS ====================

    def test_get_step_by_name_existing(self, repository, create_pipeline_step):
        """Test retrieving step by name."""
        create_pipeline_step(name="Medical Validation", order=1)

        step = repository.get_step_by_name("Medical Validation")

        assert step is not None
        assert step.name == "Medical Validation"

    def test_get_step_by_name_nonexistent(self, repository):
        """Test get_step_by_name returns None for non-existent name."""
        step = repository.get_step_by_name("Nonexistent Step")
        assert step is None

    def test_get_step_by_name_case_sensitive(self, repository, create_pipeline_step):
        """Test that name matching is case-sensitive."""
        create_pipeline_step(name="Medical Validation", order=1)

        assert repository.get_step_by_name("Medical Validation") is not None
        assert repository.get_step_by_name("medical validation") is None

    # ==================== GET STEPS BY MODEL TESTS ====================

    def test_get_steps_by_model(self, repository, create_pipeline_step, create_available_model):
        """Test retrieving steps using a specific model."""
        llama_model = create_available_model(name="Llama-70B")
        mistral_model = create_available_model(name="Mistral-Nemo")

        create_pipeline_step(name="Step 1", order=1, selected_model_id=llama_model.id)
        create_pipeline_step(name="Step 2", order=2, selected_model_id=mistral_model.id)
        create_pipeline_step(name="Step 3", order=3, selected_model_id=llama_model.id)

        llama_steps = repository.get_steps_by_model(llama_model.id)

        assert len(llama_steps) == 2
        assert all(step.selected_model_id == llama_model.id for step in llama_steps)

    def test_get_steps_by_model_empty(self, repository, create_available_model):
        """Test get_steps_by_model when no steps use the model."""
        model = create_available_model(name="Unused-Model")

        steps = repository.get_steps_by_model(model.id)

        assert len(steps) == 0

    # ==================== ENABLE/DISABLE STEP TESTS ====================

    def test_enable_step(self, repository, create_pipeline_step):
        """Test enabling a disabled step."""
        step = create_pipeline_step(name="Test Step", order=1, enabled=False)

        updated_step = repository.enable_step(step.id)

        assert updated_step is not None
        assert updated_step.enabled is True

    def test_enable_step_already_enabled(self, repository, create_pipeline_step):
        """Test enabling an already enabled step."""
        step = create_pipeline_step(name="Test Step", order=1, enabled=True)

        updated_step = repository.enable_step(step.id)

        assert updated_step is not None
        assert updated_step.enabled is True

    def test_enable_step_nonexistent(self, repository):
        """Test enabling non-existent step returns None."""
        result = repository.enable_step(999999)
        assert result is None

    def test_disable_step(self, repository, create_pipeline_step):
        """Test disabling an enabled step."""
        step = create_pipeline_step(name="Test Step", order=1, enabled=True)

        updated_step = repository.disable_step(step.id)

        assert updated_step is not None
        assert updated_step.enabled is False

    def test_disable_step_already_disabled(self, repository, create_pipeline_step):
        """Test disabling an already disabled step."""
        step = create_pipeline_step(name="Test Step", order=1, enabled=False)

        updated_step = repository.disable_step(step.id)

        assert updated_step is not None
        assert updated_step.enabled is False

    def test_disable_step_nonexistent(self, repository):
        """Test disabling non-existent step returns None."""
        result = repository.disable_step(999999)
        assert result is None

    # ==================== REORDER STEPS TESTS ====================

    def test_reorder_steps(self, repository, create_pipeline_step):
        """Test reordering pipeline steps."""
        step1 = create_pipeline_step(name="First", order=1)
        step2 = create_pipeline_step(name="Second", order=2)
        step3 = create_pipeline_step(name="Third", order=3)

        # Reorder: [step3, step1, step2]
        result = repository.reorder_steps([step3.id, step1.id, step2.id])

        assert result is True

        # Verify new order
        reordered = repository.get_all_ordered()
        assert reordered[0].id == step3.id
        assert reordered[0].order == 1
        assert reordered[1].id == step1.id
        assert reordered[1].order == 2
        assert reordered[2].id == step2.id
        assert reordered[2].order == 3

    def test_reorder_steps_single_step(self, repository, create_pipeline_step):
        """Test reordering with single step."""
        step = create_pipeline_step(name="Only Step", order=1)

        result = repository.reorder_steps([step.id])

        assert result is True
        assert repository.get_by_id(step.id).order == 1

    def test_reorder_steps_empty_list(self, repository):
        """Test reorder_steps with empty list."""
        result = repository.reorder_steps([])
        assert result is True

    def test_reorder_steps_with_nonexistent_id(self, repository, create_pipeline_step):
        """Test reorder_steps ignores non-existent IDs."""
        step1 = create_pipeline_step(name="First", order=1)
        step2 = create_pipeline_step(name="Second", order=2)

        # Include non-existent ID
        result = repository.reorder_steps([step1.id, 999999, step2.id])

        assert result is True
        # Existing steps should still be reordered
        assert repository.get_by_id(step1.id).order == 1
        assert repository.get_by_id(step2.id).order == 3

    # ==================== CONTEXT REQUIREMENTS TESTS ====================

    def test_get_steps_requiring_context(self, repository, create_pipeline_step):
        """Test retrieving steps that require specific context variable."""
        create_pipeline_step(
            name="Translation Step",
            order=1,
            required_context_variables=["target_language", "source_language"],
        )
        create_pipeline_step(
            name="Validation Step", order=2, required_context_variables=["document_type"]
        )
        create_pipeline_step(name="OCR Step", order=3, required_context_variables=None)

        steps = repository.get_steps_requiring_context("target_language")

        assert len(steps) == 1
        assert steps[0].name == "Translation Step"

    def test_get_steps_requiring_context_multiple_matches(self, repository, create_pipeline_step):
        """Test finding multiple steps requiring same context variable."""
        create_pipeline_step(name="Step 1", order=1, required_context_variables=["document_type"])
        create_pipeline_step(
            name="Step 2", order=2, required_context_variables=["document_type", "other_var"]
        )

        steps = repository.get_steps_requiring_context("document_type")

        assert len(steps) == 2

    def test_get_steps_requiring_context_no_matches(self, repository, create_pipeline_step):
        """Test get_steps_requiring_context when no steps require the variable."""
        create_pipeline_step(name="Step", order=1, required_context_variables=["other_variable"])

        steps = repository.get_steps_requiring_context("target_language")

        assert len(steps) == 0

    def test_get_steps_requiring_context_null_requirements(self, repository, create_pipeline_step):
        """Test that steps with null requirements are not returned."""
        create_pipeline_step(name="Step", order=1, required_context_variables=None)

        steps = repository.get_steps_requiring_context("any_variable")

        assert len(steps) == 0

    # ==================== STOP CONDITIONS TESTS ====================

    def test_get_steps_with_stop_conditions(self, repository, create_pipeline_step):
        """Test retrieving steps with stop conditions."""
        create_pipeline_step(
            name="Validation Step",
            order=1,
            stop_conditions={
                "stop_on_values": ["NICHT_MEDIZINISCH"],
                "termination_reason": "Non-medical content",
            },
        )
        create_pipeline_step(name="Regular Step", order=2, stop_conditions=None)
        create_pipeline_step(
            name="Another Conditional", order=3, stop_conditions={"stop_on_values": ["INVALID"]}
        )

        steps = repository.get_steps_with_stop_conditions()

        assert len(steps) == 2
        assert all(step.stop_conditions is not None for step in steps)

    def test_get_steps_with_stop_conditions_empty(self, repository, create_pipeline_step):
        """Test get_steps_with_stop_conditions when no steps have conditions."""
        create_pipeline_step(name="Step 1", order=1, stop_conditions=None)
        create_pipeline_step(name="Step 2", order=2, stop_conditions=None)

        steps = repository.get_steps_with_stop_conditions()

        assert len(steps) == 0

    # ==================== DUPLICATE STEP TESTS ====================

    def test_duplicate_step(self, repository, create_pipeline_step):
        """Test duplicating a pipeline step."""
        original = create_pipeline_step(
            name="Original Step",
            description="Original description",
            order=1,
            enabled=True,
            prompt_template="Original prompt",
            temperature=0.8,
        )

        duplicate = repository.duplicate_step(original.id, "Duplicated Step")

        assert duplicate is not None
        assert duplicate.id != original.id
        assert duplicate.name == "Duplicated Step"
        assert duplicate.description == original.description
        assert duplicate.order == original.order + 1
        assert duplicate.enabled is False  # Starts disabled
        assert duplicate.prompt_template == original.prompt_template
        assert duplicate.temperature == original.temperature
        assert duplicate.is_branching_step is False  # Never duplicate branching

    def test_duplicate_step_branching_not_copied(self, repository, create_pipeline_step):
        """Test that branching flag is not copied during duplication."""
        original = create_pipeline_step(
            name="Branching Step", order=1, is_branching_step=True, branching_field="document_type"
        )

        duplicate = repository.duplicate_step(original.id, "Duplicated Branching")

        assert duplicate is not None
        assert duplicate.is_branching_step is False
        assert duplicate.branching_field == original.branching_field

    def test_duplicate_step_nonexistent(self, repository):
        """Test duplicating non-existent step returns None."""
        result = repository.duplicate_step(999999, "New Name")
        assert result is None

    def test_duplicate_step_with_complex_attributes(self, repository, create_pipeline_step):
        """Test duplicating step with complex JSON attributes."""
        original = create_pipeline_step(
            name="Complex Step",
            order=1,
            required_context_variables=["var1", "var2"],
            stop_conditions={"stop_on_values": ["ERROR"]},
        )

        duplicate = repository.duplicate_step(original.id, "Duplicated Complex")

        assert duplicate is not None
        assert duplicate.required_context_variables == original.required_context_variables
        assert duplicate.stop_conditions == original.stop_conditions

    # ==================== STATISTICS TESTS ====================

    def test_get_step_statistics_comprehensive(
        self, repository, create_pipeline_step, create_document_class
    ):
        """Test getting comprehensive pipeline statistics."""
        doc_class = create_document_class(class_key="ARZTBRIEF")

        # Create various types of steps
        create_pipeline_step(
            name="Universal Enabled", order=1, enabled=True, document_class_id=None
        )
        create_pipeline_step(
            name="Universal Disabled", order=2, enabled=False, document_class_id=None
        )
        create_pipeline_step(
            name="Class-Specific", order=3, enabled=True, document_class_id=doc_class.id
        )
        create_pipeline_step(
            name="Branching Step",
            order=4,
            enabled=True,
            is_branching_step=True,
            document_class_id=None,
        )
        create_pipeline_step(
            name="Post-Branching",
            order=5,
            enabled=True,
            post_branching=True,
            document_class_id=None,
        )
        create_pipeline_step(
            name="Conditional Step",
            order=6,
            enabled=True,
            stop_conditions={"stop_on_values": ["ERROR"]},
            document_class_id=None,
        )

        stats = repository.get_step_statistics()

        assert stats["total_steps"] == 6
        assert stats["enabled_steps"] == 5
        assert stats["disabled_steps"] == 1
        assert stats["universal_steps"] == 5
        assert stats["class_specific_steps"] == 1
        assert stats["branching_steps"] == 1
        assert stats["post_branching_steps"] == 1
        assert stats["steps_with_stop_conditions"] == 1

    def test_get_step_statistics_empty_database(self, repository):
        """Test statistics on empty database."""
        stats = repository.get_step_statistics()

        assert stats["total_steps"] == 0
        assert stats["enabled_steps"] == 0
        assert stats["disabled_steps"] == 0
        assert stats["universal_steps"] == 0
        assert stats["class_specific_steps"] == 0
        assert stats["branching_steps"] == 0
        assert stats["post_branching_steps"] == 0
        assert stats["steps_with_stop_conditions"] == 0

    def test_get_step_statistics_all_enabled(self, repository, create_pipeline_step):
        """Test statistics when all steps are enabled."""
        create_pipeline_step(name="Step 1", order=1, enabled=True)
        create_pipeline_step(name="Step 2", order=2, enabled=True)
        create_pipeline_step(name="Step 3", order=3, enabled=True)

        stats = repository.get_step_statistics()

        assert stats["total_steps"] == 3
        assert stats["enabled_steps"] == 3
        assert stats["disabled_steps"] == 0

    # ==================== INTEGRATION TESTS ====================

    def test_pipeline_execution_flow(self, repository, create_pipeline_step, create_document_class):
        """Test complete pipeline execution flow with various step types."""
        arztbrief = create_document_class(class_key="ARZTBRIEF")

        # Create complete pipeline
        universal = create_pipeline_step(name="OCR", order=1, enabled=True)
        branching = create_pipeline_step(
            name="Classification",
            order=2,
            enabled=True,
            is_branching_step=True,
            branching_field="document_type",
        )
        class_specific = create_pipeline_step(
            name="Arztbrief Translation", order=3, enabled=True, document_class_id=arztbrief.id
        )
        post_branch = create_pipeline_step(
            name="Final Check", order=4, enabled=True, post_branching=True
        )

        # Verify pipeline structure
        all_steps = repository.get_all_ordered()
        assert len(all_steps) == 4

        enabled_steps = repository.get_enabled_steps()
        assert len(enabled_steps) == 4

        branching_step = repository.get_branching_step()
        assert branching_step.id == branching.id

        universal_steps = repository.get_universal_steps()
        assert len(universal_steps) == 3  # OCR, Classification, Final Check

        class_steps = repository.get_steps_by_document_class(arztbrief.id)
        assert len(class_steps) == 1
        assert class_steps[0].id == class_specific.id

        post_steps = repository.get_post_branching_steps()
        assert len(post_steps) == 1
        assert post_steps[0].id == post_branch.id

    def test_enable_disable_workflow(self, repository, create_pipeline_step):
        """Test workflow of enabling and disabling steps."""
        step = create_pipeline_step(name="Test Step", order=1, enabled=True)

        # Initially enabled
        assert repository.get_by_id(step.id).enabled is True
        assert len(repository.get_enabled_steps()) == 1

        # Disable
        repository.disable_step(step.id)
        assert repository.get_by_id(step.id).enabled is False
        assert len(repository.get_enabled_steps()) == 0
        assert len(repository.get_disabled_steps()) == 1

        # Re-enable
        repository.enable_step(step.id)
        assert repository.get_by_id(step.id).enabled is True
        assert len(repository.get_enabled_steps()) == 1
        assert len(repository.get_disabled_steps()) == 0

    def test_reorder_maintains_step_integrity(self, repository, create_pipeline_step):
        """Test that reordering doesn't affect other step attributes."""
        step1 = create_pipeline_step(
            name="First", order=1, enabled=True, prompt_template="Prompt 1"
        )
        step2 = create_pipeline_step(
            name="Second", order=2, enabled=False, prompt_template="Prompt 2"
        )

        # Reorder
        repository.reorder_steps([step2.id, step1.id])

        # Verify attributes unchanged except order
        reloaded_step1 = repository.get_by_id(step1.id)
        assert reloaded_step1.name == "First"
        assert reloaded_step1.enabled is True
        assert reloaded_step1.prompt_template == "Prompt 1"
        assert reloaded_step1.order == 2

        reloaded_step2 = repository.get_by_id(step2.id)
        assert reloaded_step2.name == "Second"
        assert reloaded_step2.enabled is False
        assert reloaded_step2.prompt_template == "Prompt 2"
        assert reloaded_step2.order == 1

    # ==================== ERROR HANDLING TESTS ====================

    def test_operations_with_invalid_document_class_id(self, repository):
        """Test that operations handle invalid document class IDs gracefully."""
        steps = repository.get_steps_by_document_class(999999)
        assert len(steps) == 0

    def test_operations_with_invalid_model_id(self, repository):
        """Test that operations handle invalid model IDs gracefully."""
        steps = repository.get_steps_by_model(999999)
        assert len(steps) == 0

    def test_duplicate_step_preserves_modified_by(self, repository, create_pipeline_step):
        """Test that duplicate_step sets modified_by to 'system_duplicate'."""
        original = create_pipeline_step(name="Original", order=1, modified_by="user123")

        duplicate = repository.duplicate_step(original.id, "Duplicate")

        assert duplicate is not None
        assert duplicate.modified_by == "system_duplicate"
