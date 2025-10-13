"""
Available Model Repository

Handles database operations for AI model registry.
"""

from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import AvailableModelDB
from app.repositories.base_repository import BaseRepository


class AvailableModelRepository(BaseRepository[AvailableModelDB]):
    """
    Repository for Available Model operations.

    Provides specialized queries for managing AI model registry
    beyond basic CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize available model repository.

        Args:
            db: Database session
        """
        super().__init__(db, AvailableModelDB)

    def get_by_name(self, name: str) -> AvailableModelDB | None:
        """
        Get model by its unique name.

        Args:
            name: Model name (e.g., "Meta-Llama-3_3-70B-Instruct")

        Returns:
            Model instance or None if not found
        """
        return self.db.query(self.model).filter_by(name=name).first()

    def get_enabled_models(self) -> list[AvailableModelDB]:
        """
        Get all enabled AI models.

        Returns:
            List of enabled models
        """
        return self.db.query(self.model).filter_by(
            is_enabled=True
        ).order_by(self.model.display_name).all()

    def get_disabled_models(self) -> list[AvailableModelDB]:
        """
        Get all disabled AI models.

        Returns:
            List of disabled models
        """
        return self.db.query(self.model).filter_by(
            is_enabled=False
        ).order_by(self.model.display_name).all()

    def get_enabled_model_by_id(self, model_id: int) -> AvailableModelDB | None:
        """
        Get an enabled model by ID.

        Args:
            model_id: Model ID

        Returns:
            Model instance if found and enabled, None otherwise
        """
        return self.db.query(self.model).filter_by(
            id=model_id,
            is_enabled=True
        ).first()

    def get_models_by_provider(self, provider: str) -> list[AvailableModelDB]:
        """
        Get models by provider.

        Args:
            provider: Provider name (e.g., "OVH", "OPENAI")

        Returns:
            List of models from the provider
        """
        return self.db.query(self.model).filter_by(
            provider=provider
        ).order_by(self.model.display_name).all()

    def enable_model(self, model_id: int) -> AvailableModelDB | None:
        """
        Enable an AI model.

        Args:
            model_id: ID of the model to enable

        Returns:
            Updated model or None if not found
        """
        return self.update(model_id, is_enabled=True)

    def disable_model(self, model_id: int) -> AvailableModelDB | None:
        """
        Disable an AI model.

        Args:
            model_id: ID of the model to disable

        Returns:
            Updated model or None if not found
        """
        return self.update(model_id, is_enabled=False)

    def model_name_exists(self, name: str, exclude_id: int | None = None) -> bool:
        """
        Check if a model name already exists.

        Args:
            name: Model name to check
            exclude_id: Optional ID to exclude from check (for updates)

        Returns:
            True if name exists, False otherwise
        """
        query = self.db.query(self.model).filter_by(name=name)

        if exclude_id:
            query = query.filter(self.model.id != exclude_id)

        return query.count() > 0

    def get_model_statistics(self) -> dict:
        """
        Get aggregate statistics about models.

        Returns:
            Dictionary with statistics
        """
        models = self.get_all()

        return {
            "total_models": len(models),
            "enabled_models": sum(1 for m in models if m.is_enabled),
            "disabled_models": sum(1 for m in models if not m.is_enabled),
        }
