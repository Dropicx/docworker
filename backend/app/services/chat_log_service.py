"""
Chat Log Service

Provides logging functionality for chat requests with:
- GDPR-compliant design (no query text storage)
- SHA-256 hashing for PII (IP, session, user-agent)
- Non-blocking logging (failures don't break chat flow)
- Two-phase logging (request first, response update after)
"""

from datetime import datetime
import hashlib
import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database.connection import get_db_session_context
from app.repositories.chat_log_repository import ChatLogRepository

logger = logging.getLogger(__name__)


class ChatLogService:
    """
    Service for logging chat requests and responses.

    Handles all GDPR-compliant logging operations including:
    - Hashing PII (IP addresses, session tokens, user agents)
    - Extracting query metadata without storing query text
    - Two-phase logging (request → response update)
    - Non-blocking error handling
    """

    def __init__(self, db: Session | None = None):
        """
        Initialize chat log service.

        Args:
            db: Optional database session. If not provided, uses context manager.
        """
        self._db = db

    @staticmethod
    def hash_value(value: str | None) -> str | None:
        """
        Hash a value using SHA-256 for privacy.

        Args:
            value: String to hash

        Returns:
            SHA-256 hex digest or None if input is None/empty
        """
        if not value:
            return None
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_query_metadata(query: str) -> dict[str, int]:
        """
        Extract metadata from query without storing the text.

        Args:
            query: The query string

        Returns:
            Dict with query_length and query_word_count
        """
        if not query:
            return {"query_length": 0, "query_word_count": 0}

        return {
            "query_length": len(query),
            "query_word_count": len(query.split()),
        }

    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID."""
        return str(uuid4())

    def log_request(
        self,
        request_id: str,
        app_id: str,
        ip_address: str,
        query: str,
        session_token: str | None = None,
        conversation_id: str | None = None,
        user_agent: str | None = None,
        rate_limit_allowed: bool = True,
        rate_limit_type: str | None = None,
        violations_at_request: int = 0,
    ) -> bool:
        """
        Log initial chat request (phase 1 of two-phase logging).

        This is called BEFORE the Dify request is made.
        Non-blocking: failures are logged but don't raise exceptions.

        Args:
            request_id: Unique request identifier
            app_id: App ID (guidelines/befund)
            ip_address: Client IP address (will be hashed)
            query: Query text (only metadata extracted, text not stored)
            session_token: Optional session token (will be hashed)
            conversation_id: Optional Dify conversation ID
            user_agent: Optional user agent (will be hashed)
            rate_limit_allowed: Whether request passed rate limiting
            rate_limit_type: Type of rate limit hit (if any)
            violations_at_request: Number of violations at request time

        Returns:
            True if logging succeeded, False otherwise
        """
        try:
            # Extract metadata from query (don't store the text)
            query_meta = self.extract_query_metadata(query)

            # Hash PII
            ip_hash = self.hash_value(ip_address)
            session_hash = self.hash_value(session_token)
            ua_hash = self.hash_value(user_agent)

            # Determine if new conversation
            is_new = not bool(conversation_id)

            # Use provided session or create new one
            if self._db:
                repo = ChatLogRepository(self._db)
                repo.create(
                    request_id=request_id,
                    app_id=app_id,
                    ip_address_hash=ip_hash,
                    session_token_hash=session_hash,
                    conversation_id=conversation_id,
                    query_length=query_meta["query_length"],
                    query_word_count=query_meta["query_word_count"],
                    is_new_conversation=is_new,
                    rate_limit_allowed=rate_limit_allowed,
                    rate_limit_type=rate_limit_type,
                    violations_at_request=violations_at_request,
                    user_agent_hash=ua_hash,
                    status="pending" if rate_limit_allowed else "rate_limited",
                )
            else:
                with get_db_session_context() as db:
                    repo = ChatLogRepository(db)
                    repo.create(
                        request_id=request_id,
                        app_id=app_id,
                        ip_address_hash=ip_hash,
                        session_token_hash=session_hash,
                        conversation_id=conversation_id,
                        query_length=query_meta["query_length"],
                        query_word_count=query_meta["query_word_count"],
                        is_new_conversation=is_new,
                        rate_limit_allowed=rate_limit_allowed,
                        rate_limit_type=rate_limit_type,
                        violations_at_request=violations_at_request,
                        user_agent_hash=ua_hash,
                        status="pending" if rate_limit_allowed else "rate_limited",
                    )

            logger.debug(f"Logged chat request: {request_id}")
            return True

        except Exception as e:
            # Non-blocking: log error but don't raise
            logger.error(f"Failed to log chat request {request_id}: {e}")
            return False

    def update_with_response(
        self,
        request_id: str,
        status: str,
        message_id: str | None = None,
        conversation_id: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cost_usd: float | None = None,
        response_time_ms: int | None = None,
        first_token_time_ms: int | None = None,
        stream_chunks: int | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        log_metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update chat log with response data (phase 2 of two-phase logging).

        This is called AFTER the Dify stream completes.
        Non-blocking: failures are logged but don't raise exceptions.

        Args:
            request_id: Request ID from phase 1
            status: Final status (success/error/timeout)
            message_id: Message ID from Dify
            conversation_id: Conversation ID from Dify (may be new)
            prompt_tokens: Prompt token count from Dify
            completion_tokens: Completion token count from Dify
            total_tokens: Total token count from Dify
            cost_usd: Cost from Dify (if provided)
            response_time_ms: Total response time
            first_token_time_ms: Time to first token
            stream_chunks: Number of SSE chunks received
            error_type: Error type if failed
            error_message: Error message if failed (will be truncated)
            log_metadata: Additional metadata (retriever_resources, etc.)

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            # Truncate error message if too long
            if error_message and len(error_message) > 500:
                error_message = error_message[:497] + "..."

            update_data = {
                "status": status,
                "updated_at": datetime.utcnow(),
            }

            # Add optional fields only if provided
            if message_id is not None:
                update_data["message_id"] = message_id
            if conversation_id is not None:
                update_data["conversation_id"] = conversation_id
            if prompt_tokens is not None:
                update_data["prompt_tokens"] = prompt_tokens
            if completion_tokens is not None:
                update_data["completion_tokens"] = completion_tokens
            if total_tokens is not None:
                update_data["total_tokens"] = total_tokens
            if cost_usd is not None:
                update_data["cost_usd"] = cost_usd
            if response_time_ms is not None:
                update_data["response_time_ms"] = response_time_ms
            if first_token_time_ms is not None:
                update_data["first_token_time_ms"] = first_token_time_ms
            if stream_chunks is not None:
                update_data["stream_chunks"] = stream_chunks
            if error_type is not None:
                update_data["error_type"] = error_type
            if error_message is not None:
                update_data["error_message"] = error_message
            if log_metadata is not None:
                update_data["log_metadata"] = log_metadata

            # Use provided session or create new one
            if self._db:
                repo = ChatLogRepository(self._db)
                repo.update_by_request_id(request_id, **update_data)
            else:
                with get_db_session_context() as db:
                    repo = ChatLogRepository(db)
                    repo.update_by_request_id(request_id, **update_data)

            logger.debug(f"Updated chat log: {request_id} -> {status}")
            return True

        except Exception as e:
            # Non-blocking: log error but don't raise
            logger.error(f"Failed to update chat log {request_id}: {e}")
            return False


# Global singleton for convenience (stateless, uses context manager)
chat_log_service = ChatLogService()
