"""
Repository Layer

Provides data access abstraction following the Repository pattern.
Separates business logic from database access concerns.
"""

from app.repositories.base import BaseRepository
from app.repositories.pipeline_job_repository import PipelineJobRepository

__all__ = [
    "BaseRepository",
    "PipelineJobRepository",
]
