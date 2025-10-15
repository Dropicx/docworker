"""
Unit Tests for PipelineJobRepository

Tests the repository pattern implementation for pipeline job data access.
Uses in-memory SQLite database for fast, isolated testing.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database.modular_pipeline_models import Base, PipelineJobDB, StepExecutionStatus
from app.repositories.pipeline_job_repository import PipelineJobRepository


# ==================== FIXTURES ====================

@pytest.fixture(scope="function")
def db_session() -> Session:
    """Create an in-memory SQLite database session for each test."""
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def repository(db_session: Session) -> PipelineJobRepository:
    """Create a PipelineJobRepository instance for testing."""
    return PipelineJobRepository(db_session)


@pytest.fixture
def sample_job(db_session: Session) -> PipelineJobDB:
    """Create a sample pipeline job for testing."""
    job = PipelineJobDB(
        job_id="job-test-123",
        processing_id="test-123",
        filename="test_document.pdf",
        file_type="pdf",
        file_size=1024,
        file_content=b"test content",
        pipeline_config={"steps": []},
        ocr_config={"enabled": True},
        status=StepExecutionStatus.PENDING,
        progress_percent=0,
        result_data=None,
        error_message=None
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ==================== BASE REPOSITORY TESTS ====================

def test_create_job(repository: PipelineJobRepository):
    """Test creating a new pipeline job."""
    # Arrange
    job_id = "job-create-test-123"
    processing_id = "create-test-123"
    filename = "new_document.pdf"

    # Act
    job = repository.create(
        job_id=job_id,
        processing_id=processing_id,
        filename=filename,
        file_type="pdf",
        file_size=2048,
        file_content=b"test file content",
        pipeline_config={"steps": []},
        ocr_config={"enabled": True},
        status=StepExecutionStatus.PENDING,
        progress_percent=0
    )

    # Assert
    assert job.id is not None
    assert job.job_id == job_id
    assert job.processing_id == processing_id
    assert job.filename == filename
    assert job.status == StepExecutionStatus.PENDING
    assert job.progress_percent == 0


def test_get_by_id(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test retrieving a job by ID."""
    # Act
    retrieved_job = repository.get(sample_job.id)

    # Assert
    assert retrieved_job is not None
    assert retrieved_job.id == sample_job.id
    assert retrieved_job.processing_id == sample_job.processing_id


def test_get_nonexistent_job(repository: PipelineJobRepository):
    """Test retrieving a job that doesn't exist."""
    # Act
    job = repository.get(99999)

    # Assert
    assert job is None


def test_get_all_jobs(repository: PipelineJobRepository, db_session: Session):
    """Test retrieving all jobs."""
    # Arrange - Create multiple jobs
    for i in range(3):
        job = PipelineJobDB(
            job_id=f"job-test-{i}",
            processing_id=f"test-{i}",
            filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1024,
            file_content=b"test content",
            pipeline_config={"steps": []},
            ocr_config={"enabled": True},
            status=StepExecutionStatus.PENDING,
            progress_percent=0
        )
        db_session.add(job)
    db_session.commit()

    # Act
    all_jobs = repository.get_all()

    # Assert
    assert len(all_jobs) == 3
    assert all(isinstance(job, PipelineJobDB) for job in all_jobs)


def test_update_job(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test updating a job."""
    # Arrange
    new_status = StepExecutionStatus.RUNNING
    new_progress = 50

    # Act
    updated_job = repository.update(
        sample_job.id,
        status=new_status,
        progress_percent=new_progress
    )

    # Assert
    assert updated_job is not None
    assert updated_job.status == new_status
    assert updated_job.progress_percent == new_progress


def test_delete_job(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test deleting a job."""
    # Act
    success = repository.delete(sample_job.id)

    # Assert
    assert success is True
    assert repository.get(sample_job.id) is None


def test_delete_nonexistent_job(repository: PipelineJobRepository):
    """Test deleting a job that doesn't exist."""
    # Act
    success = repository.delete(99999)

    # Assert
    assert success is False


# ==================== PIPELINE JOB REPOSITORY-SPECIFIC TESTS ====================

def test_get_by_processing_id(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test retrieving a job by processing ID."""
    # Act
    job = repository.get_by_processing_id(sample_job.processing_id)

    # Assert
    assert job is not None
    assert job.processing_id == sample_job.processing_id
    assert job.id == sample_job.id


def test_get_by_processing_id_not_found(repository: PipelineJobRepository):
    """Test retrieving a job with non-existent processing ID."""
    # Act
    job = repository.get_by_processing_id("non-existent-id")

    # Assert
    assert job is None


def test_get_active_jobs(repository: PipelineJobRepository, db_session: Session):
    """Test retrieving all active (running) jobs."""
    # Arrange - Create jobs with different statuses
    statuses = [
        StepExecutionStatus.RUNNING,
        StepExecutionStatus.RUNNING,
        StepExecutionStatus.PENDING,
        StepExecutionStatus.COMPLETED,
        StepExecutionStatus.FAILED
    ]

    for i, status in enumerate(statuses):
        job = PipelineJobDB(
            job_id=f"job-active-test-{i}",
            processing_id=f"test-{i}",
            filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1024,
            file_content=b"test content",
            pipeline_config={"steps": []},
            ocr_config={"enabled": True},
            status=status,
            progress_percent=0
        )
        db_session.add(job)
    db_session.commit()

    # Act
    active_jobs = repository.get_active_jobs()

    # Assert
    assert len(active_jobs) == 2  # Only RUNNING jobs
    assert all(job.status == StepExecutionStatus.RUNNING for job in active_jobs)


def test_get_pending_jobs(repository: PipelineJobRepository, db_session: Session):
    """Test retrieving all pending jobs."""
    # Arrange
    statuses = [
        StepExecutionStatus.PENDING,
        StepExecutionStatus.PENDING,
        StepExecutionStatus.RUNNING,
        StepExecutionStatus.COMPLETED
    ]

    for i, status in enumerate(statuses):
        job = PipelineJobDB(
            job_id=f"job-pending-test-{i}",
            processing_id=f"test-{i}",
            filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1024,
            file_content=b"test content",
            pipeline_config={"steps": []},
            ocr_config={"enabled": True},
            status=status,
            progress_percent=0
        )
        db_session.add(job)
    db_session.commit()

    # Act
    pending_jobs = repository.get_pending_jobs()

    # Assert
    assert len(pending_jobs) == 2
    assert all(job.status == StepExecutionStatus.PENDING for job in pending_jobs)


def test_update_job_status(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test updating job status."""
    # Arrange
    new_status = StepExecutionStatus.COMPLETED

    # Act
    updated_job = repository.update_job_status(sample_job.id, new_status)

    # Assert
    assert updated_job is not None
    assert updated_job.status == new_status


def test_update_job_progress(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test updating job progress."""
    # Arrange
    new_progress = 75

    # Act
    updated_job = repository.update_job_progress(sample_job.id, new_progress)

    # Assert
    assert updated_job is not None
    assert updated_job.progress_percent == new_progress


def test_update_job_progress_invalid(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test updating job progress with invalid value."""
    # Act & Assert - should clamp to 0-100
    job = repository.update_job_progress(sample_job.id, 150)
    assert job.progress_percent <= 100

    job = repository.update_job_progress(sample_job.id, -10)
    assert job.progress_percent >= 0


def test_set_job_result(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test setting job result data."""
    # Arrange
    result_data = {
        "translated_text": "Übersetzter Text",
        "document_type": "ARZTBRIEF",
        "target_language": "en"
    }

    # Act
    updated_job = repository.set_job_result(sample_job.id, result_data)

    # Assert
    assert updated_job is not None
    assert updated_job.result_data == result_data
    assert updated_job.status == StepExecutionStatus.COMPLETED


def test_set_job_error(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test setting job error."""
    # Arrange
    error_message = "Translation failed: Connection timeout"

    # Act
    updated_job = repository.set_job_error(sample_job.id, error_message)

    # Assert
    assert updated_job is not None
    assert updated_job.error_message == error_message
    assert updated_job.status == StepExecutionStatus.FAILED


def test_get_jobs_by_status(repository: PipelineJobRepository, db_session: Session):
    """Test filtering jobs by status."""
    # Arrange
    for i in range(5):
        status = StepExecutionStatus.COMPLETED if i % 2 == 0 else StepExecutionStatus.FAILED
        job = PipelineJobDB(
            job_id=f"job-status-test-{i}",
            processing_id=f"test-{i}",
            filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1024,
            file_content=b"test content",
            pipeline_config={"steps": []},
            ocr_config={"enabled": True},
            status=status,
            progress_percent=100 if status == StepExecutionStatus.COMPLETED else 50
        )
        db_session.add(job)
    db_session.commit()

    # Act
    completed_jobs = repository.get_jobs_by_status(StepExecutionStatus.COMPLETED)

    # Assert
    assert len(completed_jobs) == 3  # 0, 2, 4
    assert all(job.status == StepExecutionStatus.COMPLETED for job in completed_jobs)


def test_get_recent_jobs(repository: PipelineJobRepository, db_session: Session):
    """Test retrieving recent jobs."""
    # Arrange - Create jobs with different timestamps
    now = datetime.now()
    for i in range(5):
        job = PipelineJobDB(
            job_id=f"job-recent-test-{i}",
            processing_id=f"test-{i}",
            filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1024,
            file_content=b"test content",
            pipeline_config={"steps": []},
            ocr_config={"enabled": True},
            status=StepExecutionStatus.COMPLETED,
            progress_percent=100
        )
        db_session.add(job)
    db_session.commit()

    # Act
    recent_jobs = repository.get_recent_jobs(limit=3)

    # Assert
    assert len(recent_jobs) == 3
    # Should be ordered by created_at descending (newest first)
    assert recent_jobs[0].created_at > recent_jobs[1].created_at > recent_jobs[2].created_at


def test_cleanup_old_jobs(repository: PipelineJobRepository, db_session: Session):
    """Test cleaning up old completed jobs."""
    # Arrange - Create old and recent jobs
    now = datetime.now()
    old_date = now - timedelta(days=10)
    recent_date = now - timedelta(days=1)

    # Old completed job (should be deleted)
    old_job = PipelineJobDB(
        job_id="job-old-job",
        processing_id="old-job",
        filename="old.pdf",
        file_type="pdf",
        file_size=1024,
        file_content=b"old content",
        pipeline_config={"steps": []},
        ocr_config={"enabled": True},
        status=StepExecutionStatus.COMPLETED,
        progress_percent=100,
        created_at=old_date
    )

    # Recent completed job (should be kept)
    recent_job = PipelineJobDB(
        job_id="job-recent-job",
        processing_id="recent-job",
        filename="recent.pdf",
        file_type="pdf",
        file_size=1024,
        file_content=b"recent content",
        pipeline_config={"steps": []},
        ocr_config={"enabled": True},
        status=StepExecutionStatus.COMPLETED,
        progress_percent=100,
        created_at=recent_date
    )

    # Old failed job (should be kept - only clean completed jobs)
    old_failed_job = PipelineJobDB(
        job_id="job-old-failed",
        processing_id="old-failed",
        filename="old-failed.pdf",
        file_type="pdf",
        file_size=1024,
        file_content=b"failed content",
        pipeline_config={"steps": []},
        ocr_config={"enabled": True},
        status=StepExecutionStatus.FAILED,
        progress_percent=50,
        created_at=old_date
    )

    db_session.add_all([old_job, recent_job, old_failed_job])
    db_session.commit()

    # Act
    deleted_count = repository.cleanup_old_jobs(days=7)

    # Assert
    assert deleted_count == 1  # Only old completed job deleted
    assert repository.get_by_processing_id("old-job") is None
    assert repository.get_by_processing_id("recent-job") is not None
    assert repository.get_by_processing_id("old-failed") is not None


def test_count_by_status(repository: PipelineJobRepository, db_session: Session):
    """Test counting jobs by status."""
    # Arrange
    statuses = [
        StepExecutionStatus.PENDING,
        StepExecutionStatus.PENDING,
        StepExecutionStatus.RUNNING,
        StepExecutionStatus.COMPLETED,
        StepExecutionStatus.COMPLETED,
        StepExecutionStatus.COMPLETED,
        StepExecutionStatus.FAILED
    ]

    for i, status in enumerate(statuses):
        job = PipelineJobDB(
            job_id=f"job-count-test-{i}",
            processing_id=f"test-{i}",
            filename=f"doc_{i}.pdf",
            file_type="pdf",
            file_size=1024,
            file_content=b"test content",
            pipeline_config={"steps": []},
            ocr_config={"enabled": True},
            status=status,
            progress_percent=0
        )
        db_session.add(job)
    db_session.commit()

    # Act
    counts = repository.count_by_status()

    # Assert
    assert counts[StepExecutionStatus.PENDING] == 2
    assert counts[StepExecutionStatus.RUNNING] == 1
    assert counts[StepExecutionStatus.COMPLETED] == 3
    assert counts[StepExecutionStatus.FAILED] == 1


# ==================== EDGE CASES AND ERROR HANDLING ====================

def test_update_nonexistent_job(repository: PipelineJobRepository):
    """Test updating a job that doesn't exist."""
    # Act
    result = repository.update(99999, status=StepExecutionStatus.COMPLETED)

    # Assert
    assert result is None


def test_concurrent_updates(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test that updates are handled correctly."""
    # Act - Simulate concurrent updates
    repository.update_job_progress(sample_job.id, 25)
    repository.update_job_progress(sample_job.id, 50)
    repository.update_job_progress(sample_job.id, 75)

    # Assert
    final_job = repository.get(sample_job.id)
    assert final_job.progress_percent == 75


def test_empty_result_data(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test setting empty result data."""
    # Act
    updated_job = repository.set_job_result(sample_job.id, {})

    # Assert
    assert updated_job is not None
    assert updated_job.result_data == {}
    assert updated_job.status == StepExecutionStatus.COMPLETED


def test_null_error_message(repository: PipelineJobRepository, sample_job: PipelineJobDB):
    """Test setting null error message."""
    # Act
    updated_job = repository.set_job_error(sample_job.id, None)

    # Assert
    assert updated_job is not None
    assert updated_job.error_message is None
    assert updated_job.status == StepExecutionStatus.FAILED
