"""
Document Class Repository

Handles database operations for document class definitions.
"""

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.database.modular_pipeline_models import DocumentClassDB
from app.repositories.base_repository import BaseRepository


class DocumentClassRepository(BaseRepository[DocumentClassDB]):
    """
    Repository for Document Class operations.

    Provides specialized queries for managing document classes (types)
    beyond basic CRUD operations.
    """

    def __init__(self, db: Session):
        """
        Initialize document class repository.

        Args:
            db: Database session
        """
        super().__init__(db, DocumentClassDB)

    def get_by_class_key(self, class_key: str) -> DocumentClassDB | None:
        """
        Get document class by its unique key identifier.

        Args:
            class_key: Unique class key (e.g., 'ARZTBRIEF', 'BEFUNDBERICHT')

        Returns:
            Document class instance or None if not found
        """
        return self.db.query(self.model).filter_by(class_key=class_key).first()

    def get_enabled_classes(self) -> list[DocumentClassDB]:
        """
        Get all enabled document classes.

        Returns:
            List of enabled document classes
        """
        return (
            self.db.query(self.model)
            .filter_by(is_enabled=True)
            .order_by(self.model.display_name)
            .all()
        )

    def get_disabled_classes(self) -> list[DocumentClassDB]:
        """
        Get all disabled document classes.

        Returns:
            List of disabled document classes
        """
        return (
            self.db.query(self.model)
            .filter_by(is_enabled=False)
            .order_by(self.model.display_name)
            .all()
        )

    def get_system_classes(self) -> list[DocumentClassDB]:
        """
        Get built-in system document classes.

        System classes cannot be deleted.

        Returns:
            List of system document classes
        """
        return (
            self.db.query(self.model)
            .filter_by(is_system_class=True)
            .order_by(self.model.display_name)
            .all()
        )

    def get_user_classes(self) -> list[DocumentClassDB]:
        """
        Get user-created (non-system) document classes.

        Returns:
            List of user-created document classes
        """
        return (
            self.db.query(self.model)
            .filter_by(is_system_class=False)
            .order_by(self.model.display_name)
            .all()
        )

    def class_key_exists(self, class_key: str, exclude_id: int | None = None) -> bool:
        """
        Check if a class key already exists.

        Args:
            class_key: Class key to check
            exclude_id: Optional ID to exclude from check (for updates)

        Returns:
            True if key exists, False otherwise
        """
        query = self.db.query(self.model).filter_by(class_key=class_key)

        if exclude_id:
            query = query.filter(self.model.id != exclude_id)

        return query.count() > 0

    def enable_class(self, class_id: int) -> DocumentClassDB | None:
        """
        Enable a document class.

        Args:
            class_id: ID of the class to enable

        Returns:
            Updated class or None if not found
        """
        return self.update(class_id, is_enabled=True)

    def disable_class(self, class_id: int) -> DocumentClassDB | None:
        """
        Disable a document class.

        Args:
            class_id: ID of the class to disable

        Returns:
            Updated class or None if not found
        """
        return self.update(class_id, is_enabled=False)

    def get_classes_with_indicators(self, indicator: str) -> list[DocumentClassDB]:
        """
        Get classes that have a specific indicator (strong or weak).

        Args:
            indicator: Indicator text to search for

        Returns:
            List of classes containing the indicator
        """
        classes = self.get_all()

        matching = []
        for doc_class in classes:
            if (
                doc_class.strong_indicators
                and indicator in doc_class.strong_indicators
                or doc_class.weak_indicators
                and indicator in doc_class.weak_indicators
            ):
                matching.append(doc_class)

        return matching

    def get_classes_with_examples(self, example_text: str) -> list[DocumentClassDB]:
        """
        Get classes that have a specific example.

        Args:
            example_text: Example text to search for

        Returns:
            List of classes containing the example
        """
        classes = self.get_all()

        return [
            doc_class
            for doc_class in classes
            if doc_class.examples and example_text in doc_class.examples
        ]

    def add_example(self, class_id: int, example: str) -> DocumentClassDB | None:
        """
        Add an example to a document class.

        Args:
            class_id: ID of the class
            example: Example text to add

        Returns:
            Updated class or None if not found
        """
        doc_class = self.get(class_id)
        if not doc_class:
            return None

        if doc_class.examples is None:
            doc_class.examples = []

        if example not in doc_class.examples:
            doc_class.examples.append(example)
            flag_modified(doc_class, "examples")
            self.db.commit()
            self.db.refresh(doc_class)

        return doc_class

    def remove_example(self, class_id: int, example: str) -> DocumentClassDB | None:
        """
        Remove an example from a document class.

        Args:
            class_id: ID of the class
            example: Example text to remove

        Returns:
            Updated class or None if not found
        """
        doc_class = self.get(class_id)
        if not doc_class or not doc_class.examples:
            return None

        if example in doc_class.examples:
            doc_class.examples.remove(example)
            flag_modified(doc_class, "examples")
            self.db.commit()
            self.db.refresh(doc_class)

        return doc_class

    def add_strong_indicator(self, class_id: int, indicator: str) -> DocumentClassDB | None:
        """
        Add a strong indicator to a document class.

        Args:
            class_id: ID of the class
            indicator: Indicator text to add

        Returns:
            Updated class or None if not found
        """
        doc_class = self.get(class_id)
        if not doc_class:
            return None

        if doc_class.strong_indicators is None:
            doc_class.strong_indicators = []

        if indicator not in doc_class.strong_indicators:
            doc_class.strong_indicators.append(indicator)
            flag_modified(doc_class, "strong_indicators")
            self.db.commit()
            self.db.refresh(doc_class)

        return doc_class

    def add_weak_indicator(self, class_id: int, indicator: str) -> DocumentClassDB | None:
        """
        Add a weak indicator to a document class.

        Args:
            class_id: ID of the class
            indicator: Indicator text to add

        Returns:
            Updated class or None if not found
        """
        doc_class = self.get(class_id)
        if not doc_class:
            return None

        if doc_class.weak_indicators is None:
            doc_class.weak_indicators = []

        if indicator not in doc_class.weak_indicators:
            doc_class.weak_indicators.append(indicator)
            flag_modified(doc_class, "weak_indicators")
            self.db.commit()
            self.db.refresh(doc_class)

        return doc_class

    def has_associated_steps(self, class_id: int) -> bool:
        """
        Check if document class has associated pipeline steps.

        Args:
            class_id: ID of the class

        Returns:
            True if class has steps, False otherwise
        """
        from app.database.modular_pipeline_models import DynamicPipelineStepDB

        count = self.db.query(DynamicPipelineStepDB).filter_by(document_class_id=class_id).count()

        return count > 0

    def get_class_statistics(self) -> dict:
        """
        Get aggregate statistics about document classes.

        Returns:
            Dictionary with statistics
        """
        classes = self.get_all()

        return {
            "total_classes": len(classes),
            "enabled_classes": sum(1 for c in classes if c.is_enabled),
            "disabled_classes": sum(1 for c in classes if not c.is_enabled),
            "system_classes": sum(1 for c in classes if c.is_system_class),
            "user_classes": sum(1 for c in classes if not c.is_system_class),
            "classes_with_examples": sum(1 for c in classes if c.examples),
            "classes_with_strong_indicators": sum(1 for c in classes if c.strong_indicators),
            "classes_with_weak_indicators": sum(1 for c in classes if c.weak_indicators),
        }

    def search_by_display_name(self, search_term: str) -> list[DocumentClassDB]:
        """
        Search document classes by display name.

        Args:
            search_term: Text to search for (case-insensitive)

        Returns:
            List of matching document classes
        """
        return (
            self.db.query(self.model)
            .filter(self.model.display_name.ilike(f"%{search_term}%"))
            .all()
        )

    def search_by_description(self, search_term: str) -> list[DocumentClassDB]:
        """
        Search document classes by description.

        Args:
            search_term: Text to search for (case-insensitive)

        Returns:
            List of matching document classes
        """
        return (
            self.db.query(self.model).filter(self.model.description.ilike(f"%{search_term}%")).all()
        )
