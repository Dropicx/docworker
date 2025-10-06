"""
AI Cost Tracker Service

Lightweight service for tracking AI token usage and costs.
Does NOT store input/output text - only tokens and costs.
Fetches pricing dynamically from available_models table.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.unified_models import AILogInteractionDB
from app.database.modular_pipeline_models import AvailableModelDB

logger = logging.getLogger(__name__)


class AICostTracker:
    """
    Lightweight AI cost tracking service.
    Tracks tokens and costs without storing text content.
    Fetches pricing from available_models table.
    """

    def __init__(self, session: Session):
        self.session = session
        self._pricing_cache = {}  # Cache pricing to avoid repeated DB queries

    def _get_model_pricing(self, model_name: str) -> Dict[str, float]:
        """
        Get pricing for a model from available_models table.
        Uses cache to avoid repeated DB queries.

        Returns:
            Dict with 'input' and 'output' prices per 1K tokens (converted from per 1M)
        """
        # Check cache first
        if model_name in self._pricing_cache:
            return self._pricing_cache[model_name]

        try:
            # Query database for model pricing
            model = self.session.query(AvailableModelDB).filter(
                AvailableModelDB.name == model_name
            ).first()

            if model and model.price_input_per_1m_tokens and model.price_output_per_1m_tokens:
                # Convert from per 1M tokens to per 1K tokens
                pricing = {
                    "input": model.price_input_per_1m_tokens / 1000,
                    "output": model.price_output_per_1m_tokens / 1000,
                }
                # Cache for future use
                self._pricing_cache[model_name] = pricing
                return pricing
            else:
                logger.warning(
                    f"No pricing found for model '{model_name}' in database, using default"
                )
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
        processing_time_seconds: Optional[float] = None,
        confidence_score: Optional[float] = None,
        document_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log AI call with automatic cost calculation.
        Pricing fetched dynamically from available_models table.

        Args:
            processing_id: Unique processing ID
            step_name: Pipeline step name (e.g., "CLASSIFICATION", "TRANSLATION")
            input_tokens: Number of input tokens sent to AI
            output_tokens: Number of output tokens received from AI
            model_provider: AI provider (default: "OVH")
            model_name: Specific model used
            processing_time_seconds: Time taken for API call
            confidence_score: Confidence score if applicable
            document_type: Document type being processed
            metadata: Additional metadata (temperature, max_tokens, etc.)
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
        processing_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get total costs and token usage.

        Args:
            processing_id: Filter by specific processing ID
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Dict with total_cost_usd, total_tokens, total_calls
        """
        try:
            query = self.session.query(AILogInteractionDB)

            if processing_id:
                query = query.filter(AILogInteractionDB.processing_id == processing_id)
            if start_date:
                query = query.filter(AILogInteractionDB.created_at >= start_date)
            if end_date:
                query = query.filter(AILogInteractionDB.created_at <= end_date)

            logs = query.all()

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
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed cost breakdown by model and step.

        Returns:
            Dict with breakdown by model and by step
        """
        try:
            query = self.session.query(AILogInteractionDB)

            if start_date:
                query = query.filter(AILogInteractionDB.created_at >= start_date)
            if end_date:
                query = query.filter(AILogInteractionDB.created_at <= end_date)

            logs = query.all()

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
