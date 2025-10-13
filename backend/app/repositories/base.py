"""
Base Repository Pattern

Provides a generic base class for database access operations following
the Repository pattern. This abstracts database access from business logic.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy.orm import Session

# Type variable for the database model
ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.

    This generic repository can be extended for specific models to add
    custom query methods while inheriting standard CRUD functionality.

    Example:
        class UserRepository(BaseRepository[UserDB]):
            def __init__(self, session: Session):
                super().__init__(UserDB, session)

            def get_by_email(self, email: str) -> UserDB | None:
                return self.session.query(self.model).filter_by(
                    email=email
                ).first()
    """

    def __init__(self, model: type[ModelType], session: Session):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    def get(self, id: int) -> ModelType | None:
        """
        Get a single record by ID.

        Args:
            id: Primary key ID

        Returns:
            Model instance or None if not found
        """
        return self.session.query(self.model).filter_by(id=id).first()

    def get_all(self, limit: int | None = None, offset: int | None = None) -> list[ModelType]:
        """
        Get all records with optional pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        query = self.session.query(self.model)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model fields and values

        Returns:
            Created model instance

        Raises:
            SQLAlchemyError: If database operation fails
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance

    def update(self, id: int, **kwargs: Any) -> ModelType | None:
        """
        Update an existing record.

        Args:
            id: Primary key ID
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        instance = self.get(id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        self.session.commit()
        self.session.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        """
        Delete a record by ID.

        Args:
            id: Primary key ID

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        instance = self.get(id)
        if not instance:
            return False

        self.session.delete(instance)
        self.session.commit()
        return True

    def count(self) -> int:
        """
        Get total count of records.

        Returns:
            Total number of records
        """
        return self.session.query(self.model).count()

    def exists(self, id: int) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Primary key ID

        Returns:
            True if exists, False otherwise
        """
        return self.session.query(self.model).filter_by(id=id).count() > 0

    def filter_by(self, **kwargs: Any) -> list[ModelType]:
        """
        Filter records by exact field values.

        Args:
            **kwargs: Field names and values to filter by

        Returns:
            List of matching model instances

        Example:
            repository.filter_by(status="active", enabled=True)
        """
        return self.session.query(self.model).filter_by(**kwargs).all()

    def get_one_by(self, **kwargs: Any) -> ModelType | None:
        """
        Get a single record by field values.

        Args:
            **kwargs: Field names and values to filter by

        Returns:
            Model instance or None if not found

        Example:
            repository.get_one_by(email="user@example.com")
        """
        return self.session.query(self.model).filter_by(**kwargs).first()
