"""
Dependency Injection

Provides FastAPI dependency factories for services and repositories.
Enables clean dependency injection throughout the application.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.connection import get_session
from app.services.processing_service import ProcessingService
from app.services.statistics_service import StatisticsService
from app.services.ai_cost_tracker import AICostTracker


# ==================== Service Factories ====================


def get_processing_service(
    db: Session = Depends(get_session)
) -> ProcessingService:
    """
    Dependency injection factory for ProcessingService.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        ProcessingService instance

    Usage:
        @router.post("/endpoint")
        async def endpoint(
            service: ProcessingService = Depends(get_processing_service)
        ):
            result = service.do_something()
            return result
    """
    return ProcessingService(db)


def get_statistics_service(
    db: Session = Depends(get_session)
) -> StatisticsService:
    """
    Dependency injection factory for StatisticsService.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        StatisticsService instance

    Usage:
        @router.get("/stats")
        async def get_stats(
            service: StatisticsService = Depends(get_statistics_service)
        ):
            stats = service.get_pipeline_statistics()
            return stats
    """
    return StatisticsService(db)


def get_ai_cost_tracker(
    db: Session = Depends(get_session)
) -> AICostTracker:
    """
    Dependency injection factory for AICostTracker.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        AICostTracker instance

    Usage:
        @router.get("/costs")
        async def get_costs(
            tracker: AICostTracker = Depends(get_ai_cost_tracker)
        ):
            costs = tracker.get_total_cost()
            return costs
    """
    return AICostTracker(db)


# ==================== Repository Factories ====================
# Add repository factories here as needed for direct access

from app.repositories.pipeline_job_repository import PipelineJobRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository
from app.repositories.pipeline_step_execution_repository import PipelineStepExecutionRepository
from app.repositories.document_class_repository import DocumentClassRepository
from app.repositories.system_settings_repository import SystemSettingsRepository
from app.repositories.ocr_configuration_repository import OCRConfigurationRepository
from app.repositories.available_model_repository import AvailableModelRepository
from app.repositories.ai_log_interaction_repository import AILogInteractionRepository


def get_pipeline_job_repository(
    db: Session = Depends(get_session)
) -> PipelineJobRepository:
    """
    Dependency injection factory for PipelineJobRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        PipelineJobRepository instance
    """
    return PipelineJobRepository(db)


def get_pipeline_step_repository(
    db: Session = Depends(get_session)
) -> PipelineStepRepository:
    """
    Dependency injection factory for PipelineStepRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        PipelineStepRepository instance
    """
    return PipelineStepRepository(db)


def get_pipeline_step_execution_repository(
    db: Session = Depends(get_session)
) -> PipelineStepExecutionRepository:
    """
    Dependency injection factory for PipelineStepExecutionRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        PipelineStepExecutionRepository instance
    """
    return PipelineStepExecutionRepository(db)


def get_document_class_repository(
    db: Session = Depends(get_session)
) -> DocumentClassRepository:
    """
    Dependency injection factory for DocumentClassRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        DocumentClassRepository instance
    """
    return DocumentClassRepository(db)


def get_system_settings_repository(
    db: Session = Depends(get_session)
) -> SystemSettingsRepository:
    """
    Dependency injection factory for SystemSettingsRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        SystemSettingsRepository instance
    """
    return SystemSettingsRepository(db)


def get_ocr_configuration_repository(
    db: Session = Depends(get_session)
) -> OCRConfigurationRepository:
    """
    Dependency injection factory for OCRConfigurationRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        OCRConfigurationRepository instance
    """
    return OCRConfigurationRepository(db)


def get_available_model_repository(
    db: Session = Depends(get_session)
) -> AvailableModelRepository:
    """
    Dependency injection factory for AvailableModelRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        AvailableModelRepository instance
    """
    return AvailableModelRepository(db)


def get_ai_log_interaction_repository(
    db: Session = Depends(get_session)
) -> AILogInteractionRepository:
    """
    Dependency injection factory for AILogInteractionRepository.

    Args:
        db: Database session (injected by FastAPI)

    Returns:
        AILogInteractionRepository instance
    """
    return AILogInteractionRepository(db)
