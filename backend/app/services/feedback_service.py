"""
Feedback Service

Business logic for user feedback system (Issue #47).
Handles feedback submission, retrieval, and GDPR content management.
"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.feedback_repository import (
    FeedbackRepository,
    PipelineJobFeedbackRepository,
)

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
        If consent is not given, content will be cleared by cleanup task.

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
        else:
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

        result = self._feedback_to_dict(feedback)

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
        return {
            "id": feedback.id,
            "processing_id": feedback.processing_id,
            "overall_rating": feedback.overall_rating,
            "detailed_ratings": feedback.detailed_ratings,
            "comment": feedback.comment,
            "data_consent_given": feedback.data_consent_given,
            "submitted_at": feedback.submitted_at.isoformat(),
        }
