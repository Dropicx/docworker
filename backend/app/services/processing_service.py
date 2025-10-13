"""
Processing Service

Handles business logic for document processing workflows.
Coordinates between repositories and external services (Celery).
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import StepExecutionStatus
from app.models.document import ProcessingStatus
from app.repositories.pipeline_job_repository import PipelineJobRepository

logger = logging.getLogger(__name__)


class ProcessingService:
    """
    Service for managing document processing operations.

    This service encapsulates the business logic for document processing,
    delegating database operations to repositories and coordinating with
    external services like Celery workers.
    """

    def __init__(
        self,
        session: Session,
        job_repository: PipelineJobRepository | None = None
    ):
        """
        Initialize processing service.

        Args:
            session: Database session
            job_repository: Optional job repository (for dependency injection)
        """
        self.session = session
        self.job_repository = job_repository or PipelineJobRepository(session)

    def start_processing(
        self,
        processing_id: str,
        options: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Start document processing with given options.

        Args:
            processing_id: Unique processing identifier
            options: Processing options (e.g., target_language)

        Returns:
            Dictionary with processing start information

        Raises:
            ValueError: If job not found
            RuntimeError: If failed to queue task
        """
        # Get job from repository
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Processing job {processing_id} not found or expired")

        # Update job with processing options
        job.processing_options = options
        self.session.commit()

        logger.info(f"📋 Processing options saved for {processing_id[:8]}: {options}")

        # Enqueue to Celery worker
        try:
            from app.services.celery_client import enqueue_document_processing
            task_id = enqueue_document_processing(processing_id, options=options)
            logger.info(f"📤 Job queued to Redis: {processing_id[:8]} (task_id: {task_id})")

            return {
                "message": "Verarbeitung gestartet",
                "processing_id": processing_id,
                "status": "QUEUED",
                "task_id": task_id,
                "target_language": options.get('target_language')
            }

        except Exception as queue_error:
            logger.error(f"❌ Failed to queue task: {queue_error}")
            raise RuntimeError(f"Failed to queue processing task: {str(queue_error)}")

    def get_processing_status(self, processing_id: str) -> dict[str, Any]:
        """
        Get current processing status for a job.

        Args:
            processing_id: Unique processing identifier

        Returns:
            Dictionary with status information

        Raises:
            ValueError: If job not found
        """
        # Get job from repository
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Processing job {processing_id} not found")

        # Map database status to API status
        api_status = self._map_status_to_api(job.status)

        # Get step description
        current_step = self._get_step_description(job)

        return {
            "processing_id": processing_id,
            "status": api_status,
            "progress_percent": job.progress_percent,
            "current_step": current_step,
            "message": None,
            "error": job.error_message
        }

    def get_processing_result(self, processing_id: str) -> dict[str, Any]:
        """
        Get processing result for a completed job.

        Args:
            processing_id: Unique processing identifier

        Returns:
            Processing result data

        Raises:
            ValueError: If job not found or not completed
        """
        # Get job from repository
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Processing job {processing_id} not found")

        # Check if job is completed
        if job.status != StepExecutionStatus.COMPLETED:
            raise ValueError(
                f"Processing not completed yet. Status: {job.status}"
            )

        # Get result data
        result_data = job.result_data
        if not result_data:
            raise ValueError("Processing result not available")

        return result_data

    def get_active_processes(self) -> dict[str, Any]:
        """
        Get overview of all active processing jobs.

        Returns:
            Dictionary with active process information
        """
        from app.services.cleanup import processing_store
        from datetime import datetime

        active_processes = []

        for proc_id, data in processing_store.items():
            active_processes.append({
                "processing_id": proc_id[:8] + "...",  # Shortened for privacy
                "status": data.get("status"),
                "progress_percent": data.get("progress_percent", 0),
                "current_step": data.get("current_step"),
                "created_at": data.get("created_at"),
                "filename": data.get("filename", "").split("/")[-1] if data.get("filename") else None
            })

        return {
            "active_count": len(active_processes),
            "processes": active_processes,
            "timestamp": datetime.now()
        }

    def _map_status_to_api(self, db_status: StepExecutionStatus) -> ProcessingStatus:
        """
        Map database status to API status enum.

        Args:
            db_status: Database status

        Returns:
            API status enum value
        """
        status_mapping = {
            StepExecutionStatus.PENDING: ProcessingStatus.PENDING,
            StepExecutionStatus.RUNNING: ProcessingStatus.PROCESSING,
            StepExecutionStatus.COMPLETED: ProcessingStatus.COMPLETED,
            StepExecutionStatus.FAILED: ProcessingStatus.ERROR,
            StepExecutionStatus.SKIPPED: ProcessingStatus.ERROR
        }
        return status_mapping.get(db_status, ProcessingStatus.PENDING)

    def _get_step_description(self, job) -> str:
        """
        Get human-readable description of current processing step.

        Args:
            job: Pipeline job instance

        Returns:
            Step description string
        """
        if job.status == StepExecutionStatus.RUNNING:
            return f"Verarbeite Schritt {job.progress_percent}%"
        elif job.status == StepExecutionStatus.COMPLETED:
            return "Verarbeitung abgeschlossen"
        elif job.status == StepExecutionStatus.FAILED:
            return "Fehler bei Verarbeitung"
        return "Warten auf Verarbeitung..."
