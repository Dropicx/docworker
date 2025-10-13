"""
Pipeline Step Execution Repository

Handles database operations for pipeline step execution logs and audit trail.
"""

from datetime import datetime
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import PipelineStepExecutionDB
from app.repositories.base_repository import BaseRepository


class PipelineStepExecutionRepository(BaseRepository[PipelineStepExecutionDB]):
    """
    Repository for Pipeline Step Execution operations.

    Provides specialized queries for execution logs, statistics,
    and audit trail beyond basic CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize pipeline step execution repository.

        Args:
            db: Database session
        """
        super().__init__(db, PipelineStepExecutionDB)

    def get_by_job_id(self, job_id: int) -> list[PipelineStepExecutionDB]:
        """
        Get all step executions for a specific job.

        Args:
            job_id: Pipeline job ID

        Returns:
            List of step executions ordered by step order
        """
        return self.db.query(self.model).filter_by(
            job_id=job_id
        ).order_by(self.model.step_order).all()

    def get_recent_executions(self, limit: int = 100) -> list[PipelineStepExecutionDB]:
        """
        Get most recent step executions.

        Args:
            limit: Maximum number of executions to return

        Returns:
            List of recent executions ordered by started_at descending
        """
        return self.db.query(self.model).order_by(
            desc(self.model.started_at)
        ).limit(limit).all()

    def get_executions_since(self, since: datetime) -> list[PipelineStepExecutionDB]:
        """
        Get executions since a specific timestamp.

        Args:
            since: Timestamp to filter from

        Returns:
            List of executions since the timestamp
        """
        return self.db.query(self.model).filter(
            self.model.started_at >= since
        ).all()

    def count_since(self, since: datetime) -> int:
        """
        Count executions since a specific timestamp.

        Args:
            since: Timestamp to filter from

        Returns:
            Count of executions
        """
        return self.db.query(self.model).filter(
            self.model.started_at >= since
        ).count()

    def get_average_execution_time(self, limit: int = 100) -> float:
        """
        Get average execution time for recent executions.

        Args:
            limit: Number of recent executions to average

        Returns:
            Average execution time in seconds, or 0 if no data
        """
        avg_time = self.db.query(
            func.avg(self.model.execution_time_seconds)
        ).filter(
            self.model.execution_time_seconds.isnot(None)
        ).limit(limit).scalar()

        return float(avg_time) if avg_time else 0.0

    def get_step_usage_statistics(self) -> list[tuple[int, int]]:
        """
        Get usage statistics for each step (step_id, count).

        Returns:
            List of tuples (step_id, count) ordered by count descending
        """
        return self.db.query(
            self.model.step_id,
            func.count(self.model.step_id).label('count')
        ).group_by(
            self.model.step_id
        ).order_by(
            desc('count')
        ).all()

    def get_most_used_step_id(self) -> int | None:
        """
        Get the ID of the most frequently executed step.

        Returns:
            Step ID or None if no executions
        """
        result = self.db.query(
            self.model.step_id,
            func.count(self.model.step_id).label('count')
        ).group_by(
            self.model.step_id
        ).order_by(
            desc('count')
        ).first()

        return result.step_id if result else None

    def get_by_status(self, status: str) -> list[PipelineStepExecutionDB]:
        """
        Get executions by status.

        Args:
            status: Status to filter by (COMPLETED, FAILED, SKIPPED, TERMINATED)

        Returns:
            List of executions with the specified status
        """
        return self.db.query(self.model).filter_by(status=status).all()

    def get_failed_executions(self, limit: int = 100) -> list[PipelineStepExecutionDB]:
        """
        Get recent failed executions.

        Args:
            limit: Maximum number to return

        Returns:
            List of failed executions ordered by started_at descending
        """
        return self.db.query(self.model).filter_by(
            status="FAILED"
        ).order_by(
            desc(self.model.started_at)
        ).limit(limit).all()

    def get_success_rate(self, limit: int = 100) -> float:
        """
        Calculate success rate for recent executions.

        Args:
            limit: Number of recent executions to analyze

        Returns:
            Success rate as percentage (0-100)
        """
        recent = self.get_recent_executions(limit)
        if not recent:
            return 100.0

        success_count = sum(1 for log in recent if log.status == "COMPLETED")
        return (success_count / len(recent)) * 100

    def delete_old_executions(self, older_than: datetime) -> int:
        """
        Delete execution logs older than specified date.

        Args:
            older_than: Delete logs older than this timestamp

        Returns:
            Number of deleted records
        """
        try:
            deleted = self.db.query(self.model).filter(
                self.model.started_at < older_than
            ).delete()
            self.db.commit()
            return deleted
        except Exception:
            self.db.rollback()
            return 0
