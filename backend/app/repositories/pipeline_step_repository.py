"""
Pipeline Step Repository

Handles database operations for dynamic pipeline steps configuration.
"""

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import DynamicPipelineStepDB
from app.repositories.base_repository import BaseRepository


class PipelineStepRepository(BaseRepository[DynamicPipelineStepDB]):
    """
    Repository for Pipeline Step operations.

    Provides specialized queries for managing pipeline steps beyond
    basic CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize pipeline step repository.

        Args:
            db: Database session
        """
        super().__init__(db, DynamicPipelineStepDB)

    def get_all_ordered(self) -> list[DynamicPipelineStepDB]:
        """
        Get all pipeline steps ordered by their execution order.

        Returns:
            List of steps sorted by order field
        """
        return self.db.query(self.model).order_by(
            self.model.order
        ).all()

    def get_enabled_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Get all enabled pipeline steps ordered by execution order.

        Returns:
            List of enabled steps sorted by order
        """
        return self.db.query(self.model).filter_by(
            enabled=True
        ).order_by(self.model.order).all()

    def get_disabled_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Get all disabled pipeline steps.

        Returns:
            List of disabled steps
        """
        return self.db.query(self.model).filter_by(
            enabled=False
        ).order_by(self.model.order).all()

    def get_universal_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Get universal pipeline steps (not specific to any document class).

        Universal steps run for all document types.

        Returns:
            List of universal steps ordered by execution order
        """
        return self.db.query(self.model).filter(
            self.model.document_class_id.is_(None)
        ).order_by(self.model.order).all()

    def get_steps_by_document_class(self, document_class_id: int) -> list[DynamicPipelineStepDB]:
        """
        Get pipeline steps for a specific document class.

        Args:
            document_class_id: ID of the document class

        Returns:
            List of steps for the document class ordered by execution order
        """
        return self.db.query(self.model).filter_by(
            document_class_id=document_class_id
        ).order_by(self.model.order).all()

    def get_branching_step(self) -> DynamicPipelineStepDB | None:
        """
        Get the branching step that determines document classification.

        Returns:
            The branching step or None if not configured
        """
        return self.db.query(self.model).filter_by(
            is_branching_step=True
        ).first()

    def get_post_branching_steps(self) -> list[DynamicPipelineStepDB]:
        """
        Get steps that run after document-specific processing.

        Returns:
            List of post-branching steps ordered by execution order
        """
        return self.db.query(self.model).filter_by(
            post_branching=True
        ).order_by(self.model.order).all()

    def get_step_by_name(self, name: str) -> DynamicPipelineStepDB | None:
        """
        Get a pipeline step by its name.

        Args:
            name: Name of the step

        Returns:
            Step instance or None if not found
        """
        return self.db.query(self.model).filter_by(name=name).first()

    def get_steps_by_model(self, model_id: int) -> list[DynamicPipelineStepDB]:
        """
        Get all steps that use a specific AI model.

        Args:
            model_id: ID of the AI model

        Returns:
            List of steps using the model
        """
        return self.db.query(self.model).filter_by(
            selected_model_id=model_id
        ).all()

    def enable_step(self, step_id: int) -> DynamicPipelineStepDB | None:
        """
        Enable a pipeline step.

        Args:
            step_id: ID of the step to enable

        Returns:
            Updated step or None if not found
        """
        return self.update(step_id, enabled=True)

    def disable_step(self, step_id: int) -> DynamicPipelineStepDB | None:
        """
        Disable a pipeline step.

        Args:
            step_id: ID of the step to disable

        Returns:
            Updated step or None if not found
        """
        return self.update(step_id, enabled=False)

    def reorder_steps(self, step_order: list[int]) -> bool:
        """
        Reorder pipeline steps.

        Args:
            step_order: List of step IDs in desired execution order

        Returns:
            True if successful, False otherwise
        """
        try:
            for new_order, step_id in enumerate(step_order, start=1):
                step = self.get(step_id)
                if step:
                    step.order = new_order

            self.db.commit()
            return True

        except Exception:
            self.db.rollback()
            return False

    def get_steps_requiring_context(self, variable_name: str) -> list[DynamicPipelineStepDB]:
        """
        Get steps that require a specific context variable.

        Args:
            variable_name: Name of the required context variable

        Returns:
            List of steps requiring the variable
        """
        steps = self.db.query(self.model).filter(
            self.model.required_context_variables.isnot(None)
        ).all()

        # Filter steps that have the variable in their requirements
        return [
            step for step in steps
            if step.required_context_variables and variable_name in step.required_context_variables
        ]

    def get_steps_with_stop_conditions(self) -> list[DynamicPipelineStepDB]:
        """
        Get steps that have stop conditions configured.

        Returns:
            List of steps with stop conditions
        """
        steps = self.get_all()

        # Filter steps that have actual stop conditions (not None, not empty)
        return [
            step for step in steps
            if step.stop_conditions
        ]

    def duplicate_step(self, step_id: int, new_name: str) -> DynamicPipelineStepDB | None:
        """
        Duplicate a pipeline step with a new name.

        Args:
            step_id: ID of the step to duplicate
            new_name: Name for the duplicated step

        Returns:
            New step instance or None if original not found
        """
        original = self.get(step_id)
        if not original:
            return None

        # Create new step with copied attributes
        new_step = self.create(
            name=new_name,
            description=original.description,
            order=original.order + 1,  # Place after original
            enabled=False,  # Start disabled
            prompt_template=original.prompt_template,
            selected_model_id=original.selected_model_id,
            temperature=original.temperature,
            max_tokens=original.max_tokens,
            retry_on_failure=original.retry_on_failure,
            max_retries=original.max_retries,
            input_from_previous_step=original.input_from_previous_step,
            output_format=original.output_format,
            document_class_id=original.document_class_id,
            is_branching_step=False,  # Don't duplicate branching
            branching_field=original.branching_field,
            post_branching=original.post_branching,
            required_context_variables=original.required_context_variables,
            stop_conditions=original.stop_conditions,
            modified_by="system_duplicate"
        )

        return new_step

    def get_step_statistics(self) -> dict:
        """
        Get aggregate statistics about pipeline steps.

        Returns:
            Dictionary with statistics
        """
        steps = self.get_all()

        return {
            "total_steps": len(steps),
            "enabled_steps": sum(1 for s in steps if s.enabled),
            "disabled_steps": sum(1 for s in steps if not s.enabled),
            "universal_steps": sum(1 for s in steps if s.document_class_id is None),
            "class_specific_steps": sum(1 for s in steps if s.document_class_id is not None),
            "branching_steps": sum(1 for s in steps if s.is_branching_step),
            "post_branching_steps": sum(1 for s in steps if s.post_branching),
            "steps_with_stop_conditions": sum(1 for s in steps if s.stop_conditions),
        }
