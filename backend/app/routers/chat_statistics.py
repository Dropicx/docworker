"""
Chat Statistics Router

Provides admin endpoints for viewing chat usage statistics, including:
- Usage overview (requests, tokens, costs, success rate)
- Daily/hourly breakdowns
- Cost analysis by app
- Error breakdown
- Performance percentiles (p50/p95/p99)
"""

from datetime import date, datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.permissions import require_admin
from app.database.auth_models import UserDB
from app.database.connection import get_session
from app.repositories.chat_log_repository import ChatLogRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat/stats", tags=["chat-statistics"])


# ==================== RESPONSE MODELS ====================


class ChatOverviewResponse(BaseModel):
    """Overview statistics for chat usage."""

    total_requests: int = Field(..., description="Total chat requests")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    success_count: int = Field(..., description="Successful requests")
    success_rate: float = Field(..., description="Success rate percentage")
    avg_response_time_ms: float = Field(..., description="Average response time in ms")
    avg_first_token_time_ms: float = Field(..., description="Average time to first token in ms")
    unique_users: int = Field(0, description="Unique users (by IP hash)")


class DailyStatEntry(BaseModel):
    """Daily statistics entry."""

    date: str = Field(..., description="Date (ISO format)")
    request_count: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    success_count: int = Field(..., description="Successful requests")
    error_count: int = Field(..., description="Failed requests")
    rate_limited_count: int = Field(..., description="Rate limited requests")
    success_rate: float = Field(..., description="Success rate percentage")


class DailyStatsResponse(BaseModel):
    """Daily statistics response."""

    stats: list[DailyStatEntry] = Field(..., description="Daily stats list")
    total_days: int = Field(..., description="Number of days in response")


class HourlyStatEntry(BaseModel):
    """Hourly statistics entry."""

    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    request_count: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    success_count: int = Field(..., description="Successful requests")


class HourlyStatsResponse(BaseModel):
    """Hourly statistics for a specific date."""

    date: str = Field(..., description="Date (ISO format)")
    stats: list[HourlyStatEntry] = Field(..., description="Hourly stats list")


class AppCostBreakdown(BaseModel):
    """Cost breakdown for a single app."""

    request_count: int = Field(..., description="Number of requests")
    total_tokens: int = Field(..., description="Total tokens")
    prompt_tokens: int = Field(..., description="Prompt tokens")
    completion_tokens: int = Field(..., description="Completion tokens")
    total_cost_usd: float = Field(..., description="Total cost in USD")


class CostBreakdownResponse(BaseModel):
    """Cost breakdown by app."""

    total_cost_usd: float = Field(..., description="Total cost across all apps")
    total_tokens: int = Field(..., description="Total tokens across all apps")
    by_app: dict[str, AppCostBreakdown] = Field(..., description="Breakdown per app")


class ErrorBreakdownResponse(BaseModel):
    """Error breakdown by status and type."""

    by_status: dict[str, int] = Field(..., description="Count by status")
    by_error_type: dict[str, int] = Field(..., description="Count by error type")


class PercentileStats(BaseModel):
    """Percentile statistics."""

    p50: int = Field(..., description="50th percentile (median)")
    p95: int = Field(..., description="95th percentile")
    p99: int = Field(..., description="99th percentile")
    min: int = Field(..., description="Minimum value")
    max: int = Field(..., description="Maximum value")


class PerformanceResponse(BaseModel):
    """Performance percentile statistics."""

    sample_count: int = Field(..., description="Number of samples")
    response_time_ms: PercentileStats = Field(..., description="Response time percentiles")
    first_token_time_ms: PercentileStats = Field(..., description="First token time percentiles")


# ==================== DEPENDENCY ====================


def get_chat_log_repository(db: Session = Depends(get_session)) -> ChatLogRepository:
    """Dependency injection factory for ChatLogRepository."""
    return ChatLogRepository(db)


# ==================== ENDPOINTS ====================


@router.get("/overview", response_model=ChatOverviewResponse)
async def get_chat_overview(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    repo: ChatLogRepository = Depends(get_chat_log_repository),
):
    """
    Get chat usage overview statistics (admin only).

    Returns total requests, tokens, cost, success rate, and average response times.
    """
    try:
        stats = repo.get_overview_stats(start_date=start_date, end_date=end_date)
        unique_users = repo.get_unique_users_count(start_date=start_date, end_date=end_date)

        return ChatOverviewResponse(
            total_requests=stats["total_requests"],
            total_tokens=stats["total_tokens"],
            total_cost_usd=stats["total_cost_usd"],
            success_count=stats["success_count"],
            success_rate=stats["success_rate"],
            avg_response_time_ms=stats["avg_response_time_ms"],
            avg_first_token_time_ms=stats["avg_first_token_time_ms"],
            unique_users=unique_users,
        )

    except Exception as e:
        logger.error(f"Error getting chat overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat overview",
        ) from e


@router.get("/daily", response_model=DailyStatsResponse)
async def get_daily_stats(
    start_date: date | None = Query(None, description="Start date"),
    end_date: date | None = Query(None, description="End date"),
    app_id: str | None = Query(None, description="Filter by app (guidelines/befund)"),
    current_user: UserDB = Depends(require_admin()),
    repo: ChatLogRepository = Depends(get_chat_log_repository),
):
    """
    Get daily breakdown of chat statistics (admin only).

    Returns request count, tokens, cost, and success rate per day.
    Defaults to last 30 days if no date range specified.
    """
    try:
        # Default to last 30 days
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        stats = repo.get_daily_stats(
            start_date=start_date,
            end_date=end_date,
            app_id=app_id,
        )

        return DailyStatsResponse(
            stats=[DailyStatEntry(**s) for s in stats],
            total_days=len(stats),
        )

    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get daily stats",
        ) from e


@router.get("/hourly/{target_date}", response_model=HourlyStatsResponse)
async def get_hourly_stats(
    target_date: date,
    app_id: str | None = Query(None, description="Filter by app (guidelines/befund)"),
    current_user: UserDB = Depends(require_admin()),
    repo: ChatLogRepository = Depends(get_chat_log_repository),
):
    """
    Get hourly breakdown for a specific date (admin only).

    Returns request count, tokens, and cost per hour.
    """
    try:
        stats = repo.get_hourly_stats(target_date=target_date, app_id=app_id)

        return HourlyStatsResponse(
            date=target_date.isoformat(),
            stats=[HourlyStatEntry(**s) for s in stats],
        )

    except Exception as e:
        logger.error(f"Error getting hourly stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get hourly stats",
        ) from e


@router.get("/costs", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    repo: ChatLogRepository = Depends(get_chat_log_repository),
):
    """
    Get cost breakdown by app (admin only).

    Returns total cost and per-app token/cost breakdown.
    """
    try:
        breakdown = repo.get_cost_breakdown(start_date=start_date, end_date=end_date)

        by_app = {app_id: AppCostBreakdown(**data) for app_id, data in breakdown["by_app"].items()}

        return CostBreakdownResponse(
            total_cost_usd=breakdown["total_cost_usd"],
            total_tokens=breakdown["total_tokens"],
            by_app=by_app,
        )

    except Exception as e:
        logger.error(f"Error getting cost breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cost breakdown",
        ) from e


@router.get("/errors", response_model=ErrorBreakdownResponse)
async def get_error_breakdown(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    repo: ChatLogRepository = Depends(get_chat_log_repository),
):
    """
    Get error breakdown by status and type (admin only).

    Returns counts grouped by status (success/error/rate_limited/timeout)
    and by error_type for non-success requests.
    """
    try:
        breakdown = repo.get_error_breakdown(start_date=start_date, end_date=end_date)

        return ErrorBreakdownResponse(
            by_status=breakdown["by_status"],
            by_error_type=breakdown["by_error_type"],
        )

    except Exception as e:
        logger.error(f"Error getting error breakdown: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get error breakdown",
        ) from e


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance_stats(
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    current_user: UserDB = Depends(require_admin()),
    repo: ChatLogRepository = Depends(get_chat_log_repository),
):
    """
    Get performance percentiles (admin only).

    Returns p50/p95/p99 percentiles for response time and first token time.
    Only includes successful requests.
    """
    try:
        perf = repo.get_performance_percentiles(start_date=start_date, end_date=end_date)

        return PerformanceResponse(
            sample_count=perf["sample_count"],
            response_time_ms=PercentileStats(**perf["response_time_ms"]),
            first_token_time_ms=PercentileStats(**perf["first_token_time_ms"]),
        )

    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performance stats",
        ) from e


# ==================== HEALTH CHECK ====================


@router.get("/health")
async def chat_statistics_health_check():
    """
    Chat statistics service health check.

    Returns:
        Service status
    """
    return {"status": "healthy", "service": "chat-statistics", "version": "1.0.0"}
