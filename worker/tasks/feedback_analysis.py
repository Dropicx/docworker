"""
Feedback AI Analysis Task

Celery task for AI-powered quality analysis of user feedback.
Runs in the background when users submit feedback with consent.
"""

import asyncio
import logging
import os
import sys

# Add paths for imports
sys.path.insert(0, '/app/backend')
sys.path.insert(0, '/app/shared')

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from worker.tasks.base import BaseDocumentTask

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=BaseDocumentTask,
    name='analyze_feedback_quality',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,  # 5 minutes max backoff
    soft_time_limit=120,  # 2 minutes soft limit
    time_limit=180,  # 3 minutes hard limit
)
def analyze_feedback_quality(self, feedback_id: int) -> dict:
    """
    Analyze feedback quality using Mistral Large AI.

    This task:
    1. Fetches the feedback entry and associated processing data
    2. Retrieves OCR text, PII-anonymized text, and final translation
    3. Sends to Mistral Large for quality analysis
    4. Stores the analysis results in the feedback record

    Args:
        feedback_id: ID of the feedback entry to analyze

    Returns:
        dict with analysis status and summary
    """
    logger.info(f"Starting feedback analysis task for feedback_id={feedback_id}")

    try:
        # Import here to avoid circular imports and ensure fresh DB session
        from app.database.connection import get_db_session_context
        from app.services.feedback_analysis_service import FeedbackAnalysisService
        from app.services.feature_flags import FeatureFlags, Feature

        # Get database session
        with get_db_session_context() as db:
            # Check if feature is enabled
            flags = FeatureFlags(session=db)
            if not flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS):
                logger.info("Feedback AI analysis feature is disabled, skipping")
                return {"status": "skipped", "message": "Feature disabled"}

            # Create analysis service
            analysis_service = FeedbackAnalysisService(db)

            # Run async analysis in sync context
            result = asyncio.run(analysis_service.analyze_feedback(feedback_id))

            logger.info(f"Feedback analysis completed for feedback_id={feedback_id}: {result}")
            return result

    except Exception as e:
        logger.error(f"Feedback analysis failed for feedback_id={feedback_id}: {e}")

        # Try to mark as failed in database
        try:
            from app.database.connection import get_db_session_context
            from app.database.modular_pipeline_models import FeedbackAnalysisStatus
            from app.repositories.feedback_repository import FeedbackRepository

            with get_db_session_context() as db:
                repo = FeedbackRepository(db)
                repo.update_analysis_result(
                    feedback_id=feedback_id,
                    status=FeedbackAnalysisStatus.FAILED,
                    error_message=str(e),
                )
        except Exception as db_error:
            logger.error(f"Failed to update analysis status: {db_error}")

        # Re-raise to trigger retry if applicable
        raise


@shared_task(
    name='retry_failed_analyses',
    soft_time_limit=300,
    time_limit=360,
)
def retry_failed_analyses(max_age_hours: int = 24, limit: int = 50) -> dict:
    """
    Retry failed feedback analyses (scheduled task).

    Can be run periodically to retry analyses that failed due to
    transient errors (API timeouts, etc.).

    Args:
        max_age_hours: Only retry analyses that failed within this many hours
        limit: Maximum number of analyses to retry

    Returns:
        dict with retry statistics
    """
    logger.info(f"Retrying failed analyses (max_age={max_age_hours}h, limit={limit})")

    try:
        from datetime import datetime, timedelta
        from app.database.connection import get_db_session_context
        from app.database.modular_pipeline_models import FeedbackAnalysisStatus, UserFeedbackDB
        from app.services.feature_flags import FeatureFlags, Feature

        with get_db_session_context() as db:
            # Check if feature is enabled
            flags = FeatureFlags(session=db)
            if not flags.is_enabled(Feature.FEEDBACK_AI_ANALYSIS):
                return {"status": "skipped", "message": "Feature disabled"}

            # Find failed analyses within time window
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            failed = (
                db.query(UserFeedbackDB)
                .filter(
                    UserFeedbackDB.ai_analysis_status == FeedbackAnalysisStatus.FAILED,
                    UserFeedbackDB.ai_analysis_completed_at >= cutoff,
                    UserFeedbackDB.data_consent_given == True,  # noqa: E712
                )
                .limit(limit)
                .all()
            )

            retried = 0
            for feedback in failed:
                # Reset status to pending
                feedback.ai_analysis_status = FeedbackAnalysisStatus.PENDING
                feedback.ai_analysis_error = None
                db.commit()

                # Enqueue for re-analysis
                analyze_feedback_quality.delay(feedback.id)
                retried += 1

            logger.info(f"Queued {retried} failed analyses for retry")
            return {"status": "success", "retried_count": retried}

    except Exception as e:
        logger.error(f"Failed to retry analyses: {e}")
        return {"status": "error", "message": str(e)}
