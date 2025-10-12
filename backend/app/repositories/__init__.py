"""
Repository Layer

Provides data access abstraction using the Repository pattern.
All database access should go through repositories for better:
- Testability (easy to mock)
- Maintainability (centralized data access logic)
- Reusability (common CRUD operations)

Usage:
    from app.repositories import SettingsRepository
    from app.database.connection import get_session

    with next(get_session()) as db:
        settings_repo = SettingsRepository(db)
        value = settings_repo.get_value("some_key", default="default")
"""

from app.repositories.base_repository import BaseRepository
from app.repositories.settings_repository import SettingsRepository
from app.repositories.feature_flags_repository import FeatureFlagsRepository

__all__ = [
    "BaseRepository",
    "SettingsRepository",
    "FeatureFlagsRepository",
]
