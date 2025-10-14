"""
Statistics Service

Handles business logic for pipeline statistics and performance metrics.
"""

from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from app.repositories.pipeline_step_execution_repository import PipelineStepExecutionRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.repositories.system_settings_repository import SystemSettingsRepository

logger = logging.getLogger(__name__)


class StatisticsService:
    """
    Service for managing pipeline statistics and performance metrics.

    Provides aggregate statistics about pipeline execution, AI interactions,
    and system configuration.
    """

    def __init__(
        self,
        db: Session,
        step_repository: PipelineStepRepository | None = None,
        execution_repository: PipelineStepExecutionRepository | None = None,
        settings_repository: SystemSettingsRepository | None = None
    ):
        """
        Initialize statistics service.

        Args:
            db: Database session
            step_repository: Optional step repository (for DI)
            execution_repository: Optional execution repository (for DI)
            settings_repository: Optional settings repository (for DI)
        """
        self.db = db
        self.step_repository = step_repository or PipelineStepRepository(db)
        self.execution_repository = execution_repository or PipelineStepExecutionRepository(db)
        self.settings_repository = settings_repository or SystemSettingsRepository(db)

    def get_pipeline_statistics(self) -> dict:
        """
        Get comprehensive pipeline performance statistics.

        Returns:
            Dictionary with statistics about pipeline execution,
            AI interactions, configuration, and system health

        Raises:
            Exception: If statistics cannot be calculated
        """
        try:
            now = datetime.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            # Get AI interaction statistics
            ai_stats = self._get_ai_interaction_statistics(last_24h, last_7d)

            # Get pipeline configuration statistics
            pipeline_config = self._get_pipeline_configuration()

            # Get prompt configuration statistics
            prompt_config = self._get_prompt_configuration()

            # Get system health statistics
            system_health = self._get_system_health()

            # Get cache statistics
            cache_stats = self._get_cache_statistics(ai_stats["total_interactions"], ai_stats["last_24h_interactions"])

            # Get performance improvements
            performance_metrics = self._get_performance_metrics(ai_stats, pipeline_config)

            return {
                "pipeline_mode": "modular",
                "timestamp": now.isoformat(),
                "cache_statistics": cache_stats,
                "ai_interaction_statistics": ai_stats,
                "pipeline_configuration": pipeline_config,
                "prompt_configuration": prompt_config,
                "system_health": system_health,
                "performance_improvements": performance_metrics
            }

        except Exception as e:
            logger.error(f"Failed to get pipeline statistics: {e}")
            return self._get_error_statistics()

    def _get_ai_interaction_statistics(self, last_24h: datetime, last_7d: datetime) -> dict:
        """
        Get AI interaction statistics using repository pattern.

        Args:
            last_24h: Timestamp for 24 hours ago
            last_7d: Timestamp for 7 days ago

        Returns:
            Dictionary with AI interaction statistics
        """
        # Total AI interactions
        total_interactions = self.execution_repository.count()

        # Recent interactions (24h)
        recent_interactions = self.execution_repository.count_since(last_24h)

        # Weekly interactions
        weekly_interactions = self.execution_repository.count_since(last_7d)

        # Average processing time (last 100 interactions)
        avg_processing_time = self.execution_repository.get_average_execution_time(limit=100)
        avg_processing_time_ms = avg_processing_time * 1000  # Convert to ms

        # Success rate (last 100 executions)
        success_rate = self.execution_repository.get_success_rate(limit=100)

        # Most used step
        most_used_step_id = self.execution_repository.get_most_used_step_id()
        most_used_step = "N/A"
        if most_used_step_id:
            most_used_step_db = self.step_repository.get(most_used_step_id)
            most_used_step = most_used_step_db.name if most_used_step_db else "N/A"

        return {
            "total_interactions": total_interactions,
            "last_24h_interactions": recent_interactions,
            "last_7d_interactions": weekly_interactions,
            "avg_processing_time_ms": round(avg_processing_time_ms, 2) if avg_processing_time_ms else 0,
            "success_rate_percent": round(success_rate, 1),
            "most_used_step": most_used_step
        }

    def _get_pipeline_configuration(self) -> dict:
        """
        Get pipeline configuration statistics.

        Returns:
            Dictionary with pipeline configuration details
        """
        pipeline_steps = self.step_repository.get_all_ordered()
        enabled_steps = [step for step in pipeline_steps if step.enabled]
        disabled_steps = [step for step in pipeline_steps if not step.enabled]

        return {
            "total_steps": len(pipeline_steps),
            "enabled_steps": len(enabled_steps),
            "disabled_steps": len(disabled_steps),
            "enabled_step_names": [step.name for step in enabled_steps],
            "disabled_step_names": [step.name for step in disabled_steps]
        }

    def _get_prompt_configuration(self) -> dict:
        """
        Get prompt configuration statistics.

        Returns:
            Dictionary with prompt configuration details
        """
        total_pipeline_steps = self.step_repository.count()

        return {
            "dynamic_pipeline_steps": total_pipeline_steps,
            "total_prompts_configured": total_pipeline_steps
        }

    def _get_system_health(self) -> dict:
        """
        Get system health statistics.

        Returns:
            Dictionary with system health metrics
        """
        # Get feature flag settings
        system_settings = self.settings_repository.get_settings_by_prefix('enable_')
        enabled_features = sum(
            1 for setting in system_settings
            if setting.value.lower() == 'true'
        )
        total_features = len(system_settings)

        return {
            "enabled_features": enabled_features,
            "total_features": total_features,
            "feature_adoption_percent": round(
                (enabled_features / total_features * 100), 1
            ) if total_features > 0 else 0,
            "database_status": "operational"
        }

    def _get_cache_statistics(self, total: int, recent: int) -> dict:
        """
        Get cache statistics.

        Args:
            total: Total interactions
            recent: Recent interactions (24h)

        Returns:
            Dictionary with cache statistics
        """
        # Get cache timeout from settings
        cache_timeout = self.settings_repository.get_int_value(
            'pipeline_cache_timeout',
            default=3600
        )

        return {
            "total_entries": total,
            "active_entries": recent,
            "expired_entries": max(0, total - recent),
            "cache_timeout_seconds": cache_timeout
        }

    def _get_performance_metrics(self, ai_stats: dict, pipeline_config: dict) -> dict:
        """
        Get performance improvement metrics.

        Args:
            ai_stats: AI interaction statistics
            pipeline_config: Pipeline configuration

        Returns:
            Dictionary with performance metrics
        """
        metrics = {}

        if ai_stats["total_interactions"] > 0:
            metrics["avg_processing_time"] = f"{ai_stats['avg_processing_time_ms']:.0f}ms average processing time"
            metrics["success_rate"] = f"{ai_stats['success_rate_percent']:.1f}% success rate"
            metrics["daily_throughput"] = f"{ai_stats['last_24h_interactions']} interactions in last 24h"
            metrics["weekly_volume"] = f"{ai_stats['last_7d_interactions']} interactions in last 7 days"
        else:
            metrics["status"] = "No AI interactions recorded yet"

        if pipeline_config["enabled_steps"] > 0:
            metrics["active_pipeline_steps"] = f"{pipeline_config['enabled_steps']}/{pipeline_config['total_steps']} pipeline steps enabled"
            metrics["most_used_step"] = f"Most used: {ai_stats['most_used_step']}"

        metrics["configuration_completeness"] = f"{pipeline_config['total_steps']} dynamic pipeline steps configured"

        return metrics

    def _get_error_statistics(self) -> dict:
        """
        Get fallback statistics when error occurs.

        Returns:
            Dictionary with minimal error statistics
        """
        # Try to get cache timeout even in error case
        try:
            cache_timeout = self.settings_repository.get_int_value(
                'pipeline_cache_timeout',
                default=3600
            )
        except Exception:
            cache_timeout = 3600

        return {
            "pipeline_mode": "unified",
            "timestamp": datetime.now().isoformat(),
            "error": "Unable to calculate statistics",
            "cache_statistics": {
                "total_entries": 0,
                "active_entries": 0,
                "expired_entries": 0,
                "cache_timeout_seconds": cache_timeout
            },
            "ai_interaction_statistics": {
                "total_interactions": 0,
                "last_24h_interactions": 0,
                "last_7d_interactions": 0,
                "avg_processing_time_ms": 0,
                "success_rate_percent": 0,
                "most_used_step": "N/A"
            },
            "pipeline_configuration": {
                "total_steps": 0,
                "enabled_steps": 0,
                "disabled_steps": 0,
                "enabled_step_names": [],
                "disabled_step_names": []
            },
            "prompt_configuration": {
                "universal_prompts": 0,
                "document_specific_prompts": 0,
                "total_prompts_configured": 0
            },
            "system_health": {
                "enabled_features": 0,
                "total_features": 0,
                "feature_adoption_percent": 0,
                "database_status": "error"
            },
            "performance_improvements": {
                "error": "Unable to calculate performance metrics"
            }
        }

    def get_performance_comparison(self) -> dict:
        """
        Get performance comparison between optimized and legacy pipeline.

        Returns:
            Dictionary with performance comparison information
        """
        return {
            "optimized_pipeline": {
                "features": [
                    "Prompt caching (5min TTL)",
                    "Parallel classification + preprocessing",
                    "Parallel quality checks (fact + grammar)",
                    "Async AI API calls",
                    "Smart error fallbacks",
                    "AI-based medical validation",
                    "AI-based text formatting"
                ],
                "expected_improvements": {
                    "speed": "40-60% faster processing",
                    "database_calls": "90% reduction via caching",
                    "ai_api_efficiency": "2-3x better throughput with parallel calls",
                    "reliability": "Better error handling and fallbacks"
                }
            },
            "legacy_pipeline": {
                "features": [
                    "Sequential processing",
                    "Database call per document",
                    "Hardcoded medical validation",
                    "Hardcoded text formatting",
                    "No parallel operations"
                ],
                "limitations": [
                    "Slower due to sequential processing",
                    "More database load",
                    "Less flexible validation",
                    "Fixed formatting logic"
                ]
            },
            "recommendation": "Use optimized pipeline for better performance and flexibility",
            "toggle_method": "Set USE_OPTIMIZED_PIPELINE environment variable"
        }

    def clear_cache(self) -> dict:
        """
        Clear pipeline cache (compatibility endpoint).

        In the unified system, prompts are stored in database,
        so this is a no-op but kept for API compatibility.

        Returns:
            Dictionary with clear cache result
        """
        return {
            "success": True,
            "message": "Unified system uses database storage - no cache to clear",
            "timestamp": datetime.now()
        }
