"""AI Logging Service for comprehensive interaction tracking and debugging.

Full-featured logging service that captures complete AI interaction details including
input/output text, processing times, confidence scores, and metadata. Designed for
debugging, quality assurance, and pipeline analysis.

⚠️ **PRIVACY WARNING**: This service stores FULL TEXT CONTENT (input/output prompts
and completions) in the database. For medical documents containing PII, this may
violate GDPR/HIPAA unless:
    - Database encryption enabled
    - Strict access controls enforced
    - Retention policies implemented (auto-deletion)
    - Legal basis established for processing

**Alternative**: For cost tracking WITHOUT storing text, use AICostTracker which
logs only token counts and metadata (GDPR-compliant by design).

**Core Features**:
    - Full interaction logging: input_text, output_text, metadata
    - Context manager: Automatic timing and error handling
    - Pipeline-specific loggers: Medical validation, classification, translation, etc.
    - Analytics: Success rates, step counts, performance metrics
    - Audit trail: Complete processing history per document

**Use Cases**:
    - Debugging: Reproduce AI behavior from logged inputs
    - Quality assurance: Review AI outputs for accuracy
    - Performance analysis: Identify slow pipeline steps
    - Compliance auditing: Track all AI interactions
    - Model evaluation: Compare outputs across model versions

**Database Schema**:
    Writes to AILogInteractionDB (ai_interaction_logs table) with fields:
    - processing_id, step_name, input_text, output_text
    - processing_time_ms, status, error_message
    - confidence_score, model_name, document_type
    - user_id, session_id, request_id
    - input_metadata, output_metadata (JSON)
    - created_at

**Usage Example**:
    >>> from app.database.connection import get_db_session
    >>> db = next(get_db_session())
    >>> logger = AILoggingService(session=db)
    >>>
    >>> # Context manager for automatic timing
    >>> with logger.log_interaction(
    ...     processing_id="abc123",
    ...     step_name="TRANSLATION",
    ...     document_type="ARZTBRIEF"
    ... ) as ctx:
    ...     # Your AI processing here
    ...     input_prompt = "Translate this medical report..."
    ...     ctx['set_input'](input_prompt)
    ...
    ...     translation = ai_client.translate(input_prompt)
    ...     ctx['set_output'](translation)
    >>>
    >>> # Or use specific loggers
    >>> logger.log_classification(
    ...     processing_id="abc123",
    ...     input_text="Patient shows symptoms...",
    ...     document_type="ARZTBRIEF",
    ...     confidence=0.95,
    ...     method="llm_classifier"
    ... )

**Privacy Considerations**:
    - Production: Consider disabling text logging for medical documents
    - Development: Essential for debugging but requires secure environment
    - Compliance: Check with legal team before deploying with text logging

Note:
    This service complements (not replaces) AICostTracker. Use both for
    complete observability: text logging for debugging + cost tracking for budget.
"""

from contextlib import contextmanager
from datetime import datetime
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.database.unified_models import AILogInteractionDB
from app.repositories.ai_log_interaction_repository import AILogInteractionRepository

logger = logging.getLogger(__name__)

class AILoggingService:
    """Comprehensive AI interaction logging service with full text capture.

    ⚠️ **PRIVACY WARNING**: Logs complete input/output text to database.
    Not GDPR-compliant for medical PII without additional security measures.

    Provides multiple interfaces for logging AI interactions:
    - Generic context manager (log_interaction)
    - Internal method (_log_ai_interaction)
    - Pipeline-specific helpers (log_classification, log_translation, etc.)

    Automatically captures processing times, errors, and metadata for complete
    audit trails and debugging capabilities.

    Attributes:
        session (Session): SQLAlchemy database session for writing logs
        log_repository (AILogInteractionRepository): Repository for log queries

    Example:
        >>> logger = AILoggingService(session=db)
        >>>
        >>> # Context manager automatically times and handles errors
        >>> with logger.log_interaction("doc123", "TRANSLATION") as ctx:
        ...     ctx['set_input']("Diagnose: Diabetes mellitus...")
        ...     result = translate_text(...)
        ...     ctx['set_output'](result)
        >>>
        >>> # Or use specialized methods
        >>> logger.log_classification(
        ...     processing_id="doc123",
        ...     input_text="Medical report text...",
        ...     document_type="ARZTBRIEF",
        ...     confidence=0.95,
        ...     method="llm"
        ... )

    Note:
        **Session Management**: Commits after each log write. Rollback on error.
        Caller responsible for session lifecycle (creation/close).

        **Error Handling**: Database errors logged but don't propagate.
        Logging failures shouldn't disrupt document processing.

        **Performance**: Direct DB writes on each call. Consider async batching
        for high-throughput scenarios.
    """

    def __init__(
        self,
        session: Session,
        log_repository: AILogInteractionRepository | None = None
    ):
        """Initialize logging service with database session.

        Args:
            session: SQLAlchemy database session for writing to ai_interaction_logs
            log_repository: Optional repository for log queries (for DI)
        """
        self.session = session
        self.log_repository = log_repository or AILogInteractionRepository(session)

    def _log_ai_interaction(
        self,
        processing_id: str,
        step_name: str,
        input_text: str | None = None,
        output_text: str | None = None,
        processing_time_ms: int | None = None,
        status: str = "success",
        error_message: str | None = None,
        document_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None,
        confidence_score: float | None = None,
        model_name: str | None = None,
        input_metadata: dict[str, Any] | None = None,
        output_metadata: dict[str, Any] | None = None
    ):
        """Log AI interaction to database"""
        try:
            log_entry = AILogInteractionDB(
                processing_id=processing_id,
                step_name=step_name,
                input_text=input_text,
                output_text=output_text,
                processing_time_ms=processing_time_ms or 0,
                status=status,
                error_message=error_message,
                document_type=document_type,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                confidence_score=confidence_score,
                model_name=model_name,
                input_metadata=input_metadata,
                output_metadata=output_metadata,
                created_at=datetime.now()
            )

            self.session.add(log_entry)
            self.session.commit()

        except Exception as e:
            logger.error(f"Failed to log AI interaction: {e}")
            self.session.rollback()

    @contextmanager
    def log_interaction(
        self,
        processing_id: str,
        step_name: str,
        document_type: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None
    ):
        """Context manager for automatic AI interaction logging with timing.

        Wraps AI processing code to automatically capture input/output, measure
        execution time, and handle errors. Logs to database on context exit
        (both success and failure paths). Ideal for instrumentation without
        manual timing/error handling code.

        Args:
            processing_id: Unique document processing identifier (UUID)
            step_name: Pipeline step being logged (e.g., "TRANSLATION", "CLASSIFICATION")
            document_type: Document classification if known (e.g., "ARZTBRIEF")
            user_id: User identifier for multi-tenant tracking (optional)
            session_id: Session identifier for request correlation (optional)
            request_id: Request identifier for distributed tracing (optional)

        Yields:
            Dict[str, Callable]: Context dict with setter functions:
                - 'set_input': Lambda to set input text → ctx['set_input'](text)
                - 'set_output': Lambda to set output text → ctx['set_output'](text)
                - 'set_error': Lambda to set error message → ctx['set_error'](error)

        Example:
            >>> logger = AILoggingService(session=db)
            >>>
            >>> # Basic usage with input/output capture
            >>> with logger.log_interaction("doc123", "TRANSLATION") as ctx:
            ...     input_prompt = "Translate this: Diagnose Diabetes"
            ...     ctx['set_input'](input_prompt)
            ...
            ...     # Call AI service
            ...     translation = ai_client.translate(input_prompt)
            ...
            ...     ctx['set_output'](translation)
            >>> # Automatic timing: context exit logs processing_time_ms
            >>>
            >>> # Error handling automatically captured
            >>> with logger.log_interaction("doc123", "CLASSIFICATION") as ctx:
            ...     ctx['set_input']("Medical report...")
            ...     result = classifier.classify()  # May raise exception
            ...     ctx['set_output'](result)
            >>> # If exception raised: status="error", error_message logged
            >>>
            >>> # Manual error reporting
            >>> with logger.log_interaction("doc123", "VALIDATION") as ctx:
            ...     try:
            ...         validate_document()
            ...     except ValidationError as e:
            ...         ctx['set_error'](str(e))

        Note:
            **Automatic Features**:
            - Timing: Calculates processing_time_ms from context entry to exit
            - Error capture: Exceptions set status="error" with exception message
            - Database commit: Writes log entry on __exit__ (finally block)

            **Context Variables**:
            Uses instance attributes (_input_text, _output_text, _error_message)
            to pass data from yield to finally block. Thread-unsafe if sharing
            AILoggingService instances across threads.

            **Status Determination**:
            - "success": No error_message set and no exception raised
            - "error": Exception raised OR ctx['set_error']() called

            **Performance Overhead**:
            ~1-5ms per logged interaction (DB write + timing). Negligible for
            AI calls (typically 100ms-10s processing time).

            **Privacy Warning**:
            ⚠️ Logs full input/output text to database. Ensure compliance.
        """
        start_time = time.time()
        input_text = None
        output_text = None
        error_message = None
        status = "success"

        try:
            yield {
                "set_input": lambda text: setattr(self, '_input_text', text),
                "set_output": lambda text: setattr(self, '_output_text', text),
                "set_error": lambda error: setattr(self, '_error_message', error)
            }

            # Get values from context
            input_text = getattr(self, '_input_text', None)
            output_text = getattr(self, '_output_text', None)
            error_message = getattr(self, '_error_message', None)

            if error_message:
                status = "error"

        except Exception as e:
            status = "error"
            error_message = str(e)
            logger.error(f"Error in AI interaction logging: {e}")

        finally:
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Log to database
            self._log_ai_interaction(
                processing_id=processing_id,
                step_name=step_name,
                input_text=input_text,
                output_text=output_text,
                processing_time_ms=processing_time_ms,
                status=status,
                error_message=error_message,
                document_type=document_type,
                user_id=user_id,
                session_id=session_id,
                request_id=request_id
            )

    def log_medical_validation(
        self,
        processing_id: str,
        input_text: str,
        is_medical: bool,
        confidence: float,
        method: str,
        document_type: str | None = None
    ):
        """Log medical validation step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="MEDICAL_VALIDATION",
            input_text=input_text,
            output_text=f"Medical: {is_medical}, Confidence: {confidence:.2%}, Method: {method}",
            confidence_score=confidence,
            status="success" if is_medical else "non_medical",
            document_type=document_type,
            input_metadata={"method": method},
            output_metadata={"is_medical": is_medical, "confidence": confidence}
        )

    def log_classification(
        self,
        processing_id: str,
        input_text: str,
        document_type: str,
        confidence: float,
        method: str
    ):
        """Log document classification step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="CLASSIFICATION",
            input_text=input_text,
            output_text=f"Classified as: {document_type}",
            confidence_score=confidence,
            status="success",
            document_type=document_type,
            input_metadata={"method": method},
            output_metadata={"document_type": document_type, "confidence": confidence}
        )

    def log_translation(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        confidence: float,
        model_name: str,
        document_type: str | None = None
    ):
        """Log translation step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="TRANSLATION",
            input_text=input_text,
            output_text=output_text,
            confidence_score=confidence,
            model_name=model_name,
            status="success",
            document_type=document_type,
            output_metadata={"confidence": confidence, "model": model_name}
        )

    def log_quality_check(
        self,
        processing_id: str,
        step_name: str,
        input_text: str,
        output_text: str,
        changes_made: int,
        document_type: str | None = None
    ):
        """Log quality check step (fact check, grammar check, etc.)"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name=step_name,
            input_text=input_text,
            output_text=output_text,
            status="success",
            document_type=document_type,
            output_metadata={"changes_made": changes_made}
        )

    def log_fact_check(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        document_type: str,
        status: str,
        details: dict[str, Any] | None = None
    ):
        """Log fact check step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="FACT_CHECK",
            input_text=input_text,
            output_text=output_text,
            status=status,
            document_type=document_type,
            output_metadata={"details": details}
        )

    def log_grammar_check(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        document_type: str,
        status: str,
        details: dict[str, Any] | None = None
    ):
        """Log grammar check step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="GRAMMAR_CHECK",
            input_text=input_text,
            output_text=output_text,
            status=status,
            document_type=document_type,
            output_metadata={"details": details}
        )

    def log_language_translation(
        self,
        processing_id: str,
        input_text: str,
        output_text: str,
        target_language: str,
        confidence: float
    ):
        """Log language translation step"""
        self._log_ai_interaction(
            processing_id=processing_id,
            step_name="LANGUAGE_TRANSLATION",
            input_text=input_text,
            output_text=output_text,
            confidence_score=confidence,
            status="success",
            output_metadata={"target_language": target_language, "confidence": confidence}
        )

    def get_processing_logs(self, processing_id: str) -> list:
        """Get all logs for a processing ID"""
        try:
            logs = self.log_repository.get_by_processing_id(processing_id)
            return [log.__dict__ for log in logs]
        except Exception as e:
            logger.error(f"Failed to get processing logs: {e}")
            return []

    def get_analytics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        document_type: str | None = None
    ) -> dict[str, Any]:
        """Generate comprehensive analytics from AI interaction logs.

        Aggregates log data to provide insights into system health, success rates,
        and pipeline step distribution. Useful for dashboards, monitoring, and
        operational reports.

        Args:
            start_date: ISO format datetime string for range start (e.g., "2025-01-15T00:00:00")
            end_date: ISO format datetime string for range end (e.g., "2025-01-31T23:59:59")
            document_type: Filter to specific document type (e.g., "ARZTBRIEF")

        Returns:
            Dict[str, Any]: Analytics summary with keys:
                - total_interactions (int): Total log entries
                - success_count (int): Successful interactions (status="success")
                - error_count (int): Failed interactions (status="error")
                - success_rate (float): Proportion of successful interactions (0.0-1.0)
                - step_counts (dict): Count per pipeline step {step_name: count}
                - date_range (dict): Applied date filter {"start": str, "end": str}
                - error (str): Error message if query failed (only present on error)

        Example:
            >>> logger = AILoggingService(session=db)
            >>>
            >>> # Get all-time analytics
            >>> stats = logger.get_analytics()
            >>> print(f"Success rate: {stats['success_rate']:.1%}")
            Success rate: 94.5%
            >>> print(f"Total interactions: {stats['total_interactions']}")
            Total interactions: 12,345
            >>>
            >>> # Analyze specific date range
            >>> stats = logger.get_analytics(
            ...     start_date="2025-01-01T00:00:00",
            ...     end_date="2025-01-31T23:59:59"
            ... )
            >>>
            >>> # Break down by pipeline step
            >>> for step, count in stats['step_counts'].items():
            ...     print(f"{step}: {count} calls")
            TRANSLATION: 5,432 calls
            CLASSIFICATION: 2,876 calls
            FACT_CHECK: 1,987 calls
            >>>
            >>> # Filter by document type
            >>> arztbrief_stats = logger.get_analytics(document_type="ARZTBRIEF")
            >>> print(f"Arztbrief success rate: {arztbrief_stats['success_rate']:.1%}")

        Note:
            **Date Format**:
            ISO 8601 format required: "YYYY-MM-DDTHH:MM:SS"
            Invalid formats raise ValueError from datetime.fromisoformat()

            **Filter Combination**:
            Multiple filters ANDed together:
            - start_date + end_date = date range
            - document_type = specific doc class
            - All three = date range for specific doc type

            **Success Rate Calculation**:
            success_rate = success_count / total_interactions
            Returns 0 if total_interactions == 0 (no divide-by-zero)

            **Error Handling**:
            Database/parsing errors return dict with zeros + "error" key.
            Never propagates exceptions - safe for dashboards.

            **Performance**:
            Loads all matching logs into memory for Python aggregation.
            Consider date filtering for large datasets (>100K logs).
            No database aggregation - suitable for reports, not real-time queries.
        """
        try:
            # Convert date strings to datetime objects
            start_dt = datetime.fromisoformat(start_date) if start_date else None
            end_dt = datetime.fromisoformat(end_date) if end_date else None

            # Get filtered logs using repository
            logs = self.log_repository.get_filtered(
                start_date=start_dt,
                end_date=end_dt,
                document_type=document_type
            )

            # Basic analytics
            total_interactions = len(logs)
            success_count = len([log for log in logs if log.status == "success"])
            error_count = len([log for log in logs if log.status == "error"])

            # Group by step
            step_counts = {}
            for log in logs:
                step = log.step_name
                step_counts[step] = step_counts.get(step, 0) + 1

            return {
                "total_interactions": total_interactions,
                "success_count": success_count,
                "error_count": error_count,
                "success_rate": success_count / total_interactions if total_interactions > 0 else 0,
                "step_counts": step_counts,
                "date_range": {
                    "start": start_date,
                    "end": end_date
                }
            }
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {
                "total_interactions": 0,
                "success_count": 0,
                "error_count": 0,
                "success_rate": 0,
                "step_counts": {},
                "error": str(e)
            }
