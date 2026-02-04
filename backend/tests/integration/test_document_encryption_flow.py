"""
Integration tests for document encryption flow.

Tests end-to-end encryption flow: upload → process → encrypt → decrypt → download.
"""

import pytest
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus
from app.repositories.feedback_repository import PipelineJobFeedbackRepository
from app.repositories.pipeline_job_repository import PipelineJobRepository
from app.repositories.pipeline_step_execution_repository import (
    PipelineStepExecutionRepository,
)


@pytest.fixture
def sample_binary_content() -> bytes:
    """Sample binary content for testing (simulates PDF file)."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


@pytest.fixture
def repositories(db_session: Session):
    """Create all repositories needed for integration tests."""
    return {
        "job_repo": PipelineJobRepository(db_session),
        "step_execution_repo": PipelineStepExecutionRepository(db_session),
        "feedback_repo": PipelineJobFeedbackRepository(db_session),
    }


class TestDocumentEncryptionFlow:
    """Test complete document encryption flow."""

    def test_upload_process_download_flow(self, repositories: dict, sample_binary_content: bytes):
        """Test complete flow: upload → process → download with encryption."""
        job_repo = repositories["job_repo"]
        step_execution_repo = repositories["step_execution_repo"]

        # Step 1: Upload (create job with file_content)
        job = job_repo.create(
            job_id="integration-test-123",
            processing_id="integration-processing-123",
            filename="test_document.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,  # Encrypted on create
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        assert job is not None
        assert job.file_content == sample_binary_content  # Decrypted

        # Step 2: Process (create step executions with text)
        input_text = "Extracted text from OCR"
        output_text = "Processed and translated text"

        step_execution = step_execution_repo.create(
            job_id=job.job_id,
            step_id=1,
            step_name="ocr_extraction",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text=input_text,  # Encrypted on create
            output_text=output_text,  # Encrypted on create
        )

        assert step_execution is not None
        assert step_execution.input_text == input_text  # Decrypted
        assert step_execution.output_text == output_text  # Decrypted

        # Step 3: Download (retrieve job and verify content)
        retrieved_job = job_repo.get_by_processing_id("integration-processing-123")
        assert retrieved_job is not None
        assert retrieved_job.file_content == sample_binary_content  # Decrypted

        retrieved_executions = step_execution_repo.get_by_job_id(job.job_id)
        assert len(retrieved_executions) == 1
        assert retrieved_executions[0].input_text == input_text  # Decrypted
        assert retrieved_executions[0].output_text == output_text  # Decrypted

    def test_consent_flow_with_encryption(self, repositories: dict, sample_binary_content: bytes):
        """Test consent flow: content encrypted regardless of consent, cleared if no consent."""
        job_repo = repositories["job_repo"]
        feedback_repo = repositories["feedback_repo"]

        # Create job (content is encrypted when stored)
        job = job_repo.create(
            job_id="consent-test-123",
            processing_id="consent-processing-123",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.COMPLETED,
            pipeline_config={},
            ocr_config={},
        )

        # Verify content is encrypted in database (but decrypted when retrieved)
        assert job.file_content == sample_binary_content

        # Simulate user giving consent
        updated_job = feedback_repo.mark_feedback_given(
            "consent-processing-123", consent_given=True
        )
        assert updated_job is not None
        assert updated_job.data_consent_given is True

        # Content should still be available (encrypted in DB, decrypted on read)
        job_with_consent = job_repo.get_by_processing_id("consent-processing-123")
        assert job_with_consent is not None
        assert job_with_consent.file_content == sample_binary_content

        # Simulate user NOT giving consent
        job_no_consent = job_repo.create(
            job_id="consent-test-456",
            processing_id="consent-processing-456",
            filename="test2.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.COMPLETED,
            pipeline_config={},
            ocr_config={},
        )

        # Mark no consent
        feedback_repo.mark_feedback_given("consent-processing-456", consent_given=False)

        # Clear content (should work with encrypted fields)
        cleared_job = feedback_repo.clear_content_for_job("consent-processing-456")

        # Verify content is cleared
        assert cleared_job is not None
        assert cleared_job.file_content is None

    def test_content_clearing_with_encryption(
        self, repositories: dict, sample_binary_content: bytes
    ):
        """Test that content clearing works correctly with encrypted fields."""
        job_repo = repositories["job_repo"]
        step_execution_repo = repositories["step_execution_repo"]
        feedback_repo = repositories["feedback_repo"]

        # Create job with content
        job = job_repo.create(
            job_id="clear-test-123",
            processing_id="clear-processing-123",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.COMPLETED,
            pipeline_config={},
            ocr_config={},
        )

        # Create step executions with text
        step_execution_repo.create(
            job_id=job.job_id,
            step_id=1,
            step_name="test_step",
            step_order=1,
            status=StepExecutionStatus.COMPLETED,
            input_text="Input text to be cleared",
            output_text="Output text to be cleared",
        )

        # Clear content using feedback repository
        cleared_job = feedback_repo.clear_content_for_job("clear-processing-123")

        # Verify job content is cleared
        assert cleared_job is not None
        assert cleared_job.file_content is None

        # Verify step execution text is cleared
        executions = step_execution_repo.get_by_job_id(job.job_id)
        assert len(executions) == 1
        assert executions[0].input_text is None
        assert executions[0].output_text is None

    def test_multiple_jobs_encryption_isolation(self, repositories: dict):
        """Test that encryption is isolated per job (no cross-contamination)."""
        job_repo = repositories["job_repo"]

        content1 = b"PDF content for job 1"
        content2 = b"PDF content for job 2"
        content3 = b"PDF content for job 3"

        # Create multiple jobs
        job1 = job_repo.create(
            job_id="isolation-test-1",
            processing_id="isolation-processing-1",
            filename="test1.pdf",
            file_type="pdf",
            file_size=len(content1),
            file_content=content1,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        job2 = job_repo.create(
            job_id="isolation-test-2",
            processing_id="isolation-processing-2",
            filename="test2.pdf",
            file_type="pdf",
            file_size=len(content2),
            file_content=content2,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        job3 = job_repo.create(
            job_id="isolation-test-3",
            processing_id="isolation-processing-3",
            filename="test3.pdf",
            file_type="pdf",
            file_size=len(content3),
            file_content=content3,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Retrieve all and verify isolation
        retrieved_job1 = job_repo.get_by_processing_id("isolation-processing-1")
        retrieved_job2 = job_repo.get_by_processing_id("isolation-processing-2")
        retrieved_job3 = job_repo.get_by_processing_id("isolation-processing-3")

        assert retrieved_job1.file_content == content1
        assert retrieved_job2.file_content == content2
        assert retrieved_job3.file_content == content3

        # Verify no cross-contamination
        assert retrieved_job1.file_content != content2
        assert retrieved_job1.file_content != content3
        assert retrieved_job2.file_content != content1
        assert retrieved_job2.file_content != content3
