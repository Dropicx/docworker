"""
Base Repository Pattern

Provides generic CRUD operations for database entities.
All specific repositories should inherit from BaseRepository.
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Generic type for database models
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: Session):
                super().__init__(db, User)
    """

    def __init__(self, db: Session, model: type[ModelType]):
        """
        Initialize repository with database session and model class.

        Args:
            db: SQLAlchemy session
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model

    def get(self, record_id: Any) -> ModelType | None:
        """
        Get entity by primary key (convenience method).

        Alias for get_by_id() for shorter syntax.

        Args:
            record_id: Primary key value

        Returns:
            Entity instance or None if not found
        """
        return self.get_by_id(record_id)

    def get_by_id(self, record_id: Any) -> ModelType | None:
        """Get entity by primary key."""
        try:
            return self.db.query(self.model).filter(self.model.id == record_id).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id={record_id}: {e}")
            raise

    def get_all(
        self, skip: int = 0, limit: int = 100, filters: dict[str, Any] | None = None
    ) -> list[ModelType]:
        """
        Get all entities with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field:value filters
        """
        try:
            query = self.db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise

    def get_one(self, filters: dict[str, Any]) -> ModelType | None:
        """
        Get single entity by filters.

        Args:
            filters: Dictionary of field:value filters
        """
        try:
            query = self.db.query(self.model)

            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.filter(getattr(self.model, field) == value)

            return query.first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} with filters {filters}: {e}")
            raise

    def create(self, **kwargs) -> ModelType:
        """
        Create new entity.

        Args:
            **kwargs: Field values for new entity
        """
        try:
            entity = self.model(**kwargs)
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)

            logger.info(f"Created {self.model.__name__} with id={entity.id}")
            return entity
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    def update(self, record_id: Any, **kwargs) -> ModelType | None:
        """
        Update entity by primary key.

        Args:
            record_id: Primary key value
            **kwargs: Fields to update
        """
        try:
            entity = self.get_by_id(record_id)
            if not entity:
                logger.warning(f"{self.model.__name__} with id={record_id} not found")
                return None

            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            self.db.commit()
            self.db.refresh(entity)

            logger.info(f"Updated {self.model.__name__} with id={record_id}")
            return entity
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} id={record_id}: {e}")
            raise

    def delete(self, record_id: Any) -> bool:
        """
        Delete entity by primary key.

        Args:
            record_id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        try:
            entity = self.get_by_id(record_id)
            if not entity:
                logger.warning(f"{self.model.__name__} with id={record_id} not found")
                return False

            self.db.delete(entity)
            self.db.commit()

            logger.info(f"Deleted {self.model.__name__} with id={record_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} id={record_id}: {e}")
            raise

    def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        Count entities with optional filtering.

        Args:
            filters: Dictionary of field:value filters
        """
        try:
            query = self.db.query(self.model)

            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)

            return query.count()
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise

    def exists(self, filters: dict[str, Any]) -> bool:
        """
        Check if entity exists with given filters.

        Args:
            filters: Dictionary of field:value filters
        """
        return self.count(filters) > 0
