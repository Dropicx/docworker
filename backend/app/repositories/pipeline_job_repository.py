"""
Pipeline Job Repository

Handles database operations for pipeline jobs (document processing tasks).
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus
from app.repositories.base_repository import BaseRepository


class PipelineJobRepository(BaseRepository[PipelineJobDB]):
    """
    Repository for Pipeline Job operations.

    Provides specialized queries for managing document processing jobs
    beyond basic CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize pipeline job repository.

        Args:
            db: Database session
        """
        super().__init__(db, PipelineJobDB)

    def get_by_processing_id(self, processing_id: str) -> PipelineJobDB | None:
        """
        Get job by processing ID (UUID).

        Args:
            processing_id: Unique processing identifier

        Returns:
            Job instance or None if not found
        """
        return self.db.query(self.model).filter_by(processing_id=processing_id).first()

    def get_active_jobs(self) -> list[PipelineJobDB]:
        """
        Get all active (running) jobs.

        Returns:
            List of jobs with RUNNING status
        """
        return self.db.query(self.model).filter_by(status=StepExecutionStatus.RUNNING).all()

    def get_pending_jobs(self) -> list[PipelineJobDB]:
        """
        Get all pending jobs waiting to start.

        Returns:
            List of jobs with PENDING status
        """
        return self.db.query(self.model).filter_by(status=StepExecutionStatus.PENDING).all()

    def get_completed_jobs(
        self, limit: int | None = None, since: datetime | None = None
    ) -> list[PipelineJobDB]:
        """
        Get completed jobs with optional filters.

        Args:
            limit: Maximum number of jobs to return
            since: Only return jobs completed after this time

        Returns:
            List of completed jobs
        """
        query = self.db.query(self.model).filter_by(status=StepExecutionStatus.COMPLETED)

        if since:
            query = query.filter(self.model.updated_at >= since)

        query = query.order_by(self.model.updated_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_failed_jobs(
        self, limit: int | None = None, since: datetime | None = None
    ) -> list[PipelineJobDB]:
        """
        Get failed jobs with optional filters.

        Args:
            limit: Maximum number of jobs to return
            since: Only return jobs that failed after this time

        Returns:
            List of failed jobs
        """
        query = self.db.query(self.model).filter_by(status=StepExecutionStatus.FAILED)

        if since:
            query = query.filter(self.model.updated_at >= since)

        query = query.order_by(self.model.updated_at.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_jobs_by_status(self, status: StepExecutionStatus) -> list[PipelineJobDB]:
        """
        Get all jobs with a specific status.

        Args:
            status: Job status to filter by

        Returns:
            List of jobs with the given status
        """
        return self.db.query(self.model).filter_by(status=status).all()

    def get_recent_jobs(self, hours: int = 24, limit: int | None = None) -> list[PipelineJobDB]:
        """
        Get jobs created in the last N hours.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of jobs to return

        Returns:
            List of recent jobs
        """
        since = datetime.now() - timedelta(hours=hours)
        query = (
            self.db.query(self.model)
            .filter(self.model.created_at >= since)
            .order_by(self.model.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    def update_job_status(
        self, processing_id: str, status: StepExecutionStatus, error_message: str | None = None
    ) -> PipelineJobDB | None:
        """
        Update job status and optional error message.

        Args:
            processing_id: Job processing ID
            status: New status
            error_message: Optional error message (for FAILED status)

        Returns:
            Updated job or None if not found
        """
        job = self.get_by_processing_id(processing_id)
        if not job:
            return None

        job.status = status
        if error_message:
            job.error_message = error_message

        job.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_progress(
        self, processing_id: str, progress_percent: int, current_step: str | None = None
    ) -> PipelineJobDB | None:
        """
        Update job progress information.

        Args:
            processing_id: Job processing ID
            progress_percent: Progress percentage (0-100)
            current_step: Optional current step description

        Returns:
            Updated job or None if not found
        """
        job = self.get_by_processing_id(processing_id)
        if not job:
            return None

        # Clamp progress to 0-100 range
        job.progress_percent = max(0, min(100, progress_percent))
        if current_step:
            job.current_step = current_step

        job.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(job)
        return job

    def set_job_result(
        self,
        processing_id: str,
        result_data: dict,
        status: StepExecutionStatus = StepExecutionStatus.COMPLETED,
    ) -> PipelineJobDB | None:
        """
        Set job result data and mark as completed.

        Args:
            processing_id: Job processing ID
            result_data: Job result data dictionary
            status: Final job status (default: COMPLETED)

        Returns:
            Updated job or None if not found
        """
        job = self.get_by_processing_id(processing_id)
        if not job:
            return None

        job.result_data = result_data
        job.status = status
        job.progress_percent = 100
        job.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(job)
        return job

    def set_job_error(
        self,
        processing_id: str,
        error_message: str | None,
    ) -> PipelineJobDB | None:
        """
        Set job error message and mark as failed.

        Args:
            processing_id: Job processing ID
            error_message: Error message describing the failure

        Returns:
            Updated job or None if not found
        """
        job = self.get_by_processing_id(processing_id)
        if not job:
            return None

        job.error_message = error_message
        job.status = StepExecutionStatus.FAILED
        job.updated_at = datetime.now()

        self.db.commit()
        self.db.refresh(job)
        return job

    def count_by_status(self) -> dict[StepExecutionStatus, int]:
        """
        Count jobs grouped by status.

        Returns:
            Dictionary mapping status to count
        """
        from collections import defaultdict

        jobs = self.db.query(self.model).all()
        counts = defaultdict(int)

        for job in jobs:
            counts[job.status] += 1

        return dict(counts)

    def cleanup_old_jobs(self, days: int = 7) -> int:
        """
        Delete completed jobs older than specified days.

        Args:
            days: Number of days to keep

        Returns:
            Number of jobs deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        jobs_to_delete = (
            self.db.query(self.model)
            .filter(self.model.created_at < cutoff_date)
            .filter(self.model.status == StepExecutionStatus.COMPLETED)
            .all()
        )

        count = len(jobs_to_delete)

        for job in jobs_to_delete:
            self.db.delete(job)

        self.db.commit()
        return count

    def get_job_statistics(self, since: datetime | None = None) -> dict:
        """
        Get aggregate statistics about jobs.

        Args:
            since: Only include jobs created after this time

        Returns:
            Dictionary with statistics (total, completed, failed, etc.)
        """
        query = self.db.query(self.model)

        if since:
            query = query.filter(self.model.created_at >= since)

        jobs = query.all()

        return {
            "total": len(jobs),
            "pending": sum(1 for j in jobs if j.status == StepExecutionStatus.PENDING),
            "running": sum(1 for j in jobs if j.status == StepExecutionStatus.RUNNING),
            "completed": sum(1 for j in jobs if j.status == StepExecutionStatus.COMPLETED),
            "failed": sum(1 for j in jobs if j.status == StepExecutionStatus.FAILED),
            "skipped": sum(1 for j in jobs if j.status == StepExecutionStatus.SKIPPED),
        }
