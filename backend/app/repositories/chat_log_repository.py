"""
Chat Log Repository

Handles database operations for chat request logging and analytics.
Provides CRUD operations and specialized analytics queries.
"""

from datetime import datetime, date
from typing import Any

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.database.chat_models import ChatLogDB
from app.repositories.base_repository import BaseRepository


class ChatLogRepository(BaseRepository[ChatLogDB]):
    """
    Repository for chat log operations.

    Provides CRUD operations and analytics queries for chat request logs.
    All queries are designed for GDPR compliance (no query text exposure).
    """

    def __init__(self, db: Session):
        """
        Initialize chat log repository.

        Args:
            db: Database session
        """
        super().__init__(db, ChatLogDB)

    def get_by_request_id(self, request_id: str) -> ChatLogDB | None:
        """
        Get a chat log by its unique request ID.

        Args:
            request_id: UUID string of the request

        Returns:
            ChatLogDB instance or None
        """
        return (
            self.db.query(self.model)
            .filter(self.model.request_id == request_id)
            .first()
        )

    def update_by_request_id(self, request_id: str, **kwargs) -> ChatLogDB | None:
        """
        Update a chat log by request ID.

        Args:
            request_id: UUID string of the request
            **kwargs: Fields to update

        Returns:
            Updated ChatLogDB instance or None
        """
        log = self.get_by_request_id(request_id)
        if not log:
            return None

        for key, value in kwargs.items():
            if hasattr(log, key):
                setattr(log, key, value)

        self.db.commit()
        self.db.refresh(log)
        return log

    def get_filtered(
        self,
        app_id: str | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        ip_hash: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChatLogDB]:
        """
        Get chat logs with multiple filters.

        Args:
            app_id: Filter by app (guidelines/befund)
            status: Filter by status (success/error/rate_limited/timeout)
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            ip_hash: Filter by IP address hash
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            List of matching ChatLogDB instances
        """
        query = self.db.query(self.model)

        if app_id:
            query = query.filter(self.model.app_id == app_id)
        if status:
            query = query.filter(self.model.status == status)
        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)
        if ip_hash:
            query = query.filter(self.model.ip_address_hash == ip_hash)

        return (
            query.order_by(self.model.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    # ==================== Analytics Queries ====================

    def get_overview_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get overview statistics for chat usage.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dictionary with total_requests, total_tokens, total_cost_usd,
            success_rate, avg_response_time_ms
        """
        query = self.db.query(
            func.count(self.model.id).label("total_requests"),
            func.coalesce(func.sum(self.model.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(self.model.cost_usd), 0.0).label("total_cost_usd"),
            func.count(
                case((self.model.status == "success", 1))
            ).label("success_count"),
            func.avg(
                case(
                    (self.model.status == "success", self.model.response_time_ms)
                )
            ).label("avg_response_time_ms"),
            func.avg(
                case(
                    (self.model.status == "success", self.model.first_token_time_ms)
                )
            ).label("avg_first_token_time_ms"),
        )

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)

        result = query.first()

        total_requests = result.total_requests or 0
        success_count = result.success_count or 0
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "total_requests": total_requests,
            "total_tokens": int(result.total_tokens or 0),
            "total_cost_usd": round(float(result.total_cost_usd or 0), 6),
            "success_count": success_count,
            "success_rate": round(success_rate, 2),
            "avg_response_time_ms": round(float(result.avg_response_time_ms or 0), 2),
            "avg_first_token_time_ms": round(float(result.avg_first_token_time_ms or 0), 2),
        }

    def get_daily_stats(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        app_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get daily breakdown of chat statistics.

        Args:
            start_date: Start date
            end_date: End date
            app_id: Optional filter by app

        Returns:
            List of dicts with date, request_count, tokens, cost, success_rate
        """
        # Extract date from timestamp
        date_col = func.date(self.model.created_at)

        query = self.db.query(
            date_col.label("date"),
            func.count(self.model.id).label("request_count"),
            func.coalesce(func.sum(self.model.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(self.model.cost_usd), 0.0).label("total_cost_usd"),
            func.count(case((self.model.status == "success", 1))).label("success_count"),
            func.count(case((self.model.status == "error", 1))).label("error_count"),
            func.count(case((self.model.status == "rate_limited", 1))).label("rate_limited_count"),
        )

        if start_date:
            query = query.filter(func.date(self.model.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(self.model.created_at) <= end_date)
        if app_id:
            query = query.filter(self.model.app_id == app_id)

        results = (
            query.group_by(date_col)
            .order_by(date_col.desc())
            .all()
        )

        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "request_count": row.request_count,
                "total_tokens": int(row.total_tokens),
                "total_cost_usd": round(float(row.total_cost_usd), 6),
                "success_count": row.success_count,
                "error_count": row.error_count,
                "rate_limited_count": row.rate_limited_count,
                "success_rate": round(
                    (row.success_count / row.request_count * 100)
                    if row.request_count > 0 else 0.0, 2
                ),
            }
            for row in results
        ]

    def get_hourly_stats(
        self,
        target_date: date,
        app_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get hourly breakdown for a specific date.

        Args:
            target_date: The date to analyze
            app_id: Optional filter by app

        Returns:
            List of dicts with hour, request_count, tokens, cost
        """
        # Extract hour from timestamp
        hour_col = func.extract("hour", self.model.created_at)
        date_col = func.date(self.model.created_at)

        query = self.db.query(
            hour_col.label("hour"),
            func.count(self.model.id).label("request_count"),
            func.coalesce(func.sum(self.model.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(self.model.cost_usd), 0.0).label("total_cost_usd"),
            func.count(case((self.model.status == "success", 1))).label("success_count"),
        ).filter(date_col == target_date)

        if app_id:
            query = query.filter(self.model.app_id == app_id)

        results = (
            query.group_by(hour_col)
            .order_by(hour_col)
            .all()
        )

        return [
            {
                "hour": int(row.hour),
                "request_count": row.request_count,
                "total_tokens": int(row.total_tokens),
                "total_cost_usd": round(float(row.total_cost_usd), 6),
                "success_count": row.success_count,
            }
            for row in results
        ]

    def get_cost_breakdown(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get cost breakdown by app.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict with total_cost and per-app breakdown
        """
        query = self.db.query(
            self.model.app_id,
            func.count(self.model.id).label("request_count"),
            func.coalesce(func.sum(self.model.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(self.model.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(self.model.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(self.model.cost_usd), 0.0).label("total_cost_usd"),
        )

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)

        results = query.group_by(self.model.app_id).all()

        apps = {}
        total_cost = 0.0
        total_tokens = 0

        for row in results:
            cost = float(row.total_cost_usd)
            tokens = int(row.total_tokens)
            total_cost += cost
            total_tokens += tokens

            apps[row.app_id] = {
                "request_count": row.request_count,
                "total_tokens": tokens,
                "prompt_tokens": int(row.prompt_tokens),
                "completion_tokens": int(row.completion_tokens),
                "total_cost_usd": round(cost, 6),
            }

        return {
            "total_cost_usd": round(total_cost, 6),
            "total_tokens": total_tokens,
            "by_app": apps,
        }

    def get_error_breakdown(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get error statistics grouped by type.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict with error counts by type and status
        """
        # By status
        status_query = self.db.query(
            self.model.status,
            func.count(self.model.id).label("count"),
        )

        if start_date:
            status_query = status_query.filter(self.model.created_at >= start_date)
        if end_date:
            status_query = status_query.filter(self.model.created_at <= end_date)

        status_results = status_query.group_by(self.model.status).all()

        # By error_type (for non-success statuses)
        error_query = self.db.query(
            self.model.error_type,
            func.count(self.model.id).label("count"),
        ).filter(self.model.status != "success")

        if start_date:
            error_query = error_query.filter(self.model.created_at >= start_date)
        if end_date:
            error_query = error_query.filter(self.model.created_at <= end_date)

        error_results = (
            error_query.filter(self.model.error_type.isnot(None))
            .group_by(self.model.error_type)
            .all()
        )

        return {
            "by_status": {row.status: row.count for row in status_results},
            "by_error_type": {
                (row.error_type or "unknown"): row.count for row in error_results
            },
        }

    def get_performance_percentiles(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Get performance percentiles (p50, p95, p99) for response times.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Dict with response_time and first_token_time percentiles
        """
        # Build base query for successful requests with response times
        base_filter = and_(
            self.model.status == "success",
            self.model.response_time_ms.isnot(None),
        )

        if start_date:
            base_filter = and_(base_filter, self.model.created_at >= start_date)
        if end_date:
            base_filter = and_(base_filter, self.model.created_at <= end_date)

        # Get response times
        response_times = (
            self.db.query(self.model.response_time_ms)
            .filter(base_filter)
            .order_by(self.model.response_time_ms)
            .all()
        )

        # Get first token times
        first_token_filter = and_(base_filter, self.model.first_token_time_ms.isnot(None))
        first_token_times = (
            self.db.query(self.model.first_token_time_ms)
            .filter(first_token_filter)
            .order_by(self.model.first_token_time_ms)
            .all()
        )

        def calculate_percentiles(values: list) -> dict:
            if not values:
                return {"p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}

            vals = [v[0] for v in values]
            n = len(vals)

            return {
                "p50": vals[int(n * 0.50)] if n > 0 else 0,
                "p95": vals[int(n * 0.95)] if n > 0 else 0,
                "p99": vals[int(n * 0.99)] if n > 0 else 0,
                "min": vals[0] if n > 0 else 0,
                "max": vals[-1] if n > 0 else 0,
            }

        return {
            "sample_count": len(response_times),
            "response_time_ms": calculate_percentiles(response_times),
            "first_token_time_ms": calculate_percentiles(first_token_times),
        }

    def get_unique_users_count(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Get count of unique users (by IP hash).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Count of unique IP hashes
        """
        query = self.db.query(
            func.count(func.distinct(self.model.ip_address_hash))
        )

        if start_date:
            query = query.filter(self.model.created_at >= start_date)
        if end_date:
            query = query.filter(self.model.created_at <= end_date)

        return query.scalar() or 0

    def delete_old_logs(self, older_than: datetime) -> int:
        """
        Delete logs older than specified date (for GDPR retention policies).

        Args:
            older_than: Delete logs created before this timestamp

        Returns:
            Number of deleted records
        """
        try:
            deleted = (
                self.db.query(self.model)
                .filter(self.model.created_at < older_than)
                .delete()
            )
            self.db.commit()
            return deleted
        except Exception:
            self.db.rollback()
            return 0
