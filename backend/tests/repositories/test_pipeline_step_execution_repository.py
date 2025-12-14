"""
Tests for PipelineStepExecutionRepository with encryption support.

Tests encryption/decryption of input_text and output_text fields.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import (
    PipelineStepExecutionDB,
    StepExecutionStatus,
)
from app.repositories.pipeline_step_execution_repository import (
    PipelineStepExecutionRepository,
)


@pytest.fixture
def step_execution_repository(db_session: Session) -> PipelineStepExecutionRepository:
    """Create a PipelineStepExecutionRepository instance."""
    return PipelineStepExecutionRepository(db_session)


class TestPipelineStepExecutionRepositoryEncryption:
    """Test encryption/decryption of input_text and output_text."""

    def test_create_execution_encrypts_text_fields(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test that input_text and output_text are encrypted when creating."""
        input_text = "This is the input text for processing."
        output_text = "This is the output text after processing."

        execution = step_execution_repository.create(
            job_id="test-job-123",
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text=input_text,
            output_text=output_text,
        )

        # Verify execution was created
        assert execution is not None
        assert execution.job_id == "test-job-123"

        # Verify text fields are decrypted when retrieved (transparent decryption)
        assert execution.input_text == input_text
        assert execution.output_text == output_text

        # Verify in database they're encrypted (query directly)
        db_execution = (
            step_execution_repository.db.query(PipelineStepExecutionDB)
            .filter_by(id=execution.id)
            .first()
        )
        assert db_execution is not None

        # Check that stored values are encrypted (not plaintext)
        stored_input = db_execution.input_text
        stored_output = db_execution.output_text

        assert stored_input != input_text  # Should be encrypted
        assert stored_output != output_text  # Should be encrypted
        assert len(stored_input) > len(input_text)  # Encrypted is larger
        assert len(stored_output) > len(output_text)  # Encrypted is larger

    def test_get_execution_decrypts_text_fields(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test that text fields are decrypted when retrieving an execution."""
        input_text = "Input text for decryption test"
        output_text = "Output text for decryption test"

        # Create execution
        execution = step_execution_repository.create(
            job_id="test-job-456",
            step_id=2,
            step_name="test_step_2",
            step_order=2,
            status=StepExecutionStatus.COMPLETED,
            input_text=input_text,
            output_text=output_text,
        )

        # Retrieve execution by ID
        retrieved_execution = step_execution_repository.get_by_id(execution.id)

        # Verify text fields are decrypted
        assert retrieved_execution is not None
        assert retrieved_execution.input_text == input_text
        assert retrieved_execution.output_text == output_text

    def test_get_executions_by_job_id_decrypts(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test that text fields are decrypted when retrieving by job_id."""
        job_id = "test-job-789"
        input_text = "Input for job test"
        output_text = "Output for job test"

        # Create multiple executions for same job
        execution1 = step_execution_repository.create(
            job_id=job_id,
            step_id=1,
            step_name="step1",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text=input_text + " 1",
            output_text=output_text + " 1",
        )

        execution2 = step_execution_repository.create(
            job_id=job_id,
            step_id=2,
            step_name="step2",
            step_order=2,
            status=StepExecutionStatus.COMPLETED,
            input_text=input_text + " 2",
            output_text=output_text + " 2",
        )

        # Retrieve all executions for job
        executions = step_execution_repository.get_by_job_id(job_id)

        # Verify all are decrypted
        assert len(executions) == 2
        assert executions[0].input_text == input_text + " 1"
        assert executions[0].output_text == output_text + " 1"
        assert executions[1].input_text == input_text + " 2"
        assert executions[1].output_text == output_text + " 2"

    def test_update_execution_encrypts_new_text_fields(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test that updating text fields encrypts the new values."""
        # Create execution
        execution = step_execution_repository.create(
            job_id="test-job-update",
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text="Original input",
            output_text="Original output",
        )

        # Update with new text
        new_input = "Updated input text"
        new_output = "Updated output text"
        updated_execution = step_execution_repository.update(
            execution.id, input_text=new_input, output_text=new_output
        )

        # Verify updated text is decrypted
        assert updated_execution is not None
        assert updated_execution.input_text == new_input
        assert updated_execution.output_text == new_output

        # Verify old text is gone
        assert updated_execution.input_text != "Original input"
        assert updated_execution.output_text != "Original output"

    def test_clear_text_content_sets_to_none(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test that clearing text content sets fields to None."""
        job_id = "test-job-clear"

        # Create execution with text
        execution = step_execution_repository.create(
            job_id=job_id,
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text="Some input text",
            output_text="Some output text",
        )

        # Clear text content
        cleared_count = step_execution_repository.clear_text_content(job_id)

        # Verify text fields are None
        assert cleared_count == 1
        retrieved_execution = step_execution_repository.get_by_id(execution.id)
        assert retrieved_execution is not None
        assert retrieved_execution.input_text is None
        assert retrieved_execution.output_text is None

    def test_null_text_fields_handling(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test that None text fields are handled correctly."""
        execution = step_execution_repository.create(
            job_id="test-job-null",
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text=None,
            output_text=None,
        )

        # Verify None is preserved
        assert execution is not None
        retrieved_execution = step_execution_repository.get_by_id(execution.id)
        assert retrieved_execution is not None
        assert retrieved_execution.input_text is None
        assert retrieved_execution.output_text is None

    def test_partial_text_fields(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test execution with only input_text or only output_text."""
        # Only input_text
        execution1 = step_execution_repository.create(
            job_id="test-job-partial-1",
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.PENDING,
            input_text="Only input text",
            output_text=None,
        )

        assert execution1.input_text == "Only input text"
        assert execution1.output_text is None

        # Only output_text
        execution2 = step_execution_repository.create(
            job_id="test-job-partial-2",
            step_id=2,
            step_name="test_step",
            step_order=2,
            status=StepExecutionStatus.COMPLETED,
            input_text=None,
            output_text="Only output text",
        )

        assert execution2.input_text is None
        assert execution2.output_text == "Only output text"

    def test_large_text_fields_encryption(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test encryption of large text fields."""
        # Create large text (100KB)
        large_input = "X" * (100 * 1024)
        large_output = "Y" * (100 * 1024)

        execution = step_execution_repository.create(
            job_id="test-job-large",
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text=large_input,
            output_text=large_output,
        )

        # Verify large text is encrypted and decrypted correctly
        assert execution is not None
        retrieved_execution = step_execution_repository.get_by_id(execution.id)
        assert retrieved_execution is not None
        assert retrieved_execution.input_text == large_input
        assert retrieved_execution.output_text == large_output
        assert len(retrieved_execution.input_text) == 100 * 1024
        assert len(retrieved_execution.output_text) == 100 * 1024

    def test_text_round_trip(
        self, step_execution_repository: PipelineStepExecutionRepository
    ):
        """Test complete round-trip: create → retrieve → verify text integrity."""
        input_text = "Original input text with special chars: äöü ß €"
        output_text = "Original output text with numbers: 12345"

        # Create
        execution = step_execution_repository.create(
            job_id="test-job-roundtrip",
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text=input_text,
            output_text=output_text,
        )

        # Retrieve
        retrieved_execution = step_execution_repository.get_by_id(execution.id)

        # Verify text integrity
        assert retrieved_execution is not None
        assert retrieved_execution.input_text == input_text
        assert retrieved_execution.output_text == output_text

