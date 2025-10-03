"""
Document Class Manager Service

Manages CRUD operations for dynamic document classification types.
Allows users to create, update, and manage custom document classes
with their own pipeline branches.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.modular_pipeline_models import (
    DocumentClassDB,
    DynamicPipelineStepDB
)

logger = logging.getLogger(__name__)


class DocumentClassManager:
    """
    Service for managing dynamic document classification types.

    Features:
    - CRUD operations for document classes
    - System class protection (cannot delete ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
    - Auto-update classification prompts when classes change
    - Validation and business logic
    """

    def __init__(self, session: Session):
        """
        Initialize Document Class Manager.

        Args:
            session: SQLAlchemy session for database access
        """
        self.session = session

    # ==================== READ OPERATIONS ====================

    def get_all_classes(self, enabled_only: bool = False) -> List[DocumentClassDB]:
        """
        Get all document classes.

        Args:
            enabled_only: If True, only return enabled classes

        Returns:
            List of document classes ordered by display_name
        """
        try:
            query = self.session.query(DocumentClassDB)

            if enabled_only:
                query = query.filter_by(is_enabled=True)

            classes = query.order_by(DocumentClassDB.display_name).all()

            logger.info(f"📋 Retrieved {len(classes)} document classes (enabled_only={enabled_only})")
            return classes

        except Exception as e:
            logger.error(f"❌ Failed to get document classes: {e}")
            return []

    def get_class(self, class_id: int) -> Optional[DocumentClassDB]:
        """
        Get a single document class by ID.

        Args:
            class_id: Database ID of the class

        Returns:
            Document class or None if not found
        """
        try:
            doc_class = self.session.query(DocumentClassDB).filter_by(id=class_id).first()

            if doc_class:
                logger.debug(f"Found document class: {doc_class.class_key}")
            else:
                logger.warning(f"Document class ID {class_id} not found")

            return doc_class

        except Exception as e:
            logger.error(f"❌ Failed to get document class {class_id}: {e}")
            return None

    def get_class_by_key(self, class_key: str) -> Optional[DocumentClassDB]:
        """
        Get a document class by its unique key.

        Args:
            class_key: Unique class key (e.g., "ARZTBRIEF")

        Returns:
            Document class or None if not found
        """
        try:
            doc_class = self.session.query(DocumentClassDB).filter_by(class_key=class_key).first()

            if doc_class:
                logger.debug(f"Found document class: {doc_class.class_key}")
            else:
                logger.warning(f"Document class key '{class_key}' not found")

            return doc_class

        except Exception as e:
            logger.error(f"❌ Failed to get document class by key '{class_key}': {e}")
            return None

    def get_enabled_classes(self) -> List[DocumentClassDB]:
        """
        Get all enabled document classes.

        Returns:
            List of enabled document classes
        """
        return self.get_all_classes(enabled_only=True)

    # ==================== CREATE OPERATIONS ====================

    def create_class(self, class_data: Dict[str, Any]) -> Optional[DocumentClassDB]:
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

            logger.info(f"✅ Created document class: {doc_class.class_key} - {doc_class.display_name}")

            # Trigger classification prompt update
            self._trigger_classification_prompt_update()

            return doc_class

        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"❌ Integrity error creating document class: {e}")
            raise ValueError(f"Document class with this key already exists")

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Failed to create document class: {e}")
            return None

    # ==================== UPDATE OPERATIONS ====================

    def update_class(self, class_id: int, class_data: Dict[str, Any]) -> Optional[DocumentClassDB]:
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
                        raise ValueError(f"Document class '{class_data['class_key']}' already exists")

            # Update fields
            for key, value in class_data.items():
                if hasattr(doc_class, key) and key not in ['id', 'created_at', 'created_by']:
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

            # Check if class has associated pipeline steps
            step_count = self.session.query(DynamicPipelineStepDB).filter_by(
                document_class_id=class_id
            ).count()

            if step_count > 0:
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
            # Find all branching/classification steps
            branching_steps = self.session.query(DynamicPipelineStepDB).filter_by(
                is_branching_step=True
            ).all()

            if not branching_steps:
                logger.info("   ℹ️  No branching steps found to update")
                return

            # Generate new classification prompt template
            new_prompt_template = self.get_classification_prompt_template()

            # Update all branching steps
            updated_count = 0
            for step in branching_steps:
                step.prompt_template = new_prompt_template
                step.last_modified = datetime.now()
                updated_count += 1

            self.session.commit()

            logger.info(f"   ✅ Updated {updated_count} classification step(s) with new document classes")

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
        prompt_template = f"""Analyze the following medical document and classify it into one of these categories:

{chr(10).join(class_descriptions)}

Consider these classification indicators:

{self._format_classification_indicators(enabled_classes)}

Based on your analysis, classify the document and respond with ONLY the class key (e.g., ARZTBRIEF).

Document to classify:
{{input_text}}
"""

        return prompt_template

    def _format_classification_indicators(self, classes: List[DocumentClassDB]) -> str:
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

    def get_class_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about document classes.

        Returns:
            Dictionary with class statistics
        """
        try:
            total_classes = self.session.query(DocumentClassDB).count()
            enabled_classes = self.session.query(DocumentClassDB).filter_by(is_enabled=True).count()
            system_classes = self.session.query(DocumentClassDB).filter_by(is_system_class=True).count()
            custom_classes = total_classes - system_classes

            return {
                "total_classes": total_classes,
                "enabled_classes": enabled_classes,
                "system_classes": system_classes,
                "custom_classes": custom_classes
            }

        except Exception as e:
            logger.error(f"❌ Failed to get class statistics: {e}")
            return {
                "total_classes": 0,
                "enabled_classes": 0,
                "system_classes": 0,
                "custom_classes": 0
            }
