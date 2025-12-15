"""
Pipeline Job Repository

Provides data access methods for pipeline job management including CRUD operations
and job status tracking.

Includes transparent encryption for file_content field (binary PDF/image files).
"""

import logging
from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import PipelineJobDB, StepExecutionStatus
from app.repositories.base_repository import BaseRepository, EncryptedRepositoryMixin

logger = logging.getLogger(__name__)


class PipelineJobRepository(EncryptedRepositoryMixin, BaseRepository[PipelineJobDB]):
    """
    Repository for pipeline job data access operations.

    Encrypted fields:
    - file_content: Binary PDF/image files
    - result_data: JSON containing medical content (original_text, translated_text)

    IMPORTANT: EncryptedRepositoryMixin must come FIRST in inheritance order
    so that its create()/update()/get*() methods override BaseRepository methods.
    """

    # Define fields to encrypt
    encrypted_fields = ["file_content", "result_data"]

    def __init__(self, db: Session):
        super().__init__(db, PipelineJobDB)

    def get_by_job_id(self, job_id: str) -> PipelineJobDB | None:
        """
        Get pipeline job by job_id (UUID string).

        Args:
            job_id: Job UUID string

        Returns:
            Pipeline job instance with decrypted file_content (detached from session), or None if not found
        """
        try:
            job = self.db.query(PipelineJobDB).filter(PipelineJobDB.job_id == job_id).first()
            decrypted_job = self._decrypt_entity(job)
            
            # Expunge to prevent accidental overwrites of decrypted data
            if decrypted_job:
                self.db.expunge(decrypted_job)
                logger.debug(f"Expunged PipelineJobDB entity (id={decrypted_job.id}) after decryption in get_by_job_id()")
            
            return decrypted_job
        except Exception as e:
            logger.error(f"Error getting pipeline job by job_id={job_id}: {e}")
            raise

    def get_by_processing_id(self, processing_id: str) -> PipelineJobDB | None:
        """
        Get pipeline job by processing_id.

        Args:
            processing_id: Processing ID string

        Returns:
            Pipeline job instance with decrypted file_content (detached from session), or None if not found
        """
        try:
            job = (
                self.db.query(PipelineJobDB)
                .filter(PipelineJobDB.processing_id == processing_id)
                .first()
            )
            decrypted_job = self._decrypt_entity(job)
            
            # Expunge to prevent accidental overwrites of decrypted data
            if decrypted_job:
                self.db.expunge(decrypted_job)
                logger.debug(f"Expunged PipelineJobDB entity (id={decrypted_job.id}) after decryption in get_by_processing_id()")
            
            return decrypted_job
        except Exception as e:
            logger.error(f"Error getting pipeline job by processing_id={processing_id}: {e}")
            raise

    def get_by_status(
        self, status: StepExecutionStatus, skip: int = 0, limit: int = 100
    ) -> list[PipelineJobDB]:
        """
        Get pipeline jobs by status.

        Args:
            status: Job status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of pipeline job instances with decrypted file_content (detached from session)
        """
        try:
            jobs = (
                self.db.query(PipelineJobDB)
                .filter(PipelineJobDB.status == status)
                .offset(skip)
                .limit(limit)
                .all()
            )
            decrypted_jobs = self._decrypt_entities(jobs)
            
            # Expunge all to prevent accidental overwrites of decrypted data
            for job in decrypted_jobs:
                self.db.expunge(job)
            logger.debug(f"Expunged {len(decrypted_jobs)} PipelineJobDB entities after decryption in get_by_status()")
            
            return decrypted_jobs
        except Exception as e:
            logger.error(f"Error getting pipeline jobs by status={status}: {e}")
            raise

    def get_pending_jobs(self, limit: int = 100) -> list[PipelineJobDB]:
        """
        Get pending pipeline jobs.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of pending pipeline job instances
        """
        return self.get_by_status(StepExecutionStatus.PENDING, skip=0, limit=limit)

    def get_completed_jobs(
        self, skip: int = 0, limit: int = 100
    ) -> list[PipelineJobDB]:
        """
        Get completed pipeline jobs.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of completed pipeline job instances
        """
        return self.get_by_status(StepExecutionStatus.COMPLETED, skip=skip, limit=limit)

    def get_failed_jobs(self, skip: int = 0, limit: int = 100) -> list[PipelineJobDB]:
        """
        Get failed pipeline jobs.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of failed pipeline job instances
        """
        return self.get_by_status(StepExecutionStatus.FAILED, skip=skip, limit=limit)

    def update_status(
        self, job_id: str, status: StepExecutionStatus, **kwargs
    ) -> PipelineJobDB | None:
        """
        Update pipeline job status and optionally other fields.

        Args:
            job_id: Job UUID string
            status: New status
            **kwargs: Additional fields to update

        Returns:
            Updated pipeline job instance with decrypted file_content, or None if not found
        """
        try:
            kwargs["status"] = status
            job = self.get_by_job_id(job_id)
            if not job:
                return None

            return self.update(job.id, **kwargs)
        except Exception as e:
            logger.error(f"Error updating status for job_id={job_id}: {e}")
            raise

    def clear_file_content(self, job_id: str) -> PipelineJobDB | None:
        """
        Clear file_content for a job (GDPR compliance).

        Sets file_content to None, preserving other job data.

        Args:
            job_id: Job UUID string

        Returns:
            Updated pipeline job instance, or None if not found
        """
        try:
            job = self.get_by_job_id(job_id)
            if not job:
                return None

            # Set file_content to None (will be stored as NULL in database)
            return self.update(job.id, file_content=None)
        except Exception as e:
            logger.error(f"Error clearing file_content for job_id={job_id}: {e}")
            raise

    def get_jobs_without_consent(
        self, older_than_hours: int = 1
    ) -> list[PipelineJobDB]:
        """
        Get jobs without user consent that are older than specified hours.

        Used for GDPR cleanup of jobs where user did not give consent.

        Args:
            older_than_hours: Minimum age in hours

        Returns:
            List of pipeline job instances (detached from session)
        """
        try:
            from datetime import datetime, timedelta

            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

            jobs = (
                self.db.query(PipelineJobDB)
                .filter(
                    and_(
                        PipelineJobDB.data_consent_given == False,  # noqa: E712
                        PipelineJobDB.created_at < cutoff_time,
                    )
                )
                .all()
            )

            decrypted_jobs = self._decrypt_entities(jobs)
            
            # Expunge all to prevent accidental overwrites of decrypted data
            for job in decrypted_jobs:
                self.db.expunge(job)
            logger.debug(f"Expunged {len(decrypted_jobs)} PipelineJobDB entities after decryption in get_jobs_without_consent()")
            
            return decrypted_jobs
        except Exception as e:
            logger.error(f"Error getting jobs without consent: {e}")
            raise
