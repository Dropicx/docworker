"""
Tests for PipelineJobRepository with encryption support.

Tests encryption/decryption of file_content (binary field).
"""

import pytest
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus
from app.repositories.pipeline_job_repository import PipelineJobRepository


@pytest.fixture
def job_repository(db_session: Session) -> PipelineJobRepository:
    """Create a PipelineJobRepository instance."""
    return PipelineJobRepository(db_session)


@pytest.fixture
def sample_binary_content() -> bytes:
    """Sample binary content for testing (simulates PDF file)."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


class TestPipelineJobRepositoryEncryption:
    """Test encryption/decryption of file_content."""

    def test_create_job_encrypts_file_content(
        self, job_repository: PipelineJobRepository, sample_binary_content: bytes
    ):
        """Test that file_content is encrypted when creating a job."""
        job = job_repository.create(
            job_id="test-job-123",
            processing_id="test-processing-123",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Verify job was created
        assert job is not None
        assert job.job_id == "test-job-123"

        # Verify file_content is decrypted when retrieved (transparent decryption)
        assert job.file_content == sample_binary_content

        # Verify in database it's encrypted (query directly)
        db_job = job_repository.db.query(PipelineJobDB).filter_by(id=job.id).first()
        assert db_job is not None

        # Check that stored value is encrypted (not plaintext)
        stored_content = db_job.file_content
        if isinstance(stored_content, bytes):
            stored_content_str = stored_content.decode("utf-8", errors="ignore")
        else:
            stored_content_str = str(stored_content)

        # Should be encrypted (base64-encoded Fernet token)
        assert stored_content_str != sample_binary_content.decode("utf-8", errors="ignore")
        assert len(stored_content_str) > len(sample_binary_content)  # Encrypted is larger

    def test_get_job_decrypts_file_content(
        self, job_repository: PipelineJobRepository, sample_binary_content: bytes
    ):
        """Test that file_content is decrypted when retrieving a job."""
        # Create job
        job = job_repository.create(
            job_id="test-job-456",
            processing_id="test-processing-456",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Retrieve job by ID
        retrieved_job = job_repository.get_by_id(job.id)

        # Verify file_content is decrypted
        assert retrieved_job is not None
        assert retrieved_job.file_content == sample_binary_content

    def test_get_job_by_processing_id_decrypts(
        self, job_repository: PipelineJobRepository, sample_binary_content: bytes
    ):
        """Test that file_content is decrypted when retrieving by processing_id."""
        # Create job
        job = job_repository.create(
            job_id="test-job-789",
            processing_id="test-processing-789",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Retrieve job by processing_id
        retrieved_job = job_repository.get_by_processing_id("test-processing-789")

        # Verify file_content is decrypted
        assert retrieved_job is not None
        assert retrieved_job.file_content == sample_binary_content

    def test_update_job_encrypts_new_file_content(
        self, job_repository: PipelineJobRepository, sample_binary_content: bytes
    ):
        """Test that updating file_content encrypts the new value."""
        # Create job
        job = job_repository.create(
            job_id="test-job-update",
            processing_id="test-processing-update",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Update with new content
        new_content = b"New PDF content for update test"
        updated_job = job_repository.update(job.id, file_content=new_content)

        # Verify updated content is decrypted
        assert updated_job is not None
        assert updated_job.file_content == new_content

        # Verify old content is gone
        assert updated_job.file_content != sample_binary_content

    def test_clear_file_content_sets_to_none(
        self, job_repository: PipelineJobRepository, sample_binary_content: bytes
    ):
        """Test that clearing file_content sets it to None."""
        # Create job
        job = job_repository.create(
            job_id="test-job-clear",
            processing_id="test-processing-clear",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Clear file content
        cleared_job = job_repository.clear_file_content(job.job_id)

        # Verify file_content is None
        assert cleared_job is not None
        assert cleared_job.file_content is None

    def test_large_file_content_encryption(self, job_repository: PipelineJobRepository):
        """Test encryption of large binary content (simulates large PDF)."""
        # Create large binary content (1MB)
        large_content = b"X" * (1024 * 1024)

        job = job_repository.create(
            job_id="test-job-large",
            processing_id="test-processing-large",
            filename="large.pdf",
            file_type="pdf",
            file_size=len(large_content),
            file_content=large_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Verify large content is encrypted and decrypted correctly
        assert job is not None
        retrieved_job = job_repository.get_by_id(job.id)
        assert retrieved_job is not None
        assert retrieved_job.file_content == large_content
        assert len(retrieved_job.file_content) == 1024 * 1024

    def test_null_file_content_handling(self, job_repository: PipelineJobRepository):
        """Test that None file_content is handled correctly."""
        job = job_repository.create(
            job_id="test-job-null",
            processing_id="test-processing-null",
            filename="test.pdf",
            file_type="pdf",
            file_size=0,
            file_content=None,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Verify None is preserved
        assert job is not None
        retrieved_job = job_repository.get_by_id(job.id)
        assert retrieved_job is not None
        assert retrieved_job.file_content is None

    def test_binary_round_trip(
        self, job_repository: PipelineJobRepository, sample_binary_content: bytes
    ):
        """Test complete round-trip: create → retrieve → verify binary integrity."""
        # Create
        job = job_repository.create(
            job_id="test-job-roundtrip",
            processing_id="test-processing-roundtrip",
            filename="test.pdf",
            file_type="pdf",
            file_size=len(sample_binary_content),
            file_content=sample_binary_content,
            status=StepExecutionStatus.PENDING,
            pipeline_config={},
            ocr_config={},
        )

        # Retrieve
        retrieved_job = job_repository.get_by_processing_id("test-processing-roundtrip")

        # Verify binary integrity
        assert retrieved_job is not None
        assert retrieved_job.file_content == sample_binary_content
        assert len(retrieved_job.file_content) == len(sample_binary_content)

        # Verify byte-by-byte match
        assert retrieved_job.file_content == sample_binary_content
