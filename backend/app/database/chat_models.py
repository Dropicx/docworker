"""
Chat Rate Limiting Database Models

This module contains database models for chat rate limiting and abuse prevention.
Tracks message counts per identifier (IP:session combo) with multi-window limits
and escalating penalties for repeat offenders.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database.auth_models import Base


class ChatRateLimitDB(Base):
    """
    Rate limit tracking for chat API.

    Tracks message counts across multiple time windows (minute, hour, day)
    and implements escalating penalties for repeat violations.

    Identifier format: "{ip_address}:{session_token}" for combined tracking.
    """

    __tablename__ = "chat_rate_limits"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Identifier (IP:session combo for combined tracking)
    identifier = Column(String(256), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv4 or IPv6
    session_token = Column(String(64), nullable=True, index=True)  # Client-side session token

    # Multi-window message counters
    messages_last_minute = Column(Integer, default=0, nullable=False)
    messages_last_hour = Column(Integer, default=0, nullable=False)
    messages_last_day = Column(Integer, default=0, nullable=False)

    # Window start timestamps (for resetting counters)
    minute_window_start = Column(DateTime, default=func.now(), nullable=False)
    hour_window_start = Column(DateTime, default=func.now(), nullable=False)
    day_window_start = Column(DateTime, default=func.now(), nullable=False)

    # Violation tracking for escalating penalties
    rate_limit_violations = Column(Integer, default=0, nullable=False)
    last_violation_at = Column(DateTime, nullable=True, index=True)

    # Ban status
    temp_ban_until = Column(DateTime, nullable=True, index=True)
    permanent_ban = Column(Boolean, default=False, nullable=False, index=True)
    ban_reason = Column(Text, nullable=True)

    # Request metadata (for abuse analysis)
    user_agent = Column(Text, nullable=True)
    last_request_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_chat_rate_limits_identifier", "identifier"),
        Index("idx_chat_rate_limits_ip", "ip_address"),
        Index("idx_chat_rate_limits_session", "session_token"),
        Index("idx_chat_rate_limits_temp_ban", "temp_ban_until"),
        Index("idx_chat_rate_limits_permanent_ban", "permanent_ban"),
        Index("idx_chat_rate_limits_violations", "rate_limit_violations"),
        Index("idx_chat_rate_limits_last_request", "last_request_at"),
    )

    def __repr__(self):
        return (
            f"<ChatRateLimitDB("
            f"id='{self.id}', "
            f"identifier='{self.identifier[:20]}...', "
            f"violations={self.rate_limit_violations}, "
            f"banned={self.permanent_ban}"
            f")>"
        )

    def is_banned(self, now: datetime | None = None) -> bool:
        """Check if this identifier is currently banned."""
        if self.permanent_ban:
            return True
        if self.temp_ban_until:
            now = now or datetime.utcnow()
            return self.temp_ban_until > now
        return False

    def get_ban_remaining_seconds(self, now: datetime | None = None) -> int | None:
        """Get remaining seconds of temp ban, or None if not temp banned."""
        if self.permanent_ban:
            return None  # Permanent ban has no remaining time
        if not self.temp_ban_until:
            return None
        now = now or datetime.utcnow()
        if self.temp_ban_until <= now:
            return None
        return int((self.temp_ban_until - now).total_seconds())
