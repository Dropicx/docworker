"""
Cost Statistics Router

Provides admin endpoints for viewing AI cost statistics, including
cost overview, breakdowns by model/step, and per-processing-job details.
"""

from datetime import datetime
from enum import Enum
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_ai_cost_tracker, get_ai_log_interaction_repository
from app.core.permissions import require_admin
from app.database.auth_models import UserDB
from app.database.connection import get_session
from app.database.unified_models import AILogInteractionDB
from app.repositories.ai_log_interaction_repository import AILogInteractionRepository
from app.services.ai_cost_tracker import AICostTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/costs", tags=["cost-statistics"])


# ==================== ENUMS ====================


class SortBy(str, Enum):
    """Sort options for processing jobs"""

    COST = "cost"
    DATE = "date"
    TOKENS = "tokens"


class SortOrder(str, Enum):
    """Sort order options"""

    ASC = "asc"
    DESC = "desc"


# ==================== RESPONSE MODELS ====================


class CostOverviewResponse(BaseModel):
    """Cost overview statistics"""

    total_cost_usd: float = Field(..., description="Total cost in USD")
    total_tokens: int = Field(..., description="Total tokens used")
    total_calls: int = Field(..., description="Total API calls")
    average_cost_per_call: float = Field(..., description="Average cost per API call")
    average_tokens_per_call: float = Field(..., description="Average tokens per call")
    # Document-level statistics
    document_count: int = Field(0, description="Number of unique documents processed")
    average_cost_per_document: float = Field(0, description="Average total cost per document")
    min_cost_per_document: float = Field(0, description="Lowest document cost")
    max_cost_per_document: float = Field(0, description="Highest document cost")


class ModelCostBreakdown(BaseModel):
    """Cost breakdown for a single model"""

    calls: int = Field(..., description="Number of API calls")
    tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Total cost in USD")
    provider: str | None = Field(None, description="Model provider")


class StepCostBreakdown(BaseModel):
    """Cost breakdown for a single pipeline step"""

    calls: int = Field(..., description="Number of API calls")
    tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Total cost in USD")


class CostBreakdownResponse(BaseModel):
    """Cost breakdown by model and pipeline step"""

    by_model: dict[str, ModelCostBreakdown] = Field(..., description="Cost breakdown per model")
    by_step: dict[str, StepCostBreakdown] = Field(
        ..., description="Cost breakdown per pipeline step"
    )


class ProcessingJobCost(BaseModel):
    """Cost summary for a processing job"""

    processing_id: str = Field(..., description="Processing job ID")
    total_cost_usd: float = Field(..., description="Total cost for this job")
    total_tokens: int = Field(..., description="Total tokens used")
    call_count: int = Field(..., description="Number of API calls")
    document_type: str | None = Field(None, description="Document type processed")
    models_used: list[str] = Field(..., description="List of models used")
    created_at: str = Field(..., description="First log entry timestamp")


class ProcessingJobsResponse(BaseModel):
    """List of processing jobs with costs"""

    jobs: list[ProcessingJobCost] = Field(..., description="List of processing jobs")
    total: int = Field(..., description="Total number of jobs")


class CostLogEntry(BaseModel):
    """Individual cost log entry"""

    id: int = Field(..., description="Log entry ID")
    step_name: str = Field(..., description="Pipeline step name")
    input_tokens: int = Field(..., description="Input tokens")
    output_tokens: int = Field(..., description="Output tokens")
    total_tokens: int = Field(..., description="Total tokens")
    total_cost_usd: float = Field(..., description="Cost in USD")
    model_name: str | None = Field(None, description="Model name")
    processing_time_seconds: float | None = Field(None, description="Processing time")
    created_at: str = Field(..., description="Timestamp")


class ProcessingJobDetailResponse(BaseModel):
    """Detailed cost information for a processing job"""

    processing_id: str = Field(..., description="Processing job ID")
    entries: list[CostLogEntry] = Field(..., description="All log entries")
    summary: CostOverviewResponse = Field(..., description="Cost summary")


class FeedbackAnalysisCostResponse(BaseModel):
    """Cost statistics specifically for feedback AI analysis"""

    total_cost_usd: float = Field(..., description="Total cost for feedback analysis")
    total_tokens: int = Field(..., description="Total tokens used")
    total_calls: int = Field(..., description="Number of feedback analyses")
    average_cost_per_analysis: float = Field(..., description="Average cost per analysis")


# ==================== ENDPOINTS ====================


@router.get("/overview", response_model=CostOverviewResponse)
async def get_cost_overview(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    tracker: AICostTracker = Depends(get_ai_cost_tracker),
    repository: AILogInteractionRepository = Depends(get_ai_log_interaction_repository),
):
    """
    Get cost overview statistics (admin only).

    Returns total cost, tokens, calls, averages, and per-document statistics.
    """
    try:
        result = tracker.get_total_cost(start_date=start_date, end_date=end_date)

        # Get document-level statistics
        doc_stats = repository.get_average_cost_per_document(
            start_date=start_date, end_date=end_date
        )

        return CostOverviewResponse(
            total_cost_usd=result.get("total_cost_usd", 0),
            total_tokens=result.get("total_tokens", 0),
            total_calls=result.get("total_calls", 0),
            average_cost_per_call=result.get("average_cost_per_call", 0),
            average_tokens_per_call=result.get("average_tokens_per_call", 0),
            # Document-level statistics
            document_count=doc_stats.get("document_count", 0),
            average_cost_per_document=doc_stats.get("average_cost_per_document", 0),
            min_cost_per_document=doc_stats.get("min_cost_per_document", 0),
            max_cost_per_document=doc_stats.get("max_cost_per_document", 0),
        )

    except Exception as e:
        logger.error(f"Error getting cost overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cost overview",
        ) from e


@router.get("/breakdown", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    tracker: AICostTracker = Depends(get_ai_cost_tracker),
):
    """
    Get cost breakdown by model and pipeline step (admin only).

    Returns detailed cost analysis grouped by model and pipeline step.
    """
    try:
        result = tracker.get_cost_breakdown(start_date=start_date, end_date=end_date)

        by_model = {
            model_name: ModelCostBreakdown(
                calls=data.get("calls", 0),
                tokens=data.get("tokens", 0),
                cost_usd=data.get("cost_usd", 0),
                provider=data.get("provider"),
            )
            for model_name, data in result.get("by_model", {}).items()
        }

        by_step = {
            step_name: StepCostBreakdown(
                calls=data.get("calls", 0),
                tokens=data.get("tokens", 0),
                cost_usd=data.get("cost_usd", 0),
            )
            for step_name, data in result.get("by_step", {}).items()
        }

        return CostBreakdownResponse(by_model=by_model, by_step=by_step)

    except Exception as e:
        logger.error(f"Error getting cost breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cost breakdown",
        ) from e


@router.get("/processing-jobs", response_model=ProcessingJobsResponse)
async def get_processing_jobs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum records to return"),
    sort_by: SortBy = Query(SortBy.DATE, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort order"),
    search: str | None = Query(None, description="Search by processing_id"),
    current_user: UserDB = Depends(require_admin()),
    db: Session = Depends(get_session),
):
    """
    Get list of processing jobs with aggregated costs (admin only).

    Returns paginated list of processing jobs with cost summaries.
    """
    try:
        # Build aggregation query
        query = (
            db.query(
                AILogInteractionDB.processing_id,
                func.sum(AILogInteractionDB.total_cost_usd).label("total_cost"),
                func.sum(AILogInteractionDB.total_tokens).label("total_tokens"),
                func.count(AILogInteractionDB.id).label("call_count"),
                func.min(AILogInteractionDB.created_at).label("created_at"),
                func.max(AILogInteractionDB.document_type).label("document_type"),
            )
            .filter(AILogInteractionDB.processing_id.isnot(None))
            .group_by(AILogInteractionDB.processing_id)
        )

        # Apply search filter
        if search:
            query = query.filter(AILogInteractionDB.processing_id.ilike(f"%{search}%"))

        # Apply sorting
        if sort_by == SortBy.COST:
            order_col = func.sum(AILogInteractionDB.total_cost_usd)
        elif sort_by == SortBy.TOKENS:
            order_col = func.sum(AILogInteractionDB.total_tokens)
        else:  # DATE
            order_col = func.min(AILogInteractionDB.created_at)

        if sort_order == SortOrder.DESC:
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())

        # Get total count
        total = query.count()

        # Apply pagination
        results = query.offset(skip).limit(limit).all()

        # Build response
        jobs = []
        for row in results:
            # Get models used for this processing_id
            models = (
                db.query(AILogInteractionDB.model_name)
                .filter(AILogInteractionDB.processing_id == row.processing_id)
                .filter(AILogInteractionDB.model_name.isnot(None))
                .distinct()
                .all()
            )
            models_used = [m[0] for m in models if m[0]]

            jobs.append(
                ProcessingJobCost(
                    processing_id=row.processing_id,
                    total_cost_usd=round(row.total_cost or 0, 6),
                    total_tokens=row.total_tokens or 0,
                    call_count=row.call_count,
                    document_type=row.document_type,
                    models_used=models_used,
                    created_at=row.created_at.isoformat() if row.created_at else "",
                )
            )

        return ProcessingJobsResponse(jobs=jobs, total=total)

    except Exception as e:
        logger.error(f"Error getting processing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get processing jobs",
        ) from e


@router.get("/processing-jobs/{processing_id}", response_model=ProcessingJobDetailResponse)
async def get_processing_job_detail(
    processing_id: str,
    current_user: UserDB = Depends(require_admin()),
    repository: AILogInteractionRepository = Depends(get_ai_log_interaction_repository),
):
    """
    Get detailed cost breakdown for a specific processing job (admin only).

    Returns all log entries and summary for the processing job.
    """
    try:
        logs = repository.get_by_processing_id(processing_id)

        if not logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Processing job not found",
            )

        # Build entries list
        entries = [
            CostLogEntry(
                id=log.id,
                step_name=log.step_name,
                input_tokens=log.input_tokens or 0,
                output_tokens=log.output_tokens or 0,
                total_tokens=log.total_tokens or 0,
                total_cost_usd=round(log.total_cost_usd or 0, 6),
                model_name=log.model_name,
                processing_time_seconds=log.processing_time_seconds,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ]

        # Calculate summary
        total_cost = sum(log.total_cost_usd or 0 for log in logs)
        total_tokens = sum(log.total_tokens or 0 for log in logs)
        total_calls = len(logs)

        summary = CostOverviewResponse(
            total_cost_usd=round(total_cost, 6),
            total_tokens=total_tokens,
            total_calls=total_calls,
            average_cost_per_call=round(total_cost / total_calls, 6) if total_calls > 0 else 0,
            average_tokens_per_call=round(total_tokens / total_calls, 0) if total_calls > 0 else 0,
        )

        return ProcessingJobDetailResponse(
            processing_id=processing_id,
            entries=entries,
            summary=summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing job detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get processing job detail",
        ) from e


# ==================== FEEDBACK ANALYSIS COSTS ====================


@router.get("/feedback-analysis", response_model=FeedbackAnalysisCostResponse)
async def get_feedback_analysis_costs(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    repository: AILogInteractionRepository = Depends(get_ai_log_interaction_repository),
):
    """
    Get cost statistics specifically for feedback AI analysis (admin only).

    Returns costs for the self-improving feedback feature using Mistral Large.
    """
    try:
        stats = repository.get_feedback_analysis_stats(start_date=start_date, end_date=end_date)

        return FeedbackAnalysisCostResponse(
            total_cost_usd=stats["total_cost_usd"],
            total_tokens=stats["total_tokens"],
            total_calls=stats["total_calls"],
            average_cost_per_analysis=stats["average_cost_per_analysis"],
        )

    except Exception as e:
        logger.error(f"Error getting feedback analysis costs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get feedback analysis costs",
        ) from e


# ==================== HEALTH CHECK ====================


@router.get("/health")
async def cost_statistics_health_check():
    """
    Cost statistics service health check.

    Returns:
        Service status
    """
    return {"status": "healthy", "service": "cost-statistics", "version": "1.0.0"}
