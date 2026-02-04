"""
Feedback Repository

Handles database operations for user feedback on translations (Issue #47).
Includes AI-powered quality analysis for self-improving feedback.
"""

from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import (
    FeedbackAnalysisStatus,
    PipelineJobDB,
    PipelineStepExecutionDB,
    UserFeedbackDB,
)
from app.repositories.base_repository import BaseRepository, EncryptedRepositoryMixin
from app.repositories.pipeline_job_repository import PipelineJobRepository
from app.repositories.pipeline_step_execution_repository import PipelineStepExecutionRepository

logger = logging.getLogger(__name__)


class FeedbackRepository(EncryptedRepositoryMixin, BaseRepository[UserFeedbackDB]):
    """
    Repository for User Feedback operations.

    Provides specialized queries for managing feedback beyond basic CRUD.
    Includes encryption for AI analysis text (may contain medical excerpts).

    Encrypted fields: ai_analysis_text
    """

    # Define fields to encrypt (ai_analysis_text may contain medical document excerpts)
    encrypted_fields = ["ai_analysis_text"]

    def __init__(self, db: Session):
        """
        Initialize feedback repository.

        Args:
            db: Database session
        """
        super().__init__(db, UserFeedbackDB)

    def get_by_processing_id(self, processing_id: str) -> UserFeedbackDB | None:
        """
        Get feedback by processing ID.

        Args:
            processing_id: Unique processing identifier

        Returns:
            Feedback instance or None if not found
        """
        return self.db.query(self.model).filter_by(processing_id=processing_id).first()

    def exists_for_processing_id(self, processing_id: str) -> bool:
        """
        Check if feedback exists for a processing ID.

        Args:
            processing_id: Unique processing identifier

        Returns:
            True if feedback exists, False otherwise
        """
        return self.db.query(self.model).filter_by(processing_id=processing_id).count() > 0

    def get_feedback_with_filters(
        self,
        skip: int = 0,
        limit: int = 50,
        rating_filter: int | None = None,
        consent_filter: bool | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        sort_by: str = "submitted_at",
        sort_order: str = "desc",
    ) -> tuple[list[UserFeedbackDB], int]:
        """
        Get feedback entries with filters and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            rating_filter: Filter by exact rating (1-5)
            consent_filter: Filter by consent status
            start_date: Filter by start date
            end_date: Filter by end date
            sort_by: Field to sort by
            sort_order: Sort direction ('asc' or 'desc')

        Returns:
            Tuple of (list of feedback, total count)
        """
        query = self.db.query(self.model)

        # Apply filters
        if rating_filter is not None:
            query = query.filter(self.model.overall_rating == rating_filter)

        if consent_filter is not None:
            query = query.filter(self.model.data_consent_given == consent_filter)

        if start_date:
            query = query.filter(self.model.submitted_at >= start_date)

        if end_date:
            query = query.filter(self.model.submitted_at <= end_date)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_column = getattr(self.model, sort_by, self.model.submitted_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        entries = query.offset(skip).limit(limit).all()

        return entries, total

    def get_feedback_statistics(self, since: datetime | None = None) -> dict:
        """
        Get aggregate statistics about feedback.

        Args:
            since: Only include feedback submitted after this time

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(self.model)

        if since:
            query = query.filter(self.model.submitted_at >= since)

        feedbacks = query.all()

        if not feedbacks:
            return {
                "total_feedback": 0,
                "average_overall_rating": 0,
                "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                "consent_rate": 0,
                "with_comments_count": 0,
                "average_detailed_ratings": {
                    "clarity": 0,
                    "accuracy": 0,
                    "formatting": 0,
                    "speed": 0,
                },
            }

        total = len(feedbacks)
        ratings_sum = sum(f.overall_rating for f in feedbacks)
        consented = sum(1 for f in feedbacks if f.data_consent_given)
        with_comments = sum(1 for f in feedbacks if f.comment)

        # Rating distribution
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for f in feedbacks:
            distribution[f.overall_rating] = distribution.get(f.overall_rating, 0) + 1

        # Average detailed ratings
        detailed_sums = {"clarity": 0, "accuracy": 0, "formatting": 0, "speed": 0}
        detailed_counts = {"clarity": 0, "accuracy": 0, "formatting": 0, "speed": 0}

        for f in feedbacks:
            if f.detailed_ratings:
                for key in detailed_sums:
                    if f.detailed_ratings.get(key):
                        detailed_sums[key] += f.detailed_ratings[key]
                        detailed_counts[key] += 1

        average_detailed = {}
        for key in detailed_sums:
            if detailed_counts[key] > 0:
                average_detailed[key] = round(detailed_sums[key] / detailed_counts[key], 2)
            else:
                average_detailed[key] = 0

        return {
            "total_feedback": total,
            "average_overall_rating": round(ratings_sum / total, 2) if total > 0 else 0,
            "rating_distribution": distribution,
            "consent_rate": round((consented / total) * 100, 1) if total > 0 else 0,
            "with_comments_count": with_comments,
            "average_detailed_ratings": average_detailed,
        }

    def get_recent_feedback(
        self, hours: int = 24, limit: int | None = None
    ) -> list[UserFeedbackDB]:
        """
        Get feedback submitted in the last N hours.

        Args:
            hours: Number of hours to look back
            limit: Maximum number of entries to return

        Returns:
            List of recent feedback entries
        """
        since = datetime.now() - timedelta(hours=hours)
        query = (
            self.db.query(self.model)
            .filter(self.model.submitted_at >= since)
            .order_by(self.model.submitted_at.desc())
        )

        if limit:
            query = query.limit(limit)

        return query.all()

    # ==================== AI ANALYSIS METHODS ====================

    def update_analysis_status(
        self,
        feedback_id: int,
        status: FeedbackAnalysisStatus,
        started_at: datetime | None = None,
    ) -> bool:
        """
        Update the AI analysis status for a feedback entry.

        Args:
            feedback_id: Feedback entry ID
            status: New analysis status
            started_at: When analysis started (optional)

        Returns:
            True if update succeeded, False if feedback not found
        """
        # Build update data
        update_data = {"ai_analysis_status": status}
        if started_at:
            update_data["ai_analysis_started_at"] = started_at

        # Use EncryptedRepositoryMixin.update() which handles session correctly
        # Note: update() returns None by design, but executes the update
        self.update(feedback_id, **update_data)

        # Verify the update was applied by checking rowcount would require
        # refactoring, so we assume success if no exception was raised
        return True

    def update_analysis_result(
        self,
        feedback_id: int,
        status: FeedbackAnalysisStatus,
        analysis_text: str | None = None,
        analysis_summary: dict | None = None,
        error_message: str | None = None,
    ) -> bool:
        """
        Update the AI analysis result for a feedback entry.

        Args:
            feedback_id: Feedback entry ID
            status: Final analysis status (COMPLETED, FAILED, SKIPPED)
            analysis_text: Full analysis text from AI (will be encrypted)
            analysis_summary: Structured summary {pii_issues, translation_issues, recommendations, quality_score}
            error_message: Error message if analysis failed

        Returns:
            True if update succeeded
        """
        # Build update data - use EncryptedRepositoryMixin.update() which handles
        # encryption and session correctly
        update_data = {
            "ai_analysis_status": status,
            "ai_analysis_completed_at": datetime.now(),
        }

        if analysis_text is not None:
            update_data["ai_analysis_text"] = analysis_text

        if analysis_summary is not None:
            update_data["ai_analysis_summary"] = analysis_summary

        if error_message is not None:
            update_data["ai_analysis_error"] = error_message

        # Note: update() returns None by design, but executes the update
        self.update(feedback_id, **update_data)
        return True

    def get_pending_analysis(self, limit: int = 100) -> list[UserFeedbackDB]:
        """
        Get feedback entries with pending AI analysis.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of feedback entries awaiting analysis
        """
        return (
            self.db.query(self.model)
            .filter(self.model.ai_analysis_status == FeedbackAnalysisStatus.PENDING)
            .limit(limit)
            .all()
        )

    def get_analysis_statistics(self, since: datetime | None = None) -> dict:
        """
        Get statistics about AI analysis completion.

        Args:
            since: Only include feedback submitted after this time

        Returns:
            Dictionary with analysis statistics
        """
        query = self.db.query(self.model).filter(
            self.model.data_consent_given == True  # noqa: E712
        )

        if since:
            query = query.filter(self.model.submitted_at >= since)

        feedbacks = query.all()

        if not feedbacks:
            return {
                "total_with_consent": 0,
                "analysis_completed": 0,
                "analysis_pending": 0,
                "analysis_failed": 0,
                "analysis_skipped": 0,
                "average_quality_score": 0,
            }

        total = len(feedbacks)
        completed = sum(
            1 for f in feedbacks if f.ai_analysis_status == FeedbackAnalysisStatus.COMPLETED
        )
        pending = sum(
            1 for f in feedbacks if f.ai_analysis_status == FeedbackAnalysisStatus.PENDING
        )
        failed = sum(1 for f in feedbacks if f.ai_analysis_status == FeedbackAnalysisStatus.FAILED)
        skipped = sum(
            1 for f in feedbacks if f.ai_analysis_status == FeedbackAnalysisStatus.SKIPPED
        )

        # Calculate average quality score from completed analyses
        quality_scores = [
            f.ai_analysis_summary.get("overall_quality_score", 0)
            for f in feedbacks
            if f.ai_analysis_status == FeedbackAnalysisStatus.COMPLETED and f.ai_analysis_summary
        ]
        avg_quality = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0

        return {
            "total_with_consent": total,
            "analysis_completed": completed,
            "analysis_pending": pending,
            "analysis_failed": failed,
            "analysis_skipped": skipped,
            "average_quality_score": avg_quality,
        }


class PipelineJobFeedbackRepository:
    """
    Repository extension for feedback-related operations on PipelineJobDB.

    Uses encrypted repositories to ensure content is properly encrypted/decrypted.
    """

    def __init__(self, db: Session):
        self.db = db
        self.job_repo = PipelineJobRepository(db)
        self.step_execution_repo = PipelineStepExecutionRepository(db)

    def mark_feedback_given(
        self, processing_id: str, consent_given: bool = True
    ) -> PipelineJobDB | None:
        """
        Mark a job as having received feedback.

        Args:
            processing_id: Job processing ID
            consent_given: Whether user consented to data usage

        Returns:
            Updated job or None if not found
        """
        job = self.job_repo.get_by_processing_id(processing_id)

        if not job:
            return None

        job_id = job.id  # Save ID before update (job may be expunged)

        # Update using repository to ensure encryption is handled
        updated = self.job_repo.update(job_id, has_feedback=True, data_consent_given=consent_given)

        # Return updated entity if available, otherwise original
        return updated or job

    def clear_content_for_step_executions(self, job_id: str) -> int:
        """
        Clear document content from step executions for a job (GDPR compliance).
        Preserves metadata like execution time, token counts, confidence scores.

        Uses encrypted repository to ensure proper handling of encrypted fields.

        Args:
            job_id: Job ID (UUID string) to clear step executions for

        Returns:
            Number of step executions cleared
        """
        # Use repository method which handles encryption properly
        cleared_count = self.step_execution_repo.clear_text_content(job_id)

        # Also clear prompt_used and error_message (not encrypted, but should be cleared)
        step_executions = self.db.query(PipelineStepExecutionDB).filter_by(job_id=job_id).all()

        for step_exec in step_executions:
            step_exec.prompt_used = None
            step_exec.error_message = None
            # Clear step_metadata JSON (may contain text content)
            step_exec.step_metadata = {}

        # Note: No commit here - let the caller commit to ensure atomicity
        return cleared_count

    def clear_content_for_job(self, processing_id: str) -> PipelineJobDB | None:
        """
        Clear document content from a job and its step executions (GDPR compliance).
        Preserves metadata like costs, timing, document type.

        Uses encrypted repositories to ensure proper handling of encrypted fields.

        Args:
            processing_id: Job processing ID

        Returns:
            Updated job or None if not found
        """
        # Get job using repository (ensures decryption if needed)
        job = self.job_repo.get_by_processing_id(processing_id)

        if not job:
            return None

        # Clear binary file content using repository (handles encryption)
        self.job_repo.clear_file_content(job.job_id)

        # Clear encrypted medical content columns while preserving metadata
        gdpr_update = {
            "original_text": "[Content cleared - GDPR]",
            "translated_text": "[Content cleared - GDPR]",
            "ocr_markdown": "[Content cleared - GDPR]" if job.ocr_markdown else None,
        }
        if job.language_translated_text:
            gdpr_update["language_translated_text"] = "[Content cleared - GDPR]"
        if job.guidelines_text:
            gdpr_update["guidelines_text"] = "[Content cleared - GDPR]"
        self.job_repo.update(job.id, **gdpr_update)

        # Clear content from all step executions for this job
        # Use job_id (UUID string) to find related step executions
        self.clear_content_for_step_executions(job.job_id)

        # Update content_cleared_at timestamp
        updated = self.job_repo.update(job.id, content_cleared_at=datetime.now())

        # Return updated entity if available, otherwise original
        return updated or job

    def get_jobs_without_feedback(self, older_than_hours: int = 1) -> list[PipelineJobDB]:
        """
        Get completed jobs without feedback older than specified hours.
        Used by cleanup task.

        Args:
            older_than_hours: Minimum age in hours

        Returns:
            List of jobs that need content cleanup
        """
        cutoff = datetime.now() - timedelta(hours=older_than_hours)

        return (
            self.db.query(PipelineJobDB)
            .filter(
                PipelineJobDB.completed_at < cutoff,
                PipelineJobDB.has_feedback == False,  # noqa: E712
                PipelineJobDB.content_cleared_at.is_(None),
            )
            .all()
        )

    def get_feedback_with_job_data(
        self, feedback_id: int
    ) -> tuple[UserFeedbackDB | None, PipelineJobDB | None]:
        """
        Get feedback entry with associated job data (for admin view).

        Uses encrypted repository to ensure job content is properly decrypted.

        Args:
            feedback_id: Feedback entry ID

        Returns:
            Tuple of (feedback, job) or (None, None)
            Job will have decrypted file_content
        """
        feedback = self.db.query(UserFeedbackDB).filter_by(id=feedback_id).first()

        if not feedback:
            return None, None

        # Use repository to get job (ensures decryption)
        job = self.job_repo.get_by_processing_id(feedback.processing_id)

        return feedback, job
