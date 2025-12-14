"""
Feedback Router

Provides endpoints for user feedback submission and admin feedback management.
Part of Issue #47 - User Feedback System with GDPR Data Protection.
"""

import logging
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.permissions import require_admin
from app.database.auth_models import UserDB
from app.database.connection import get_session
from app.services.feedback_service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])
limiter = Limiter(key_func=get_remote_address)


# ==================== ENUMS ====================


class SortBy(str, Enum):
    """Sort options for feedback list"""

    DATE = "submitted_at"
    RATING = "overall_rating"


class SortOrder(str, Enum):
    """Sort order options"""

    ASC = "asc"
    DESC = "desc"


# ==================== REQUEST MODELS ====================


class DetailedRatings(BaseModel):
    """Detailed ratings for specific aspects"""

    clarity: int | None = Field(None, ge=1, le=5, description="Verständlichkeit (1-5)")
    accuracy: int | None = Field(None, ge=1, le=5, description="Genauigkeit (1-5)")
    formatting: int | None = Field(None, ge=1, le=5, description="Formatierung (1-5)")
    speed: int | None = Field(None, ge=1, le=5, description="Geschwindigkeit (1-5)")


class FeedbackSubmission(BaseModel):
    """Request model for submitting feedback"""

    processing_id: str = Field(..., description="Processing job ID")
    overall_rating: int = Field(..., ge=1, le=5, description="Overall rating (1-5)")
    detailed_ratings: DetailedRatings | None = Field(
        None, description="Optional detailed ratings"
    )
    comment: str | None = Field(None, max_length=2000, description="Optional comment")
    data_consent_given: bool = Field(
        ..., description="Whether user consents to data usage for improvement"
    )


# ==================== RESPONSE MODELS ====================


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""

    id: int = Field(..., description="Feedback ID")
    processing_id: str = Field(..., description="Processing job ID")
    overall_rating: int = Field(..., description="Overall rating")
    detailed_ratings: dict | None = Field(None, description="Detailed ratings")
    comment: str | None = Field(None, description="Comment")
    data_consent_given: bool = Field(..., description="Consent status")
    submitted_at: str = Field(..., description="Submission timestamp")


class FeedbackExistsResponse(BaseModel):
    """Response for checking if feedback exists"""

    exists: bool = Field(..., description="Whether feedback exists")
    processing_id: str = Field(..., description="Processing job ID")


class CleanupResponse(BaseModel):
    """Response for content cleanup"""

    status: str = Field(..., description="Cleanup status")
    processing_id: str | None = Field(None, description="Processing job ID")
    reason: str | None = Field(None, description="Reason if skipped")


class FeedbackEntry(BaseModel):
    """Feedback entry in list response"""

    id: int = Field(..., description="Feedback ID")
    processing_id: str = Field(..., description="Processing job ID")
    overall_rating: int = Field(..., description="Overall rating")
    detailed_ratings: dict | None = Field(None, description="Detailed ratings")
    comment: str | None = Field(None, description="Comment")
    data_consent_given: bool = Field(..., description="Consent status")
    submitted_at: str = Field(..., description="Submission timestamp")


class FeedbackListResponse(BaseModel):
    """Response model for feedback list"""

    entries: list[FeedbackEntry] = Field(..., description="List of feedback entries")
    total: int = Field(..., description="Total number of entries")
    skip: int = Field(..., description="Offset")
    limit: int = Field(..., description="Limit")


class DetailedRatingsStats(BaseModel):
    """Statistics for detailed ratings"""

    clarity: float = Field(..., description="Average clarity rating")
    accuracy: float = Field(..., description="Average accuracy rating")
    formatting: float = Field(..., description="Average formatting rating")
    speed: float = Field(..., description="Average speed rating")


class FeedbackStatsResponse(BaseModel):
    """Response model for feedback statistics"""

    total_feedback: int = Field(..., description="Total feedback count")
    average_overall_rating: float = Field(..., description="Average overall rating")
    rating_distribution: dict[str, int] = Field(
        ..., description="Distribution of ratings (1-5)"
    )
    consent_rate: float = Field(..., description="Percentage of users who gave consent")
    with_comments_count: int = Field(..., description="Number with comments")
    average_detailed_ratings: DetailedRatingsStats = Field(
        ..., description="Average detailed ratings"
    )


class JobData(BaseModel):
    """Job data in feedback detail response"""

    filename: str | None = Field(None, description="Original filename")
    file_type: str | None = Field(None, description="File type")
    status: str | None = Field(None, description="Job status")
    completed_at: str | None = Field(None, description="Completion timestamp")
    processing_time_seconds: float | None = Field(None, description="Processing time")
    document_type: str | None = Field(None, description="Document type")
    original_text: str | None = Field(None, description="Original text (if consented)")
    translated_text: str | None = Field(None, description="Translated text (if consented)")
    language_translated_text: str | None = Field(
        None, description="Language translated text"
    )
    content_available: bool | None = Field(None, description="Whether content is available")


class FeedbackDetailResponse(BaseModel):
    """Response model for feedback detail with job data"""

    id: int = Field(..., description="Feedback ID")
    processing_id: str = Field(..., description="Processing job ID")
    overall_rating: int = Field(..., description="Overall rating")
    detailed_ratings: dict | None = Field(None, description="Detailed ratings")
    comment: str | None = Field(None, description="Comment")
    data_consent_given: bool = Field(..., description="Consent status")
    submitted_at: str = Field(..., description="Submission timestamp")
    job_data: JobData | None = Field(None, description="Associated job data")


# ==================== PUBLIC ENDPOINTS ====================


@router.post("", response_model=FeedbackResponse)
@limiter.limit("10/minute")
async def submit_feedback(
    request: Request,
    submission: FeedbackSubmission,
    db: Session = Depends(get_session),
):
    """
    Submit feedback for a translation (public endpoint).

    If consent is given, document content will be preserved.
    If consent is not given, content will be cleared.

    Rate limited to 10 submissions per minute per IP.
    """
    try:
        service = FeedbackService(db)

        # Get client IP
        client_ip = get_remote_address(request)

        # Convert detailed ratings to dict if provided
        detailed_ratings_dict = None
        if submission.detailed_ratings:
            detailed_ratings_dict = submission.detailed_ratings.model_dump(
                exclude_none=True
            )

        result = service.submit_feedback(
            processing_id=submission.processing_id,
            overall_rating=submission.overall_rating,
            data_consent_given=submission.data_consent_given,
            detailed_ratings=detailed_ratings_dict,
            comment=submission.comment,
            client_ip=client_ip,
        )

        return FeedbackResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback",
        ) from e


@router.get("/{processing_id}", response_model=FeedbackExistsResponse)
async def check_feedback_exists(
    processing_id: str,
    db: Session = Depends(get_session),
):
    """
    Check if feedback exists for a processing ID (public endpoint).

    Used by frontend to prevent duplicate submissions.
    """
    try:
        service = FeedbackService(db)
        exists = service.check_feedback_exists(processing_id)

        return FeedbackExistsResponse(exists=exists, processing_id=processing_id)

    except Exception as e:
        logger.error(f"Error checking feedback exists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check feedback status",
        ) from e


@router.post("/cleanup/{processing_id}", response_model=CleanupResponse)
async def cleanup_content(
    processing_id: str,
    db: Session = Depends(get_session),
):
    """
    Clear document content for GDPR compliance (public endpoint).

    Called via sendBeacon when user leaves page without providing feedback.
    If feedback already exists, content is preserved.
    """
    try:
        service = FeedbackService(db)
        result = service.cleanup_content(processing_id)

        return CleanupResponse(**result)

    except Exception as e:
        logger.error(f"Error cleaning up content: {e}")
        # Don't fail for cleanup requests - just log
        return CleanupResponse(status="error", processing_id=processing_id)


# ==================== ADMIN ENDPOINTS ====================


@router.get("/admin/list", response_model=FeedbackListResponse)
async def get_feedback_list(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    rating_filter: int | None = Query(None, ge=1, le=5, description="Filter by rating"),
    consent_filter: bool | None = Query(None, description="Filter by consent status"),
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    sort_by: SortBy = Query(SortBy.DATE, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session),
):
    """
    Get list of feedback entries with filters (admin only).

    Returns paginated list of feedback with sorting and filtering options.
    """
    try:
        service = FeedbackService(db)

        result = service.get_feedback_list(
            skip=skip,
            limit=limit,
            rating_filter=rating_filter,
            consent_filter=consent_filter,
            start_date=start_date,
            end_date=end_date,
            sort_by=sort_by.value,
            sort_order=sort_order.value,
        )

        return FeedbackListResponse(
            entries=[FeedbackEntry(**e) for e in result["entries"]],
            total=result["total"],
            skip=result["skip"],
            limit=result["limit"],
        )

    except Exception as e:
        logger.error(f"Error getting feedback list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback list",
        ) from e


@router.get("/admin/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    start_date: datetime | None = Query(None, description="Start date filter"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session),
):
    """
    Get aggregate feedback statistics (admin only).

    Returns statistics including average rating, distribution, and consent rate.
    """
    try:
        service = FeedbackService(db)
        result = service.get_feedback_statistics(since=start_date)

        return FeedbackStatsResponse(
            total_feedback=result["total_feedback"],
            average_overall_rating=result["average_overall_rating"],
            rating_distribution={str(k): v for k, v in result["rating_distribution"].items()},
            consent_rate=result["consent_rate"],
            with_comments_count=result["with_comments_count"],
            average_detailed_ratings=DetailedRatingsStats(
                clarity=result["average_detailed_ratings"].get("clarity", 0),
                accuracy=result["average_detailed_ratings"].get("accuracy", 0),
                formatting=result["average_detailed_ratings"].get("formatting", 0),
                speed=result["average_detailed_ratings"].get("speed", 0),
            ),
        )

    except Exception as e:
        logger.error(f"Error getting feedback stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback statistics",
        ) from e


@router.get("/admin/{feedback_id}", response_model=FeedbackDetailResponse)
async def get_feedback_detail(
    feedback_id: int,
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session),
):
    """
    Get detailed feedback with associated job data (admin only).

    Document content is only included if user gave consent.
    """
    try:
        service = FeedbackService(db)
        result = service.get_feedback_detail(feedback_id)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Feedback not found",
            )

        # Convert job_data if present
        job_data = None
        if result.get("job_data"):
            job_data = JobData(**result["job_data"])

        return FeedbackDetailResponse(
            id=result["id"],
            processing_id=result["processing_id"],
            overall_rating=result["overall_rating"],
            detailed_ratings=result["detailed_ratings"],
            comment=result["comment"],
            data_consent_given=result["data_consent_given"],
            submitted_at=result["submitted_at"],
            job_data=job_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback detail",
        ) from e


# ==================== HEALTH CHECK ====================


@router.get("/health")
async def feedback_health_check():
    """
    Feedback service health check.

    Returns:
        Service status
    """
    return {"status": "healthy", "service": "feedback", "version": "1.0.0"}
