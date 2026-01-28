"""
Chat Rate Limiter Service

Provides rate limiting for chat API endpoints with:
- Multi-window tracking (minute/hour/day)
- Escalating penalties for repeat offenders
- IP + session token tracking
- Database persistence for state across restarts
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.auth_models import AuditAction, AuditLogDB
from app.database.chat_models import ChatRateLimitDB
from app.database.connection import get_db_session_context

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    limit_type: str | None = None  # "minute", "hour", "day", "temp_ban", "permanent_ban"
    retry_after: int | None = None  # Seconds until allowed again
    message: str | None = None
    violations: int = 0
    warning_issued: bool = False


# Escalating penalty thresholds
PENALTY_THRESHOLDS = {
    "warning": (3, 5),  # 3-5 violations: formal warning
    "temp_ban_15min": (6, 10),  # 6-10 violations: 15 minute ban
    "temp_ban_1hour": (11, 20),  # 11-20 violations: 1 hour ban
    "temp_ban_24hour": (21, 50),  # 21-50 violations: 24 hour ban
    "permanent_ban": (51, float("inf")),  # 51+ violations: permanent ban
}

# Violation decay: 1 violation decays per day after 7 days of good behavior
VIOLATION_DECAY_DAYS = 7
VIOLATION_DECAY_RATE = 1  # Violations removed per day after decay period


class ChatRateLimiter:
    """
    Rate limiter for chat API with multi-window limits and escalating penalties.

    Usage:
        limiter = ChatRateLimiter()
        result = await limiter.check_rate_limit(ip_address, session_token, user_agent)
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "message": result.message},
                headers={"Retry-After": str(result.retry_after)}
            )
        # Process the request
        await limiter.record_message(ip_address, session_token)
    """

    def __init__(self):
        self.limits = {
            "minute": settings.chat_rate_limit_per_minute,
            "hour": settings.chat_rate_limit_per_hour,
            "day": settings.chat_rate_limit_per_day,
        }
        self.enabled = settings.chat_rate_limit_enabled

    def _get_identifier(self, ip_address: str, session_token: str | None) -> str:
        """Create combined identifier from IP and session token."""
        if session_token:
            return f"{ip_address}:{session_token}"
        return f"{ip_address}:anonymous"

    def _reset_windows_if_needed(
        self, record: ChatRateLimitDB, now: datetime
    ) -> ChatRateLimitDB:
        """Reset time windows if they have expired."""
        # Reset minute window (60 seconds)
        if record.minute_window_start:
            elapsed_minutes = (now - record.minute_window_start).total_seconds()
            if elapsed_minutes >= 60:
                record.messages_last_minute = 0
                record.minute_window_start = now

        # Reset hour window (3600 seconds)
        if record.hour_window_start:
            elapsed_hours = (now - record.hour_window_start).total_seconds()
            if elapsed_hours >= 3600:
                record.messages_last_hour = 0
                record.hour_window_start = now

        # Reset day window (86400 seconds)
        if record.day_window_start:
            elapsed_days = (now - record.day_window_start).total_seconds()
            if elapsed_days >= 86400:
                record.messages_last_day = 0
                record.day_window_start = now

        return record

    def _decay_violations(self, record: ChatRateLimitDB, now: datetime) -> ChatRateLimitDB:
        """Decay violations after period of good behavior."""
        if record.last_violation_at and record.rate_limit_violations > 0:
            days_since_violation = (now - record.last_violation_at).days
            if days_since_violation > VIOLATION_DECAY_DAYS:
                decay_amount = (days_since_violation - VIOLATION_DECAY_DAYS) * VIOLATION_DECAY_RATE
                record.rate_limit_violations = max(0, record.rate_limit_violations - decay_amount)
        return record

    def _get_penalty_action(self, violations: int) -> tuple[str, int | None]:
        """
        Determine penalty action based on violation count.

        Returns:
            Tuple of (action_type, ban_duration_minutes or None)
        """
        if violations >= PENALTY_THRESHOLDS["permanent_ban"][0]:
            return "permanent_ban", None
        elif violations >= PENALTY_THRESHOLDS["temp_ban_24hour"][0]:
            return "temp_ban", 24 * 60  # 24 hours in minutes
        elif violations >= PENALTY_THRESHOLDS["temp_ban_1hour"][0]:
            return "temp_ban", 60  # 1 hour
        elif violations >= PENALTY_THRESHOLDS["temp_ban_15min"][0]:
            return "temp_ban", 15  # 15 minutes
        elif violations >= PENALTY_THRESHOLDS["warning"][0]:
            return "warning", None
        return "log", None

    def _log_audit(
        self,
        db: Session,
        action: AuditAction,
        ip_address: str,
        user_agent: str | None,
        details: dict,
    ) -> None:
        """Log rate limit event to audit trail."""
        try:
            audit_log = AuditLogDB(
                action=action,
                resource_type="chat_rate_limit",
                resource_id=ip_address,
                ip_address=ip_address,
                user_agent=user_agent,
                details=json.dumps(details),
            )
            db.add(audit_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            db.rollback()

    def check_rate_limit(
        self,
        ip_address: str,
        session_token: str | None = None,
        user_agent: str | None = None,
    ) -> RateLimitResult:
        """
        Check if a request is allowed under rate limits.

        This method checks bans and rate limits but does NOT increment counters.
        Call record_message() after processing the request.

        Args:
            ip_address: Client IP address
            session_token: Optional client-side session token
            user_agent: Optional user agent string

        Returns:
            RateLimitResult with allowed status and details
        """
        if not self.enabled:
            return RateLimitResult(allowed=True)

        identifier = self._get_identifier(ip_address, session_token)
        now = datetime.utcnow()

        with get_db_session_context() as db:
            # Get or create rate limit record
            stmt = select(ChatRateLimitDB).where(ChatRateLimitDB.identifier == identifier)
            record = db.execute(stmt).scalar_one_or_none()

            if not record:
                # First request from this identifier - allowed
                return RateLimitResult(allowed=True)

            # Check permanent ban
            if record.permanent_ban:
                return RateLimitResult(
                    allowed=False,
                    limit_type="permanent_ban",
                    retry_after=None,
                    message="Access permanently suspended. Contact support if you believe this is an error.",
                    violations=record.rate_limit_violations,
                )

            # Check temp ban
            if record.temp_ban_until and record.temp_ban_until > now:
                retry_after = int((record.temp_ban_until - now).total_seconds())
                return RateLimitResult(
                    allowed=False,
                    limit_type="temp_ban",
                    retry_after=retry_after,
                    message=f"Temporarily suspended. Try again in {retry_after // 60} minutes.",
                    violations=record.rate_limit_violations,
                )

            # Reset windows if needed
            record = self._reset_windows_if_needed(record, now)
            db.commit()

            # Check rate limits
            if record.messages_last_minute >= self.limits["minute"]:
                # Calculate retry time (when minute window resets)
                elapsed = (now - record.minute_window_start).total_seconds()
                retry_after = max(1, int(60 - elapsed))
                return RateLimitResult(
                    allowed=False,
                    limit_type="minute",
                    retry_after=retry_after,
                    message=f"Too many messages. Please wait {retry_after} seconds.",
                    violations=record.rate_limit_violations,
                )

            if record.messages_last_hour >= self.limits["hour"]:
                elapsed = (now - record.hour_window_start).total_seconds()
                retry_after = max(1, int(3600 - elapsed))
                minutes = retry_after // 60
                return RateLimitResult(
                    allowed=False,
                    limit_type="hour",
                    retry_after=retry_after,
                    message=f"Hourly limit reached. Please wait {minutes} minutes.",
                    violations=record.rate_limit_violations,
                )

            if record.messages_last_day >= self.limits["day"]:
                elapsed = (now - record.day_window_start).total_seconds()
                retry_after = max(1, int(86400 - elapsed))
                hours = retry_after // 3600
                return RateLimitResult(
                    allowed=False,
                    limit_type="day",
                    retry_after=retry_after,
                    message=f"Daily limit reached. Please try again in {hours} hours.",
                    violations=record.rate_limit_violations,
                )

            return RateLimitResult(allowed=True, violations=record.rate_limit_violations)

    def record_message(
        self,
        ip_address: str,
        session_token: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Record a message after it has been processed.

        Call this AFTER processing the chat request to increment counters.

        Args:
            ip_address: Client IP address
            session_token: Optional client-side session token
            user_agent: Optional user agent string
        """
        if not self.enabled:
            return

        identifier = self._get_identifier(ip_address, session_token)
        now = datetime.utcnow()

        with get_db_session_context() as db:
            # Get or create rate limit record
            stmt = select(ChatRateLimitDB).where(ChatRateLimitDB.identifier == identifier)
            record = db.execute(stmt).scalar_one_or_none()

            if not record:
                # Create new record
                record = ChatRateLimitDB(
                    identifier=identifier,
                    ip_address=ip_address,
                    session_token=session_token,
                    messages_last_minute=1,
                    messages_last_hour=1,
                    messages_last_day=1,
                    minute_window_start=now,
                    hour_window_start=now,
                    day_window_start=now,
                    user_agent=user_agent,
                    last_request_at=now,
                )
                db.add(record)
                db.commit()
                return

            # Reset windows if needed
            record = self._reset_windows_if_needed(record, now)

            # Increment counters
            record.messages_last_minute += 1
            record.messages_last_hour += 1
            record.messages_last_day += 1
            record.last_request_at = now
            if user_agent:
                record.user_agent = user_agent

            db.commit()

    def record_violation(
        self,
        ip_address: str,
        session_token: str | None = None,
        user_agent: str | None = None,
        limit_type: str = "minute",
    ) -> RateLimitResult:
        """
        Record a rate limit violation and apply escalating penalties.

        Call this when a request is rejected due to rate limits.

        Args:
            ip_address: Client IP address
            session_token: Optional client-side session token
            user_agent: Optional user agent string
            limit_type: Type of limit exceeded

        Returns:
            RateLimitResult with any new penalties applied
        """
        if not self.enabled:
            return RateLimitResult(allowed=False, limit_type=limit_type)

        identifier = self._get_identifier(ip_address, session_token)
        now = datetime.utcnow()

        with get_db_session_context() as db:
            # Get or create rate limit record
            stmt = select(ChatRateLimitDB).where(ChatRateLimitDB.identifier == identifier)
            record = db.execute(stmt).scalar_one_or_none()

            if not record:
                record = ChatRateLimitDB(
                    identifier=identifier,
                    ip_address=ip_address,
                    session_token=session_token,
                    user_agent=user_agent,
                    minute_window_start=now,
                    hour_window_start=now,
                    day_window_start=now,
                )
                db.add(record)

            # Decay old violations
            record = self._decay_violations(record, now)

            # Increment violation count
            record.rate_limit_violations += 1
            record.last_violation_at = now
            violations = record.rate_limit_violations

            # Determine and apply penalty
            action, ban_minutes = self._get_penalty_action(violations)
            warning_issued = False

            if action == "permanent_ban":
                record.permanent_ban = True
                record.ban_reason = f"Exceeded {violations} rate limit violations"
                logger.warning(f"PERMANENT BAN applied to {ip_address} after {violations} violations")
                self._log_audit(
                    db,
                    AuditAction.CHAT_PERMANENT_BAN,
                    ip_address,
                    user_agent,
                    {"violations": violations, "identifier": identifier},
                )

            elif action == "temp_ban" and ban_minutes:
                record.temp_ban_until = now + timedelta(minutes=ban_minutes)
                record.ban_reason = f"Temporary ban for {ban_minutes} minutes after {violations} violations"
                logger.warning(
                    f"TEMP BAN ({ban_minutes}m) applied to {ip_address} after {violations} violations"
                )
                self._log_audit(
                    db,
                    AuditAction.CHAT_TEMP_BAN,
                    ip_address,
                    user_agent,
                    {"violations": violations, "ban_minutes": ban_minutes, "identifier": identifier},
                )

            elif action == "warning":
                warning_issued = True
                logger.warning(f"Rate limit WARNING for {ip_address}: {violations} violations")
                self._log_audit(
                    db,
                    AuditAction.CHAT_RATE_LIMIT_WARNING,
                    ip_address,
                    user_agent,
                    {"violations": violations, "identifier": identifier},
                )

            else:
                # Just log the violation
                logger.info(f"Rate limit violation #{violations} for {ip_address}")

            db.commit()

            # Calculate retry_after based on new state
            retry_after = None
            message = None

            if record.permanent_ban:
                message = "Access permanently suspended due to repeated violations."
                limit_type = "permanent_ban"
            elif record.temp_ban_until and record.temp_ban_until > now:
                retry_after = int((record.temp_ban_until - now).total_seconds())
                message = f"Temporarily suspended for {retry_after // 60} minutes due to repeated violations."
                limit_type = "temp_ban"

            return RateLimitResult(
                allowed=False,
                limit_type=limit_type,
                retry_after=retry_after,
                message=message,
                violations=violations,
                warning_issued=warning_issued,
            )

    def get_status(
        self,
        ip_address: str,
        session_token: str | None = None,
    ) -> dict:
        """
        Get current rate limit status for an identifier.

        Useful for debugging or admin dashboards.

        Args:
            ip_address: Client IP address
            session_token: Optional client-side session token

        Returns:
            Dictionary with current rate limit state
        """
        identifier = self._get_identifier(ip_address, session_token)
        now = datetime.utcnow()

        with get_db_session_context() as db:
            stmt = select(ChatRateLimitDB).where(ChatRateLimitDB.identifier == identifier)
            record = db.execute(stmt).scalar_one_or_none()

            if not record:
                return {
                    "identifier": identifier,
                    "exists": False,
                    "messages_minute": 0,
                    "messages_hour": 0,
                    "messages_day": 0,
                    "limits": self.limits,
                    "violations": 0,
                    "banned": False,
                }

            # Calculate remaining in each window
            record = self._reset_windows_if_needed(record, now)

            return {
                "identifier": identifier,
                "exists": True,
                "messages_minute": record.messages_last_minute,
                "messages_hour": record.messages_last_hour,
                "messages_day": record.messages_last_day,
                "limits": self.limits,
                "remaining_minute": max(0, self.limits["minute"] - record.messages_last_minute),
                "remaining_hour": max(0, self.limits["hour"] - record.messages_last_hour),
                "remaining_day": max(0, self.limits["day"] - record.messages_last_day),
                "violations": record.rate_limit_violations,
                "banned": record.is_banned(now),
                "temp_ban_until": record.temp_ban_until.isoformat() if record.temp_ban_until else None,
                "permanent_ban": record.permanent_ban,
                "last_request": record.last_request_at.isoformat() if record.last_request_at else None,
            }


# Global singleton instance
chat_rate_limiter = ChatRateLimiter()
