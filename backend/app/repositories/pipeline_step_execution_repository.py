"""
Pipeline Step Execution Repository

Provides data access methods for pipeline step execution tracking including CRUD operations
and step status management.

Includes transparent encryption for input_text and output_text fields.
"""

import logging
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import (
    PipelineStepExecutionDB,
    StepExecutionStatus,
)
from app.repositories.base_repository import BaseRepository, EncryptedRepositoryMixin

logger = logging.getLogger(__name__)


class PipelineStepExecutionRepository(
    EncryptedRepositoryMixin, BaseRepository[PipelineStepExecutionDB]
):
    """
    Repository for pipeline step execution data access operations.

    Encrypted fields: input_text, output_text

    IMPORTANT: EncryptedRepositoryMixin must come FIRST in inheritance order
    so that its create()/update()/get*() methods override BaseRepository methods.
    """

    # Define fields to encrypt
    encrypted_fields = ["input_text", "output_text"]

    def __init__(self, db: Session):
        super().__init__(db, PipelineStepExecutionDB)

    def get_by_job_id(self, job_id: str) -> list[PipelineStepExecutionDB]:
        """
        Get all step executions for a pipeline job.

        Args:
            job_id: Job UUID string

        Returns:
            List of step execution instances with decrypted input_text and output_text
        """
        try:
            executions = (
                self.db.query(PipelineStepExecutionDB)
                .filter(PipelineStepExecutionDB.job_id == job_id)
                .order_by(PipelineStepExecutionDB.step_order)
                .all()
            )
            return self._decrypt_entities(executions)
        except Exception as e:
            logger.error(f"Error getting step executions by job_id={job_id}: {e}")
            raise

    def get_by_step_name(
        self, job_id: str, step_name: str
    ) -> PipelineStepExecutionDB | None:
        """
        Get step execution by job_id and step_name.

        Args:
            job_id: Job UUID string
            step_name: Step name

        Returns:
            Step execution instance with decrypted fields, or None if not found
        """
        try:
            execution = (
                self.db.query(PipelineStepExecutionDB)
                .filter(
                    and_(
                        PipelineStepExecutionDB.job_id == job_id,
                        PipelineStepExecutionDB.step_name == step_name,
                    )
                )
                .first()
            )
            return self._decrypt_entity(execution)
        except Exception as e:
            logger.error(
                f"Error getting step execution by job_id={job_id}, step_name={step_name}: {e}"
            )
            raise

    def get_by_status(
        self, status: StepExecutionStatus, skip: int = 0, limit: int = 100
    ) -> list[PipelineStepExecutionDB]:
        """
        Get step executions by status.

        Args:
            status: Execution status to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of step execution instances with decrypted fields
        """
        try:
            executions = (
                self.db.query(PipelineStepExecutionDB)
                .filter(PipelineStepExecutionDB.status == status)
                .offset(skip)
                .limit(limit)
                .all()
            )
            return self._decrypt_entities(executions)
        except Exception as e:
            logger.error(f"Error getting step executions by status={status}: {e}")
            raise

    def clear_text_content(self, job_id: str) -> int:
        """
        Clear input_text and output_text for all step executions of a job (GDPR compliance).

        Sets input_text and output_text to None, preserving other execution data.

        Args:
            job_id: Job UUID string

        Returns:
            Number of step executions cleared
        """
        try:
            executions = self.get_by_job_id(job_id)
            cleared_count = 0

            for execution in executions:
                self.update(execution.id, input_text=None, output_text=None)
                cleared_count += 1

            logger.info(f"Cleared text content for {cleared_count} step executions (job_id={job_id})")
            return cleared_count
        except Exception as e:
            logger.error(f"Error clearing text content for job_id={job_id}: {e}")
            raise

    def get_failed_executions(
        self, job_id: str | None = None, limit: int = 100
    ) -> list[PipelineStepExecutionDB]:
        """
        Get failed step executions, optionally filtered by job_id.

        Args:
            job_id: Optional job UUID string to filter by
            limit: Maximum number of records to return

        Returns:
            List of failed step execution instances
        """
        try:
            query = self.db.query(PipelineStepExecutionDB).filter(
                PipelineStepExecutionDB.status == StepExecutionStatus.FAILED
            )

            if job_id:
                query = query.filter(PipelineStepExecutionDB.job_id == job_id)

            executions = query.limit(limit).all()
            return self._decrypt_entities(executions)
        except Exception as e:
            logger.error(f"Error getting failed executions: {e}")
            raise
