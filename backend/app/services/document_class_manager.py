"""Document Class Manager Service for dynamic medical document classification.

Comprehensive CRUD service for managing document classification types with automatic
pipeline integration. Supports system-protected classes (ARZTBRIEF, BEFUNDBERICHT,
LABORWERTE) and user-defined custom classes for extensible medical workflows.

**Core Features**:
    - CRUD operations: Create, Read, Update, Delete document classes
    - System protection: Prevent deletion/modification of core medical classes
    - Auto-sync: Classification prompts update when classes change
    - Validation: Unique keys, referential integrity checks
    - Statistics: Count system vs. custom classes

**Document Class System**:
    - **System Classes** (protected): ARZTBRIEF, BEFUNDBERICHT, LABORWERTE
      * Cannot be deleted
      * class_key cannot be modified
      * Essential for medical document processing

    - **Custom Classes** (user-defined): Any additional categories
      * Full CRUD support
      * Can be disabled without deletion
      * Support custom pipeline branches

**Database Integration**:
    - Primary table: document_classes (DocumentClassDB)
    - Related table: dynamic_pipeline_steps (DynamicPipelineStepDB)
    - Cascading updates: Changes trigger classification prompt regeneration

**Classification Prompt Auto-Generation**:
    When document classes change (create/update/delete), the service automatically
    rebuilds classification prompts for all branching pipeline steps. Ensures
    AI classifiers always see current document types.

**Use Cases**:
    - Add new medical document types (e.g., "THERAPIEPLAN", "MEDIKATIONSPLAN")
    - Customize document workflows per organization
    - Enable/disable document types without data loss
    - Generate classification prompts dynamically

**Example Usage**:
    >>> from app.database.connection import get_db_session
    >>> db = next(get_db_session())
    >>> manager = DocumentClassManager(session=db)
    >>>
    >>> # Create custom document class
    >>> new_class = manager.create_class({
    ...     "class_key": "THERAPIEPLAN",
    ...     "display_name": "Therapieplan",
    ...     "description": "Treatment and therapy plans",
    ...     "icon": "📋",
    ...     "is_enabled": True,
    ...     "strong_indicators": ["Therapie", "Behandlungsplan"],
    ...     "weak_indicators": ["Medikation", "Dosierung"]
    ... })
    >>>
    >>> # Get all enabled classes
    >>> enabled = manager.get_enabled_classes()
    >>> for cls in enabled:
    ...     print(f"{cls.icon} {cls.display_name}: {cls.description}")
    >>>
    >>> # Update class description
    >>> manager.update_class(new_class.id, {
    ...     "description": "Comprehensive therapy and treatment plans"
    ... })
    >>>
    >>> # Get classification prompt (auto-generated from enabled classes)
    >>> prompt = manager.get_classification_prompt_template()
    >>> print(prompt)  # Includes all enabled classes with indicators

**System Protection**:
    System classes marked with is_system_class=True:
    - ARZTBRIEF (Doctor's letters, discharge summaries)
    - BEFUNDBERICHT (Medical findings, diagnostic reports)
    - LABORWERTE (Lab results, blood tests)

    Protection enforced:
    - delete_class(): Raises ValueError if is_system_class=True
    - update_class(): Prevents changing class_key if is_system_class=True

Note:
    **Referential Integrity**: Cannot delete classes with associated pipeline steps.
    Must delete/reassign steps first to maintain database consistency.

    **Prompt Synchronization**: All branching pipeline steps automatically updated
    when classes change. Ensures classification always uses current schema.

    **Custom Class Lifecycle**:
    1. Create with strong/weak indicators
    2. Enable for production use
    3. Disable to hide (soft delete)
    4. Delete when no longer needed (hard delete)
"""

from datetime import datetime
import logging


from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.modular_pipeline_models import DocumentClassDB
from app.repositories.document_class_repository import DocumentClassRepository
from app.repositories.pipeline_step_repository import PipelineStepRepository

logger = logging.getLogger(__name__)


class DocumentClassManager:
    """Comprehensive service for managing dynamic medical document classification types.

    Provides full CRUD lifecycle management for document classes with built-in
    system protections, automatic prompt synchronization, and referential integrity
    validation. Designed for extensible medical document workflows.

    **Key Responsibilities**:
        - Create/Read/Update/Delete document classification types
        - Protect system-critical classes from deletion/modification
        - Auto-regenerate classification prompts on schema changes
        - Validate uniqueness and referential integrity
        - Generate statistics and analytics

    **System vs. Custom Classes**:
        - System: is_system_class=True (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
        - Custom: is_system_class=False (user-defined types)

    **Auto-Sync Behavior**:
        After create/update/delete operations, automatically calls
        _trigger_classification_prompt_update() to keep AI classifiers
        in sync with current document schema.

    Attributes:
        session (Session): SQLAlchemy database session for CRUD operations

    Example:
        >>> manager = DocumentClassManager(session=db)
        >>>
        >>> # Create new document type
        >>> therapy_plan = manager.create_class({
        ...     "class_key": "THERAPIEPLAN",
        ...     "display_name": "Therapieplan",
        ...     "description": "Treatment plans",
        ...     "icon": "📋",
        ...     "is_enabled": True
        ... })
        >>>
        >>> # Get statistics
        >>> stats = manager.get_class_statistics()
        >>> print(f"{stats['custom_classes']} custom classes")
        >>>
        >>> # Generate classification prompt
        >>> prompt = manager.get_classification_prompt_template()
        >>> # Prompt includes all enabled classes

    Note:
        **Thread Safety**: Not thread-safe. Session shared across operations.
        Use separate manager instances per thread/request.

        **Transaction Management**: Methods commit on success, rollback on error.
        Caller responsible for session lifecycle (creation/close).

        **System Class Protection**:
        ValueError raised if attempting to:
        - Delete system class
        - Change class_key of system class

        **Referential Integrity**:
        ValueError raised if attempting to delete class with associated
        pipeline steps. Must orphan/delete steps first.
    """

    def __init__(
        self,
        session: Session,
        class_repository: DocumentClassRepository | None = None,
        step_repository: PipelineStepRepository | None = None,
    ):
        """Initialize Document Class Manager with database session and repositories.

        Args:
            session: SQLAlchemy session (kept for backward compatibility)
            class_repository: Document class repository (injected for clean architecture)
            step_repository: Pipeline step repository (injected for clean architecture)
        """
        self.session = session
        self.class_repository = class_repository or DocumentClassRepository(session)
        self.step_repository = step_repository or PipelineStepRepository(session)

    # ==================== READ OPERATIONS ====================

    def get_all_classes(self, enabled_only: bool = False) -> list[DocumentClassDB]:
        """
        Get all document classes using repository pattern.

        Args:
            enabled_only: If True, only return enabled classes

        Returns:
            List of document classes ordered by display_name
        """
        try:
            if enabled_only:
                classes = self.class_repository.get_enabled_classes()
            else:
                classes = self.class_repository.get_all()

            logger.info(
                f"📋 Retrieved {len(classes)} document classes (enabled_only={enabled_only})"
            )
            return classes

        except Exception as e:
            logger.error(f"❌ Failed to get document classes: {e}")
            return []

    def get_class(self, class_id: int) -> DocumentClassDB | None:
        """
        Get a single document class by ID using repository pattern.

        Args:
            class_id: Database ID of the class

        Returns:
            Document class or None if not found
        """
        try:
            doc_class = self.class_repository.get(class_id)

            if doc_class:
                logger.debug(f"Found document class: {doc_class.class_key}")
            else:
                logger.warning(f"Document class ID {class_id} not found")

            return doc_class

        except Exception as e:
            logger.error(f"❌ Failed to get document class {class_id}: {e}")
            return None

    def get_class_by_key(self, class_key: str) -> DocumentClassDB | None:
        """
        Get a document class by its unique key using repository pattern.

        Args:
            class_key: Unique class key (e.g., "ARZTBRIEF")

        Returns:
            Document class or None if not found
        """
        try:
            doc_class = self.class_repository.get_by_class_key(class_key)

            if doc_class:
                logger.debug(f"Found document class: {doc_class.class_key}")
            else:
                logger.warning(f"Document class key '{class_key}' not found")

            return doc_class

        except Exception as e:
            logger.error(f"❌ Failed to get document class by key '{class_key}': {e}")
            return None

    def get_enabled_classes(self) -> list[DocumentClassDB]:
        """
        Get all enabled document classes.

        Returns:
            List of enabled document classes
        """
        return self.get_all_classes(enabled_only=True)

    # ==================== CREATE OPERATIONS ====================

    def create_class(self, class_data: dict[str, Any]) -> DocumentClassDB | None:
        """
        Create a new document class.

        Args:
            class_data: Dictionary containing class properties

        Returns:
            Created document class or None if creation failed

        Raises:
            ValueError: If class_key already exists or validation fails
        """
        try:
            # Validate class_key uniqueness
            class_key = class_data.get("class_key", "").upper().strip()
            if not class_key:
                raise ValueError("class_key is required")

            existing = self.get_class_by_key(class_key)
            if existing:
                raise ValueError(f"Document class '{class_key}' already exists")

            # Ensure class_key is uppercase and clean
            class_data["class_key"] = class_key

            # Create new document class
            doc_class = DocumentClassDB(**class_data)
            self.session.add(doc_class)
            self.session.commit()
            self.session.refresh(doc_class)

            logger.info(
                f"✅ Created document class: {doc_class.class_key} - {doc_class.display_name}"
            )

            # Trigger classification prompt update
            self._trigger_classification_prompt_update()

            return doc_class

        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"❌ Integrity error creating document class: {e}")
            raise ValueError("Document class with this key already exists") from e

        except ValueError:
            # Re-raise ValueError from validation checks (e.g., duplicate key)
            raise

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to create document class: {e}")
            return None

    # ==================== UPDATE OPERATIONS ====================

    def update_class(self, class_id: int, class_data: dict[str, Any]) -> DocumentClassDB | None:
        """
        Update an existing document class.

        Args:
            class_id: ID of the class to update
            class_data: Dictionary containing updated properties

        Returns:
            Updated document class or None if update failed

        Raises:
            ValueError: If trying to modify system class key or validation fails
        """
        try:
            doc_class = self.get_class(class_id)
            if not doc_class:
                raise ValueError(f"Document class {class_id} not found")

            # Prevent changing class_key of system classes
            if doc_class.is_system_class and "class_key" in class_data:
                if class_data["class_key"] != doc_class.class_key:
                    raise ValueError("Cannot change class_key of system document classes")

            # Ensure class_key is uppercase if being updated
            if "class_key" in class_data:
                class_data["class_key"] = class_data["class_key"].upper().strip()

                # Check uniqueness if changing class_key
                if class_data["class_key"] != doc_class.class_key:
                    existing = self.get_class_by_key(class_data["class_key"])
                    if existing:
                        raise ValueError(
                            f"Document class '{class_data['class_key']}' already exists"
                        )

            # Update fields
            for key, value in class_data.items():
                if hasattr(doc_class, key) and key not in ["id", "created_at", "created_by"]:
                    setattr(doc_class, key, value)

            doc_class.last_modified = datetime.now()
            self.session.commit()
            self.session.refresh(doc_class)

            logger.info(f"✅ Updated document class: {doc_class.class_key}")

            # Trigger classification prompt update
            self._trigger_classification_prompt_update()

            return doc_class

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to update document class {class_id}: {e}")
            raise

    # ==================== DELETE OPERATIONS ====================

    def delete_class(self, class_id: int) -> bool:
        """
        Delete a document class.

        Args:
            class_id: ID of the class to delete

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If trying to delete a system class or class with associated steps
        """
        try:
            doc_class = self.get_class(class_id)
            if not doc_class:
                logger.warning(f"Document class {class_id} not found")
                return False

            # Prevent deletion of system classes
            if doc_class.is_system_class:
                raise ValueError(f"Cannot delete system document class '{doc_class.class_key}'")

            # Check if class has associated pipeline steps using repository
            has_steps = self.class_repository.has_associated_steps(class_id)
            if has_steps:
                # Get count for error message
                steps = self.step_repository.get_steps_by_document_class(class_id)
                step_count = len(steps)
                raise ValueError(
                    f"Cannot delete document class '{doc_class.class_key}' because it has {step_count} "
                    f"associated pipeline steps. Please delete or reassign those steps first."
                )

            # Delete the class
            self.session.delete(doc_class)
            self.session.commit()

            logger.info(f"✅ Deleted document class: {doc_class.class_key}")

            # Trigger classification prompt update
            self._trigger_classification_prompt_update()

            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to delete document class {class_id}: {e}")
            raise

    # ==================== HELPER METHODS ====================

    def _trigger_classification_prompt_update(self):
        """
        Trigger update of classification prompt when document classes change.

        Automatically updates all branching steps to include current enabled document classes.
        """
        logger.info("🔄 Updating classification prompts for all branching steps...")

        try:
            # Find all branching/classification steps using repository
            branching_step = self.step_repository.get_branching_step()

            if not branching_step:
                logger.info("   ℹ️  No branching steps found to update")
                return

            branching_steps = [branching_step]  # Convert to list for iteration

            # Generate new classification prompt template
            new_prompt_template = self.get_classification_prompt_template()

            # Update all branching steps
            updated_count = 0
            for step in branching_steps:
                step.prompt_template = new_prompt_template
                step.last_modified = datetime.now()
                updated_count += 1

            self.session.commit()

            logger.info(
                f"   ✅ Updated {updated_count} classification step(s) with new document classes"
            )

        except Exception as e:
            logger.error(f"   ❌ Failed to update classification prompts: {e}")
            self.session.rollback()

    def get_classification_prompt_template(self) -> str:
        """
        Generate a classification prompt template based on current document classes.

        Returns:
            Formatted prompt template for document classification
        """
        enabled_classes = self.get_enabled_classes()

        if not enabled_classes:
            logger.warning("No enabled document classes found")
            return "No document classes available for classification."

        # Build class descriptions
        class_descriptions = []
        for doc_class in enabled_classes:
            class_descriptions.append(
                f"  - {doc_class.class_key} ({doc_class.icon}): {doc_class.description}"
            )

        # Generate prompt template
        return f"""Analyze the following medical document and classify it into one of these categories:

{chr(10).join(class_descriptions)}

Consider these classification indicators:

{self._format_classification_indicators(enabled_classes)}

Based on your analysis, classify the document and respond with ONLY the class key (e.g., ARZTBRIEF).

Document to classify:
{{input_text}}
"""

    def _format_classification_indicators(self, classes: list[DocumentClassDB]) -> str:
        """Format classification indicators for all classes"""
        indicators = []

        for doc_class in classes:
            indicators.append(f"{doc_class.class_key}:")

            if doc_class.strong_indicators:
                strong = ", ".join(doc_class.strong_indicators[:5])  # Limit to first 5
                indicators.append(f"  Strong indicators: {strong}")

            if doc_class.weak_indicators:
                weak = ", ".join(doc_class.weak_indicators[:5])  # Limit to first 5
                indicators.append(f"  Weak indicators: {weak}")

            indicators.append("")  # Blank line between classes

        return "\n".join(indicators)

    def get_class_statistics(self) -> dict[str, Any]:
        """
        Get statistics about document classes using repository pattern.

        Returns:
            Dictionary with class statistics
        """
        try:
            # Use repository method to get all statistics
            stats = self.class_repository.get_class_statistics()

            # Ensure all required keys are present
            return {
                "total_classes": stats.get("total_classes", 0),
                "enabled_classes": stats.get("enabled_classes", 0),
                "system_classes": stats.get("system_classes", 0),
                "custom_classes": stats.get(
                    "user_classes", 0
                ),  # Map user_classes to custom_classes
            }

        except Exception as e:
            logger.error(f"❌ Failed to get class statistics: {e}")
            return {
                "total_classes": 0,
                "enabled_classes": 0,
                "system_classes": 0,
                "custom_classes": 0,
            }
