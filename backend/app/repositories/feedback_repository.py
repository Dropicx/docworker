"""
Feedback Repository

Handles database operations for user feedback on translations (Issue #47).
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import PipelineJobDB, UserFeedbackDB
from app.repositories.base_repository import BaseRepository


class FeedbackRepository(BaseRepository[UserFeedbackDB]):
    """
    Repository for User Feedback operations.

    Provides specialized queries for managing feedback beyond basic CRUD.
    """

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
        return (
            self.db.query(self.model).filter_by(processing_id=processing_id).count() > 0
        )

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


class PipelineJobFeedbackRepository:
    """
    Repository extension for feedback-related operations on PipelineJobDB.
    """

    def __init__(self, db: Session):
        self.db = db

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
        job = (
            self.db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()
        )

        if not job:
            return None

        job.has_feedback = True
        job.data_consent_given = consent_given

        self.db.commit()
        self.db.refresh(job)
        return job

    def clear_content_for_job(self, processing_id: str) -> PipelineJobDB | None:
        """
        Clear document content from a job (GDPR compliance).
        Preserves metadata like costs, timing, document type.

        Args:
            processing_id: Job processing ID

        Returns:
            Updated job or None if not found
        """
        job = (
            self.db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()
        )

        if not job:
            return None

        # Clear binary file content
        job.file_content = None

        # Clear text content from result_data while preserving metadata
        if job.result_data:
            result_data = job.result_data.copy()
            # Clear text fields
            result_data["original_text"] = "[Content cleared - GDPR]"
            result_data["translated_text"] = "[Content cleared - GDPR]"
            if "language_translated_text" in result_data:
                result_data["language_translated_text"] = "[Content cleared - GDPR]"
            job.result_data = result_data

        job.content_cleared_at = datetime.now()

        self.db.commit()
        self.db.refresh(job)
        return job

    def get_jobs_without_feedback(
        self, older_than_hours: int = 1
    ) -> list[PipelineJobDB]:
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

        Args:
            feedback_id: Feedback entry ID

        Returns:
            Tuple of (feedback, job) or (None, None)
        """
        feedback = (
            self.db.query(UserFeedbackDB).filter_by(id=feedback_id).first()
        )

        if not feedback:
            return None, None

        job = (
            self.db.query(PipelineJobDB)
            .filter_by(processing_id=feedback.processing_id)
            .first()
        )

        return feedback, job
