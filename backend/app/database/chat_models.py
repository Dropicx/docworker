"""
Chat Database Models

This module contains database models for:
- Chat rate limiting and abuse prevention
- Chat request logging for analytics and cost tracking

Rate limiting tracks message counts per identifier (IP:session combo) with
multi-window limits and escalating penalties for repeat offenders.

Chat logging tracks all requests for analytics (GDPR-compliant: no query text storage).
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Index, Integer, String, Text
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


class ChatLogDB(Base):
    """
    GDPR-compliant chat request logging for analytics and cost tracking.

    Tracks chat requests with metadata (NOT text content) for:
    - Usage analytics (requests by app, time, etc.)
    - Cost tracking (tokens, cost from Dify)
    - Performance metrics (response time, first token latency)
    - Error analysis and debugging

    Privacy notes:
    - Query text is NOT stored (only length/word count)
    - IP addresses and session tokens are SHA-256 hashed
    - User agents are hashed for fingerprinting without PII
    """

    __tablename__ = "chat_logs"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)

    # Request identification
    request_id = Column(String(36), unique=True, nullable=False, index=True)
    app_id = Column(String(50), nullable=False, index=True)  # guidelines/befund

    # Session identifiers (hashed for privacy)
    ip_address_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    session_token_hash = Column(String(64), nullable=True, index=True)  # SHA-256
    conversation_id = Column(String(255), nullable=True, index=True)  # From Dify
    message_id = Column(String(255), nullable=True)  # From Dify message_end

    # Query metadata (NOT the query text - GDPR compliant)
    query_length = Column(Integer, nullable=True)  # Character count
    query_word_count = Column(Integer, nullable=True)  # Word count
    is_new_conversation = Column(Boolean, default=True, nullable=False)

    # Rate limit context (at time of request)
    rate_limit_allowed = Column(Boolean, default=True, nullable=False)
    rate_limit_type = Column(String(20), nullable=True)  # minute/hour/day/temp_ban/permanent_ban
    violations_at_request = Column(Integer, default=0, nullable=False)

    # Token usage (from Dify message_end event)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Cost tracking
    cost_usd = Column(Float, nullable=True)

    # Performance metrics
    response_time_ms = Column(Integer, nullable=True)  # Total request duration
    first_token_time_ms = Column(Integer, nullable=True)  # Time to first token
    stream_chunks = Column(Integer, nullable=True)  # Number of SSE chunks

    # Request status
    status = Column(String(20), nullable=False, default="pending", index=True)
    # Values: pending, success, error, rate_limited, timeout

    # Error tracking
    error_type = Column(String(50), nullable=True)  # timeout, connect_error, dify_error, etc.
    error_message = Column(String(500), nullable=True)  # Truncated error message

    # Additional context
    user_agent_hash = Column(String(64), nullable=True)  # SHA-256
    log_metadata = Column(JSON, nullable=True)  # retriever_resources, etc. from Dify

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for analytics queries
    __table_args__ = (
        Index("idx_chat_logs_request_id", "request_id"),
        Index("idx_chat_logs_app_id", "app_id"),
        Index("idx_chat_logs_created_at", "created_at"),
        Index("idx_chat_logs_status", "status"),
        Index("idx_chat_logs_ip_hash", "ip_address_hash"),
        Index("idx_chat_logs_session_hash", "session_token_hash"),
        Index("idx_chat_logs_conversation", "conversation_id"),
        # Composite index for date range + app queries
        Index("idx_chat_logs_app_date", "app_id", "created_at"),
        # Composite index for status + date queries
        Index("idx_chat_logs_status_date", "status", "created_at"),
    )

    def __repr__(self):
        return (
            f"<ChatLogDB("
            f"id='{self.id}', "
            f"request_id='{self.request_id}', "
            f"app_id='{self.app_id}', "
            f"status='{self.status}'"
            f")>"
        )
