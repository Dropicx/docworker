"""AI Cost Tracker Service for token usage and cost monitoring.

Lightweight, privacy-focused service that tracks AI API token usage and calculates
costs WITHOUT storing input/output text content. Designed for GDPR compliance
while maintaining comprehensive cost analytics for budget management.

**Key Features**:
    - Token tracking (input/output/total counts)
    - Automated cost calculation (per-call and aggregated)
    - Dynamic pricing from database (cached for performance)
    - Model and pipeline step breakdowns
    - Zero PII storage (no text content logged)

**Privacy Design**:
    Only logs metadata (tokens, costs, timestamps, model names) - never stores
    actual medical document content or translations. Enables cost monitoring
    while maintaining patient privacy.

**Pricing Management**:
    Fetches model pricing from available_models table (price per 1M tokens).
    Caches pricing in-memory to avoid repeated database queries. Falls back to
    Llama 3.3 70B pricing if model not found.

**Database Schema**:
    Writes to AILogInteractionDB (ai_interaction_logs table) with fields:
    - processing_id, step_name, model_provider, model_name
    - input_tokens, output_tokens, total_tokens
    - input_cost_usd, output_cost_usd, total_cost_usd
    - confidence_score, processing_time_seconds, document_type
    - created_at, log_metadata

**Usage**:
    >>> from app.database.connection import get_db_session
    >>> db = next(get_db_session())
    >>> tracker = AICostTracker(session=db)
    >>>
    >>> # Log AI call after translation
    >>> tracker.log_ai_call(
    ...     processing_id="abc123",
    ...     step_name="TRANSLATION",
    ...     input_tokens=1500,
    ...     output_tokens=2000,
    ...     model_name="Meta-Llama-3.3-70B-Instruct",
    ...     processing_time_seconds=45.2
    ... )
    >>>
    >>> # Get total costs for a document
    >>> costs = tracker.get_total_cost(processing_id="abc123")
    >>> print(f"Total cost: ${costs['total_cost_usd']:.4f}")

Example Cost Calculation:
    Model: Llama 3.3 70B (input: $0.54/1M, output: $0.81/1M)
    Input: 1,500 tokens → $0.00081
    Output: 2,000 tokens → $0.00162
    Total: $0.00243
"""

from datetime import datetime
import logging


from sqlalchemy.orm import Session

from app.database.unified_models import AILogInteractionDB
from app.repositories.ai_log_interaction_repository import AILogInteractionRepository
from app.repositories.available_model_repository import AvailableModelRepository

logger = logging.getLogger(__name__)


class AICostTracker:
    """Lightweight AI cost tracking service with privacy-first design.

    Provides comprehensive token usage and cost analytics for AI API calls
    without storing sensitive text content. Designed for production budget
    monitoring and GDPR-compliant cost attribution across pipeline steps.

    **Core Capabilities**:
        - Per-call logging: Track individual AI API invocations
        - Automated costing: Calculate costs from token counts + dynamic pricing
        - Aggregation: Total costs by processing ID, date range, model, or step
        - Breakdown analysis: Detailed cost attribution for optimization

    **Privacy Guarantee**:
        NEVER stores input prompts or output completions - only token counts,
        costs, and metadata. Safe for medical document processing under GDPR.

    **Performance Optimization**:
        Caches model pricing in-memory (_pricing_cache dict) to minimize
        database queries. Cache persists for life of AICostTracker instance.

    Attributes:
        session (Session): SQLAlchemy database session for queries and inserts
        model_repository (AvailableModelRepository): Repository for model pricing queries
        log_repository (AILogInteractionRepository): Repository for log queries
        _pricing_cache (dict): In-memory cache of model pricing (model_name → pricing dict)

    Example:
        >>> # Initialize with database session
        >>> tracker = AICostTracker(session=db)
        >>>
        >>> # Log translation call
        >>> tracker.log_ai_call(
        ...     processing_id="doc_123",
        ...     step_name="TRANSLATION",
        ...     input_tokens=800,
        ...     output_tokens=1200,
        ...     model_name="Meta-Llama-3.3-70B-Instruct",
        ...     processing_time_seconds=32.5,
        ...     confidence_score=0.95,
        ...     document_type="ARZTBRIEF"
        ... )
        >>>
        >>> # Get costs for entire document processing
        >>> costs = tracker.get_total_cost(processing_id="doc_123")
        >>> print(f"Total: ${costs['total_cost_usd']:.4f} across {costs['total_calls']} calls")
        >>>
        >>> # Analyze spending by model
        >>> breakdown = tracker.get_cost_breakdown()
        >>> for model, data in breakdown['by_model'].items():
        ...     print(f"{model}: ${data['cost_usd']:.4f} ({data['calls']} calls)")

    Note:
        **Session Management**:
        Caller responsible for session lifecycle (creation, commit, close).
        Methods commit after successful operations but don't close session.

        **Error Handling**:
        Database errors logged and return None/empty dicts to avoid disrupting
        document processing. Cost tracking failures shouldn't block pipelines.

        **Pricing Updates**:
        Pricing cache cleared on instance recreation. For long-lived instances,
        consider periodic recreation to pick up pricing changes.
    """

    def __init__(
        self,
        session: Session,
        model_repository: AvailableModelRepository | None = None,
        log_repository: AILogInteractionRepository | None = None,
    ):
        """Initialize cost tracker with database session.

        Args:
            session: SQLAlchemy database session for accessing available_models
                and writing to ai_interaction_logs table
            model_repository: Optional repository for model pricing (for DI)
            log_repository: Optional repository for log queries (for DI)
        """
        self.session = session
        self.model_repository = model_repository or AvailableModelRepository(session)
        self.log_repository = log_repository or AILogInteractionRepository(session)
        self._pricing_cache = {}  # Cache pricing to avoid repeated DB queries

    def _get_model_pricing(self, model_name: str) -> dict[str, float]:
        """Fetch model pricing from database with caching for performance.

        Queries available_models table for per-1M-token pricing, converts to
        per-1K rates, and caches result. Falls back to Llama 3.3 70B default
        pricing if model not found or pricing unavailable.

        Args:
            model_name: Model identifier (e.g., "Meta-Llama-3.3-70B-Instruct")

        Returns:
            dict[str, float]: Pricing per 1K tokens with keys:
                - "input": Cost per 1K input tokens (USD)
                - "output": Cost per 1K output tokens (USD)

        Example:
            >>> tracker = AICostTracker(session=db)
            >>> pricing = tracker._get_model_pricing("Meta-Llama-3.3-70B-Instruct")
            >>> print(pricing)
            {'input': 0.00054, 'output': 0.00081}
            >>> # $0.54 per 1M input tokens / 1000 = $0.00054 per 1K
            >>> # $0.81 per 1M output tokens / 1000 = $0.00081 per 1K

        Note:
            **Caching Strategy**:
            - First call: Queries database, caches result
            - Subsequent calls: Returns cached value (no DB hit)
            - Cache lifetime: Until AICostTracker instance destroyed

            **Fallback Pricing** (Llama 3.3 70B rates):
            - Input: $0.00054 per 1K tokens ($0.54 per 1M)
            - Output: $0.00081 per 1K tokens ($0.81 per 1M)
            - Used when: Model not in database OR pricing fields NULL

            **Database Query**:
            Queries: available_models.price_input_per_1m_tokens,
                    available_models.price_output_per_1m_tokens
            Filter: available_models.name == model_name

            **Error Handling**:
            Any database error returns default pricing with error log.
            Never propagates exceptions to avoid blocking cost logging.
        """
        # Check cache first
        if model_name in self._pricing_cache:
            return self._pricing_cache[model_name]

        try:
            # Query database for model pricing using repository
            model = self.model_repository.get_by_name(model_name)

            if model and model.price_input_per_1m_tokens and model.price_output_per_1m_tokens:
                # Convert from per 1M tokens to per 1K tokens
                pricing = {
                    "input": model.price_input_per_1m_tokens / 1000,
                    "output": model.price_output_per_1m_tokens / 1000,
                }
                # Cache for future use
                self._pricing_cache[model_name] = pricing
                return pricing
            logger.warning(f"No pricing found for model '{model_name}' in database, using default")
            # Default to Llama 3.3 70B pricing if not found
            default_pricing = {"input": 0.00054, "output": 0.00081}
            self._pricing_cache[model_name] = default_pricing
            return default_pricing

        except Exception as e:
            logger.error(f"Error fetching model pricing: {e}")
            # Return default pricing on error
            return {"input": 0.00054, "output": 0.00081}

    def log_ai_call(
        self,
        processing_id: str,
        step_name: str,
        input_tokens: int,
        output_tokens: int,
        model_provider: str = "OVH",
        model_name: str = "Meta-Llama-3.3-70B-Instruct",
        processing_time_seconds: float | None = None,
        confidence_score: float | None = None,
        document_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Log AI API call with automatic cost calculation and database persistence.

        Primary method for recording token usage and costs after each AI invocation.
        Calculates costs automatically from token counts using dynamic pricing,
        then persists to database. No text content stored - privacy compliant.

        Args:
            processing_id: Unique document processing identifier (UUID)
            step_name: Pipeline step name (e.g., "CLASSIFICATION", "TRANSLATION",
                "FACT_CHECK", "GRAMMAR_CHECK", "PII_PREPROCESSING")
            input_tokens: Count of tokens in prompt sent to AI model
            output_tokens: Count of tokens in completion received from AI model
            model_provider: AI service provider name (default: "OVH")
            model_name: Specific model identifier (default: "Meta-Llama-3.3-70B-Instruct")
            processing_time_seconds: API call duration in seconds (for performance tracking)
            confidence_score: Model's confidence score (0.0-1.0) if applicable
            document_type: Document classification (e.g., "ARZTBRIEF", "BEFUNDBERICHT")
            metadata: Additional context (temperature, max_tokens, etc.) stored as JSON

        Returns:
            AILogInteractionDB | None: Created database record, or None if logging failed

        Example:
            >>> tracker = AICostTracker(session=db)
            >>> # After translation API call
            >>> log_entry = tracker.log_ai_call(
            ...     processing_id="a1b2c3d4",
            ...     step_name="TRANSLATION",
            ...     input_tokens=1234,
            ...     output_tokens=1876,
            ...     model_name="Meta-Llama-3.3-70B-Instruct",
            ...     processing_time_seconds=42.5,
            ...     confidence_score=0.94,
            ...     document_type="ARZTBRIEF",
            ...     metadata={"temperature": 0.7, "max_tokens": 4000}
            ... )
            >>> if log_entry:
            ...     print(f"Logged ${log_entry.total_cost_usd:.6f}")
            Logged $0.002187

        Note:
            **Cost Calculation Process**:
            1. Fetch pricing via _get_model_pricing() (cached)
            2. Calculate: input_cost = (input_tokens / 1000) * input_price
            3. Calculate: output_cost = (output_tokens / 1000) * output_price
            4. Total: total_cost = input_cost + output_cost

            **Database Commit**:
            Method commits transaction on success. Rollback on error.
            Caller doesn't need to commit for cost logging.

            **Error Handling**:
            - Database errors: Logged, rollback, return None
            - Never propagates exceptions (non-critical operation)
            - Processing continues even if cost logging fails

            **Privacy Compliance**:
            NO text content stored - only token counts and metadata.
            Safe for GDPR/HIPAA medical document processing.

            **Logging Output**:
            Info log: "💰 AI Call Logged | {step} | {tokens} tokens | ${cost} | {provider}/{model}"
        """
        try:
            # Calculate total tokens
            total_tokens = input_tokens + output_tokens

            # Get pricing from database
            pricing = self._get_model_pricing(model_name)

            # Calculate costs
            input_cost = (input_tokens / 1000) * pricing["input"]
            output_cost = (output_tokens / 1000) * pricing["output"]
            total_cost = input_cost + output_cost

            # Create log entry (NO TEXT CONTENT!)
            log_entry = AILogInteractionDB(
                processing_id=processing_id,
                step_name=step_name,
                # Token tracking
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                # Cost tracking
                input_cost_usd=input_cost,
                output_cost_usd=output_cost,
                total_cost_usd=total_cost,
                # Model info
                model_provider=model_provider,
                model_name=model_name,
                # Metrics
                confidence_score=confidence_score,
                processing_time_seconds=processing_time_seconds,
                # Context
                document_type=document_type,
                created_at=datetime.now(),
                log_metadata=metadata,
            )

            self.session.add(log_entry)
            self.session.commit()

            logger.info(
                f"💰 AI Call Logged | {step_name} | "
                f"{total_tokens} tokens | ${total_cost:.6f} | "
                f"{model_provider}/{model_name}"
            )

            return log_entry

        except Exception as e:
            logger.error(f"Failed to log AI cost: {e}")
            self.session.rollback()
            return None

    def get_total_cost(
        self,
        processing_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Calculate total costs and token usage with flexible filtering.

        Aggregates AI interaction logs to provide summary statistics for cost
        tracking, budget monitoring, and usage analysis. Supports filtering by
        document, date range, or combination.

        Args:
            processing_id: Filter to specific document processing (default: all documents)
            start_date: Filter logs created on/after this datetime (inclusive, default: no limit)
            end_date: Filter logs created on/before this datetime (inclusive, default: no limit)

        Returns:
            dict[str, Any]: Aggregated statistics with keys:
                - total_cost_usd (float): Sum of all costs (rounded to 6 decimals)
                - total_tokens (int): Sum of all token counts
                - total_calls (int): Count of AI API invocations
                - average_cost_per_call (float): Mean cost per call (0 if no calls)
                - average_tokens_per_call (float): Mean tokens per call (0 if no calls)
                - error (str): Error message if query failed (only present on error)

        Example:
            >>> tracker = AICostTracker(session=db)
            >>> # Get costs for specific document
            >>> doc_costs = tracker.get_total_cost(processing_id="abc123")
            >>> print(f"Document cost: ${doc_costs['total_cost_usd']:.4f}")
            Document cost: $0.0142
            >>> print(f"API calls: {doc_costs['total_calls']}, Avg: ${doc_costs['average_cost_per_call']:.6f}")
            API calls: 5, Avg: $0.002840
            >>>
            >>> # Get costs for date range
            >>> from datetime import datetime
            >>> today = datetime.now()
            >>> week_ago = today - timedelta(days=7)
            >>> weekly_costs = tracker.get_total_cost(start_date=week_ago, end_date=today)
            >>> print(f"This week: ${weekly_costs['total_cost_usd']:.2f} ({weekly_costs['total_tokens']:,} tokens)")
            This week: $12.45 (23,456,789 tokens)

        Note:
            **Filter Combination**:
            Multiple filters are ANDed together. For example:
            - processing_id + start_date → Specific doc, within date range
            - start_date + end_date → All docs, within date window
            - No filters → All logs, all time

            **Cost Precision**:
            Costs rounded to 6 decimal places ($0.000001 precision).
            Sufficient for micro-transaction tracking.

            **Error Handling**:
            Database errors return dict with zeros + "error" key.
            Never propagates exceptions - safe for production dashboards.

            **Performance**:
            Query performance depends on filters and log volume:
            - With processing_id: Fast (indexed column)
            - Date range only: Slower on large tables (add index on created_at)
            - No filters: Full table scan (use with caution on large datasets)
        """
        try:
            # Query logs using repository with filtering
            logs = self.log_repository.get_filtered(
                processing_id=processing_id, start_date=start_date, end_date=end_date
            )

            total_cost = sum(log.total_cost_usd or 0 for log in logs)
            total_tokens = sum(log.total_tokens or 0 for log in logs)
            total_calls = len(logs)

            return {
                "total_cost_usd": round(total_cost, 6),
                "total_tokens": total_tokens,
                "total_calls": total_calls,
                "average_cost_per_call": (
                    round(total_cost / total_calls, 6) if total_calls > 0 else 0
                ),
                "average_tokens_per_call": (
                    round(total_tokens / total_calls, 0) if total_calls > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get total cost: {e}")
            return {
                "total_cost_usd": 0,
                "total_tokens": 0,
                "total_calls": 0,
                "error": str(e),
            }

    def get_cost_breakdown(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict[str, Any]:
        """Generate detailed cost breakdown for optimization and analysis.

        Provides two-dimensional cost analysis: by AI model and by pipeline step.
        Useful for identifying cost hotspots, comparing model efficiency, and
        optimizing pipeline configuration.

        Args:
            start_date: Filter logs created on/after this datetime (inclusive, default: no limit)
            end_date: Filter logs created on/before this datetime (inclusive, default: no limit)

        Returns:
            dict[str, Any]: Breakdown analysis with keys:
                - by_model (dict): Model-level aggregation, keyed by model_name:
                    * calls (int): API invocations for this model
                    * tokens (int): Total tokens consumed by this model
                    * cost_usd (float): Total cost for this model (rounded to 6 decimals)
                    * provider (str): Provider name (e.g., "OVH")
                - by_step (dict): Pipeline step aggregation, keyed by step_name:
                    * calls (int): API invocations for this step
                    * tokens (int): Total tokens consumed by this step
                    * cost_usd (float): Total cost for this step (rounded to 6 decimals)
                - error (str): Error message if query failed (only present on error)

        Example:
            >>> tracker = AICostTracker(session=db)
            >>> breakdown = tracker.get_cost_breakdown()
            >>>
            >>> # Analyze by model
            >>> print("Cost by model:")
            >>> for model, data in breakdown['by_model'].items():
            ...     print(f"  {model}: ${data['cost_usd']:.4f} ({data['calls']} calls, {data['tokens']:,} tokens)")
            Cost by model:
              Meta-Llama-3.3-70B-Instruct: $45.23 (1,234 calls, 78,456,789 tokens)
              Mistral-Nemo-Instruct-2407: $12.45 (567 calls, 23,456,789 tokens)
            >>>
            >>> # Analyze by pipeline step
            >>> print("\nCost by step:")
            >>> for step, data in breakdown['by_step'].items():
            ...     print(f"  {step}: ${data['cost_usd']:.4f} ({data['calls']} calls)")
            Cost by step:
              TRANSLATION: $34.56 (890 calls)
              CLASSIFICATION: $8.90 (456 calls)
              FACT_CHECK: $14.22 (455 calls)
            >>>
            >>> # Identify most expensive step
            >>> most_expensive = max(breakdown['by_step'].items(), key=lambda x: x[1]['cost_usd'])
            >>> print(f"Costliest step: {most_expensive[0]} at ${most_expensive[1]['cost_usd']:.2f}")
            Costliest step: TRANSLATION at $34.56

        Note:
            **Use Cases**:
            - Cost optimization: Identify expensive models/steps
            - Model comparison: Compare efficiency across models
            - Budget allocation: Understand cost distribution
            - Pipeline tuning: Find optimization opportunities

            **Date Filtering**:
            Same behavior as get_total_cost() - inclusive date range.
            No filters = all-time breakdown.

            **Model Identification**:
            Groups by model_name field. "Unknown" used if model_name NULL.

            **Error Handling**:
            Database errors return empty dicts + "error" key.
            Never propagates exceptions - safe for dashboards.

            **Performance**:
            Processes all logs in Python (not database aggregation).
            Consider date filtering for large datasets.
            Typical: <1s for 10K logs, ~10s for 1M logs.
        """
        try:
            # Query logs using repository with date filtering
            logs = self.log_repository.get_by_date_range(start_date=start_date, end_date=end_date)

            # Group by model
            by_model = {}
            for log in logs:
                model = log.model_name or "Unknown"
                if model not in by_model:
                    by_model[model] = {
                        "calls": 0,
                        "tokens": 0,
                        "cost_usd": 0,
                        "provider": log.model_provider,
                    }
                by_model[model]["calls"] += 1
                by_model[model]["tokens"] += log.total_tokens or 0
                by_model[model]["cost_usd"] += log.total_cost_usd or 0

            # Group by step
            by_step = {}
            for log in logs:
                step = log.step_name
                if step not in by_step:
                    by_step[step] = {"calls": 0, "tokens": 0, "cost_usd": 0}
                by_step[step]["calls"] += 1
                by_step[step]["tokens"] += log.total_tokens or 0
                by_step[step]["cost_usd"] += log.total_cost_usd or 0

            # Round costs
            for model_data in by_model.values():
                model_data["cost_usd"] = round(model_data["cost_usd"], 6)

            for step_data in by_step.values():
                step_data["cost_usd"] = round(step_data["cost_usd"], 6)

            return {"by_model": by_model, "by_step": by_step}

        except Exception as e:
            logger.error(f"Failed to get cost breakdown: {e}")
            return {"by_model": {}, "by_step": {}, "error": str(e)}
