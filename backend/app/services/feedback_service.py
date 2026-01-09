"""
Feedback Service

Business logic for user feedback system (Issue #47).
Handles feedback submission, retrieval, and GDPR content management.
Includes AI-powered quality analysis for self-improving feedback.
"""

from datetime import datetime
import logging

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import FeedbackAnalysisStatus
from app.repositories.feedback_repository import FeedbackRepository, PipelineJobFeedbackRepository
from app.services.celery_client import enqueue_feedback_analysis
from app.services.feature_flags import Feature, FeatureFlags

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for managing user feedback on translations.

    Handles feedback submission, content retention/cleanup based on consent,
    and admin statistics.
    """

    def __init__(self, db: Session):
        """
        Initialize feedback service.

        Args:
            db: Database session
        """
        self.db = db
        self.feedback_repo = FeedbackRepository(db)
        self.job_feedback_repo = PipelineJobFeedbackRepository(db)

    def submit_feedback(
        self,
        processing_id: str,
        overall_rating: int,
        data_consent_given: bool,
        detailed_ratings: dict | None = None,
        comment: str | None = None,
        client_ip: str | None = None,
    ) -> dict:
        """
        Submit user feedback for a translation.

        If consent is given, content is preserved.
        If consent is not given, content is immediately cleared (GDPR compliance).

        Args:
            processing_id: The processing job ID
            overall_rating: Overall rating (1-5)
            data_consent_given: Whether user consents to data usage
            detailed_ratings: Optional detailed ratings dict
            comment: Optional text comment
            client_ip: Client IP address

        Returns:
            Created feedback entry as dict

        Raises:
            ValueError: If processing_id not found or feedback already exists
        """
        # Check if feedback already exists
        if self.feedback_repo.exists_for_processing_id(processing_id):
            raise ValueError(f"Feedback already submitted for processing_id: {processing_id}")

        # Validate rating
        if not 1 <= overall_rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        # Validate detailed ratings if provided
        if detailed_ratings:
            valid_keys = {"clarity", "accuracy", "formatting", "speed"}
            for key, value in detailed_ratings.items():
                if key not in valid_keys:
                    raise ValueError(f"Invalid detailed rating key: {key}")
                if value is not None and not 1 <= value <= 5:
                    raise ValueError(f"Detailed rating '{key}' must be between 1 and 5")

        # Create feedback entry
        feedback = self.feedback_repo.create(
            processing_id=processing_id,
            overall_rating=overall_rating,
            detailed_ratings=detailed_ratings,
            comment=comment,
            data_consent_given=data_consent_given,
            client_ip=client_ip,
        )

        # Mark job as having feedback
        job = self.job_feedback_repo.mark_feedback_given(
            processing_id=processing_id,
            consent_given=data_consent_given,
        )

        if not job:
            logger.warning(f"Job not found for processing_id: {processing_id}")
        else:
            # If consent was not given, immediately clear content (GDPR compliance)
            if not data_consent_given:
                logger.info(
                    f"Clearing content for {processing_id} - consent not given"
                )
                self.job_feedback_repo.clear_content_for_job(processing_id)
            else:
                # Consent given - trigger AI analysis if feature enabled
                logger.info(f"Consent given for {processing_id}, triggering AI analysis...")
                analysis_triggered = self._trigger_ai_analysis(feedback.id)
                logger.info(f"AI analysis trigger result for feedback {feedback.id}: {analysis_triggered}")

        logger.info(
            f"Feedback submitted for {processing_id}: rating={overall_rating}, consent={data_consent_given}"
        )

        return {
            "id": feedback.id,
            "processing_id": feedback.processing_id,
            "overall_rating": feedback.overall_rating,
            "detailed_ratings": feedback.detailed_ratings,
            "comment": feedback.comment,
            "data_consent_given": feedback.data_consent_given,
            "submitted_at": feedback.submitted_at.isoformat(),
        }

    def check_feedback_exists(self, processing_id: str) -> bool:
        """
        Check if feedback exists for a processing ID.

        Args:
            processing_id: The processing job ID

        Returns:
            True if feedback exists
        """
        return self.feedback_repo.exists_for_processing_id(processing_id)

    def _trigger_ai_analysis(self, feedback_id: int) -> bool:
        """
        Trigger AI quality analysis for a feedback entry.

        Checks if the FEEDBACK_AI_ANALYSIS feature is enabled before
        enqueueing the analysis task. Sets initial status to PENDING.

        Args:
            feedback_id: Feedback entry ID

        Returns:
            True if analysis was enqueued, False if skipped/failed
        """
        try:
            # Check if feature is enabled
            flags = FeatureFlags(session=self.db)
            if not flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS):
                logger.info(
                    f"AI analysis disabled by feature flag, skipping for feedback {feedback_id}"
                )
                return False

            # Set initial status to PENDING
            self.feedback_repo.update_analysis_status(
                feedback_id=feedback_id,
                status=FeedbackAnalysisStatus.PENDING,
            )

            # Enqueue analysis task
            task_id = enqueue_feedback_analysis(feedback_id)
            if task_id:
                logger.info(
                    f"AI analysis enqueued for feedback {feedback_id}: task_id={task_id}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to enqueue AI analysis for feedback {feedback_id}"
                )
                self.feedback_repo.update_analysis_result(
                    feedback_id=feedback_id,
                    status=FeedbackAnalysisStatus.FAILED,
                    error_message="Failed to enqueue analysis task",
                )
                return False

        except Exception as e:
            logger.error(f"Error triggering AI analysis for feedback {feedback_id}: {e}")
            return False

    def cleanup_content(self, processing_id: str) -> dict:
        """
        Clear content for a processing job (called when user leaves without feedback).

        Args:
            processing_id: The processing job ID

        Returns:
            Status dict
        """
        # Check if feedback already exists - don't clear if it does
        if self.feedback_repo.exists_for_processing_id(processing_id):
            logger.info(f"Skipping cleanup for {processing_id} - feedback exists")
            return {"status": "skipped", "reason": "feedback_exists"}

        job = self.job_feedback_repo.clear_content_for_job(processing_id)

        if job:
            logger.info(f"Content cleared for {processing_id}")
            return {"status": "cleared", "processing_id": processing_id}
        logger.warning(f"Job not found for cleanup: {processing_id}")
        return {"status": "not_found", "processing_id": processing_id}

    def get_feedback_list(
        self,
        skip: int = 0,
        limit: int = 50,
        rating_filter: int | None = None,
        consent_filter: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sort_by: str = "submitted_at",
        sort_order: str = "desc",
    ) -> dict:
        """
        Get paginated list of feedback entries (admin).

        Args:
            skip: Pagination offset
            limit: Page size
            rating_filter: Filter by rating
            consent_filter: Filter by consent
            start_date: Filter from date
            end_date: Filter to date
            sort_by: Sort field
            sort_order: Sort direction

        Returns:
            Dict with entries and total count
        """
        entries, total = self.feedback_repo.get_feedback_with_filters(
            skip=skip,
            limit=limit,
            rating_filter=rating_filter,
            consent_filter=consent_filter,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "entries": [self._feedback_to_dict(f) for f in entries],
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    def get_feedback_detail(self, feedback_id: int) -> dict | None:
        """
        Get detailed feedback with associated job data (admin).

        Args:
            feedback_id: Feedback entry ID

        Returns:
            Dict with feedback and job data, or None
        """
        feedback, job = self.job_feedback_repo.get_feedback_with_job_data(feedback_id)

        if not feedback:
            return None

        result = self._feedback_to_detail_dict(feedback)

        # Add job data if available and consented
        if job:
            result["job_data"] = {
                "filename": job.filename,
                "file_type": job.file_type,
                "status": job.status.value if job.status else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "processing_time_seconds": job.total_execution_time_seconds,
                "document_type": (
                    job.result_data.get("document_type_detected") if job.result_data else None
                ),
            }

            # Only include content if consent was given and content not cleared
            if feedback.data_consent_given and job.result_data and not job.content_cleared_at:
                result["job_data"]["original_text"] = job.result_data.get("original_text")
                result["job_data"]["translated_text"] = job.result_data.get("translated_text")
                result["job_data"]["language_translated_text"] = job.result_data.get(
                    "language_translated_text"
                )
                result["job_data"]["content_available"] = True
            else:
                result["job_data"]["content_available"] = False

        return result

    def get_feedback_statistics(self, since: datetime | None = None) -> dict:
        """
        Get aggregate feedback statistics (admin).

        Args:
            since: Only include feedback after this date

        Returns:
            Statistics dict
        """
        return self.feedback_repo.get_feedback_statistics(since)

    def cleanup_orphaned_content(self, older_than_hours: int = 1) -> int:
        """
        Clean up content from jobs without feedback (safety net task).

        Args:
            older_than_hours: Minimum age of jobs to clean

        Returns:
            Number of jobs cleaned
        """
        jobs = self.job_feedback_repo.get_jobs_without_feedback(older_than_hours)

        count = 0
        for job in jobs:
            self.job_feedback_repo.clear_content_for_job(job.processing_id)
            count += 1

        if count > 0:
            logger.info(f"Cleaned content from {count} orphaned jobs")

        return count

    def _feedback_to_dict(self, feedback) -> dict:
        """Convert feedback model to dict."""
        result = {
            "id": feedback.id,
            "processing_id": feedback.processing_id,
            "overall_rating": feedback.overall_rating,
            "detailed_ratings": feedback.detailed_ratings,
            "comment": feedback.comment,
            "data_consent_given": feedback.data_consent_given,
            "submitted_at": feedback.submitted_at.isoformat(),
            # AI analysis fields
            "ai_analysis_status": (
                feedback.ai_analysis_status.value
                if feedback.ai_analysis_status
                else None
            ),
            "ai_analysis_quality_score": (
                feedback.ai_analysis_summary.get("overall_quality_score")
                if feedback.ai_analysis_summary
                else None
            ),
        }
        return result

    def _feedback_to_detail_dict(self, feedback) -> dict:
        """Convert feedback model to detailed dict with all AI analysis fields."""
        result = self._feedback_to_dict(feedback)
        # Add full AI analysis fields for detail view
        result["ai_analysis_text"] = feedback.ai_analysis_text
        result["ai_analysis_summary"] = feedback.ai_analysis_summary
        result["ai_analysis_completed_at"] = (
            feedback.ai_analysis_completed_at.isoformat()
            if feedback.ai_analysis_completed_at
            else None
        )
        result["ai_analysis_error"] = feedback.ai_analysis_error
        return result
