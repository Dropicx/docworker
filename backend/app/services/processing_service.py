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

# Step name → human-readable description mapping (used by router to enrich response)
# Keys must match actual step names from the dynamic_pipeline_steps database table
STEP_DESCRIPTIONS: dict[str, str] = {
    # Universal steps
    "Medical Content Validation": "Medizinischer Inhalt wird validiert...",
    "Document Classification": "Dokumenttyp wird erkannt...",
    "Patient-Friendly Translation": "KI vereinfacht den medizinischen Text...",
    "Medical Fact Check": "Medizinische Fakten werden geprüft...",
    "Grammar and Spelling Check": "Grammatik und Ausdruck werden optimiert...",
    "Language Translation": "Sprachübersetzung wird durchgeführt...",
    "Final Quality Check": "Qualitätsprüfung läuft...",
    "Text Formatting": "Formatierung wird abgeschlossen...",
    # Document-class-specific steps
    "Vereinfachung Arztbrief": "KI vereinfacht den Arztbrief...",
    "Vereinfachung Befundbericht": "KI vereinfacht den Befundbericht...",
    "Vereinfachung Laborwerte": "KI vereinfacht die Laborwerte...",
    "Finaler Check auf Richtigkeit": "Abschließende Qualitätsprüfung...",
}


class ProcessingService:
    """
    Service for managing document processing operations.

    This service encapsulates the business logic for document processing,
    delegating database operations to repositories and coordinating with
    external services like Celery workers.
    """

    def __init__(self, db: Session, job_repository: PipelineJobRepository | None = None):
        """
        Initialize processing service.

        Args:
            db: Database session
            job_repository: Optional job repository (for dependency injection)
        """
        self.db = db
        self.job_repository = job_repository or PipelineJobRepository(db)

    def start_processing(self, processing_id: str, options: dict[str, Any]) -> dict[str, Any]:
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
        # Get job from repository (entity is already expunged/detached)
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Processing job {processing_id} not found or expired")

        # Note: The repository already expunges the entity, so it's detached from the session.
        # No need to expire or expunge here - it's already safe from accidental overwrites.

        # Update job with processing options using repository to avoid overwriting encrypted fields
        self.job_repository.update(job.id, processing_options=options)

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
                "target_language": options.get("target_language"),
            }

        except Exception as queue_error:
            logger.error(f"❌ Failed to queue task: {queue_error}")
            raise RuntimeError(
                f"Failed to queue processing task: {str(queue_error)}"
            ) from queue_error

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
        api_status = self._map_status_to_api(job.status, job.progress_percent)

        # Get step description
        current_step = self._get_step_description(job)

        return {
            "processing_id": processing_id,
            "status": api_status,
            "progress_percent": job.progress_percent,
            "current_step": current_step,
            "message": None,
            "error": job.error_message,
        }

    def get_processing_result(self, processing_id: str) -> dict[str, Any]:
        """
        Get processing result for a completed job.

        Builds result dict from individual columns. Medical content columns
        (original_text, translated_text, etc.) are automatically decrypted
        by the repository layer (transparent encryption).

        Args:
            processing_id: Unique processing identifier

        Returns:
            Processing result data dict with all fields

        Raises:
            ValueError: If job not found or not completed
        """
        job = self.job_repository.get_by_processing_id(processing_id)
        if not job:
            raise ValueError(f"Processing job {processing_id} not found")

        if job.status != StepExecutionStatus.COMPLETED:
            raise ValueError(f"Processing not completed yet. Status: {job.status}")

        if not job.translated_text:
            raise ValueError("Processing result not available")

        # Build result dict from individual columns (Issue #55)
        result_data = {
            "processing_id": job.processing_id,
            "original_text": job.original_text or "",
            "translated_text": job.translated_text or "",
            "language_translated_text": job.language_translated_text,
            "ocr_markdown": job.ocr_markdown,
            "document_type_detected": job.document_type_detected,
            "confidence_score": job.confidence_score or 0.0,
            "ocr_confidence": job.ocr_confidence,
            "language_confidence_score": job.language_confidence_score,
            "processing_time_seconds": job.total_execution_time_seconds or 0.0,
            "ocr_time_seconds": job.ocr_time_seconds,
            "ai_processing_time_seconds": job.ai_processing_time_seconds,
            "pipeline_execution_time": job.pipeline_execution_time,
            "total_steps": job.total_steps,
            "target_language": job.target_language,
            "branching_path": job.branching_path,
            "document_class": job.document_class,
            "pipeline_config": job.pipeline_config,
            "terminated": job.terminated or False,
            "termination_reason": job.termination_reason,
            "termination_message": job.termination_message,
            "termination_step": job.termination_step,
            "matched_value": job.matched_value,
        }

        logger.info(
            f"✅ Processing result retrieved for {processing_id}: "
            f"original_text={len(result_data['original_text'])} chars, "
            f"translated_text={len(result_data['translated_text'])} chars"
        )

        return result_data

    def get_active_processes(self) -> dict[str, Any]:
        """
        Get overview of all active processing jobs.

        Returns:
            Dictionary with active process information
        """
        from datetime import datetime

        from app.services.cleanup import processing_store

        active_processes = []

        for proc_id, data in processing_store.items():
            active_processes.append(
                {
                    "processing_id": proc_id[:8] + "...",  # Shortened for privacy
                    "status": data.get("status"),
                    "progress_percent": data.get("progress_percent", 0),
                    "current_step": data.get("current_step"),
                    "created_at": data.get("created_at"),
                    "filename": data.get("filename", "").split("/")[-1]
                    if data.get("filename")
                    else None,
                }
            )

        return {
            "active_count": len(active_processes),
            "processes": active_processes,
            "timestamp": datetime.now(),
        }

    def get_job_by_processing_id(self, processing_id: str):
        """
        Get job record by processing_id.

        Args:
            processing_id: Unique processing identifier

        Returns:
            PipelineJobDB instance or None if not found
        """
        return self.job_repository.get_by_processing_id(processing_id)

    def update_job_guidelines(self, processing_id: str, guidelines_text: str) -> None:
        """
        Store guidelines text in the job record.

        Args:
            processing_id: Unique processing identifier
            guidelines_text: Guidelines text to store (will be encrypted at rest)
        """
        job = self.job_repository.get_by_processing_id(processing_id)
        if job:
            self.job_repository.update(job.id, guidelines_text=guidelines_text)

    def _map_status_to_api(
        self, db_status: StepExecutionStatus, progress: int = 0
    ) -> ProcessingStatus:
        """
        Map database status to API status enum.

        For RUNNING jobs, returns a more specific sub-status based on progress.

        Args:
            db_status: Database status
            progress: Current progress percentage (used for RUNNING sub-statuses)

        Returns:
            API status enum value
        """
        if db_status == StepExecutionStatus.RUNNING:
            if progress < 20:
                return ProcessingStatus.EXTRACTING_TEXT
            if progress < 70:
                return ProcessingStatus.TRANSLATING
            return ProcessingStatus.LANGUAGE_TRANSLATING

        status_mapping = {
            StepExecutionStatus.PENDING: ProcessingStatus.PENDING,
            StepExecutionStatus.COMPLETED: ProcessingStatus.COMPLETED,
            StepExecutionStatus.FAILED: ProcessingStatus.ERROR,
            StepExecutionStatus.SKIPPED: ProcessingStatus.ERROR,
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
            p = job.progress_percent
            if p < 10:
                return "Text wird aus dem Dokument extrahiert (OCR)..."
            if p < 20:
                return "Medizinischer Inhalt wird validiert..."
            if p < 30:
                return "Dokumenttyp wird erkannt..."
            if p < 40:
                return "Datenschutz-Filter wird angewendet..."
            if p < 55:
                return "KI vereinfacht den medizinischen Text..."
            if p < 65:
                return "Medizinische Fakten werden geprüft..."
            if p < 75:
                return "Grammatik und Ausdruck werden optimiert..."
            if p < 85:
                return "Sprachübersetzung wird durchgeführt..."
            if p < 95:
                return "Qualitätsprüfung läuft..."
            return "Formatierung wird abgeschlossen..."
        if job.status == StepExecutionStatus.COMPLETED:
            return "Verarbeitung abgeschlossen"
        if job.status == StepExecutionStatus.FAILED:
            return "Fehler bei Verarbeitung"
        return "Warten auf Verarbeitung..."
