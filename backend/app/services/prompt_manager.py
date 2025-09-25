import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import shutil
from app.models.document_types import DocumentClass, DocumentPrompts

logger = logging.getLogger(__name__)

class PromptManager:
    """
    Manages prompt configurations for different document types.
    Handles loading, saving, versioning, and backup of prompts.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the prompt manager.

        Args:
            config_dir: Directory containing prompt configuration files
        """
        self.config_dir = Path(config_dir or "app/config/prompts")
        self.ensure_config_directory()
        self._prompt_cache: Dict[DocumentClass, DocumentPrompts] = {}
        self.load_all_prompts()

    def ensure_config_directory(self):
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Prompt configuration directory: {self.config_dir}")

    def load_all_prompts(self):
        """Load all prompt configurations into cache."""
        for doc_class in DocumentClass:
            try:
                prompts = self.load_prompts(doc_class)
                self._prompt_cache[doc_class] = prompts
                logger.info(f"Loaded prompts for {doc_class.value}")
            except Exception as e:
                logger.error(f"Failed to load prompts for {doc_class.value}: {e}")
                # Load defaults if specific prompts fail
                self._prompt_cache[doc_class] = self._get_default_prompts(doc_class)

    def load_prompts(self, document_type: DocumentClass) -> DocumentPrompts:
        """
        Load prompts for a specific document type.

        Args:
            document_type: The document type to load prompts for

        Returns:
            DocumentPrompts object
        """
        config_file = self.config_dir / f"{document_type.value}.json"

        # Check if config file exists
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            return self._get_default_prompts(document_type)

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create DocumentPrompts object
            prompts = DocumentPrompts(
                document_type=document_type,
                classification_prompt=data.get("classification_prompt", ""),
                preprocessing_prompt=data.get("preprocessing_prompt", ""),
                translation_prompt=data.get("translation_prompt", ""),
                fact_check_prompt=data.get("fact_check_prompt", ""),
                grammar_check_prompt=data.get("grammar_check_prompt", ""),
                language_translation_prompt=data.get("language_translation_prompt", ""),
                final_check_prompt=data.get("final_check_prompt", ""),
                version=data.get("version", 1),
                last_modified=datetime.fromisoformat(data["last_modified"]) if "last_modified" in data else datetime.now(),
                modified_by=data.get("modified_by")
            )

            return prompts

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {config_file}: {e}")
            return self._get_default_prompts(document_type)
        except Exception as e:
            logger.error(f"Error loading prompts from {config_file}: {e}")
            return self._get_default_prompts(document_type)

    def save_prompts(
        self,
        document_type: DocumentClass,
        prompts: DocumentPrompts,
        user: Optional[str] = None,
        create_backup: bool = True
    ) -> bool:
        """
        Save prompts for a specific document type.

        Args:
            document_type: The document type
            prompts: The prompts to save
            user: Username of the person making the change
            create_backup: Whether to create a backup before saving

        Returns:
            True if successful, False otherwise
        """
        config_file = self.config_dir / f"{document_type.value}.json"

        try:
            # Create backup if requested and file exists
            if create_backup and config_file.exists():
                self._create_backup(document_type)

            # Update metadata
            prompts.version += 1
            prompts.last_modified = datetime.now()
            prompts.modified_by = user

            # Prepare data for saving
            data = {
                "document_type": document_type.value,
                "version": prompts.version,
                "last_modified": prompts.last_modified.isoformat(),
                "modified_by": prompts.modified_by,
                "classification_prompt": prompts.classification_prompt,
                "preprocessing_prompt": prompts.preprocessing_prompt,
                "translation_prompt": prompts.translation_prompt,
                "fact_check_prompt": prompts.fact_check_prompt,
                "grammar_check_prompt": prompts.grammar_check_prompt,
                "language_translation_prompt": prompts.language_translation_prompt,
                "final_check_prompt": prompts.final_check_prompt
            }

            # Save to file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Update cache
            self._prompt_cache[document_type] = prompts

            logger.info(f"Saved prompts for {document_type.value} (version {prompts.version})")
            return True

        except Exception as e:
            logger.error(f"Failed to save prompts for {document_type.value}: {e}")
            return False

    def get_prompts(self, document_type: DocumentClass) -> DocumentPrompts:
        """
        Get prompts for a specific document type from cache.

        Args:
            document_type: The document type

        Returns:
            DocumentPrompts object
        """
        if document_type in self._prompt_cache:
            return self._prompt_cache[document_type]

        # Try to load if not in cache
        prompts = self.load_prompts(document_type)
        self._prompt_cache[document_type] = prompts
        return prompts

    def get_prompt_by_step(
        self,
        document_type: DocumentClass,
        step: str
    ) -> str:
        """
        Get a specific prompt for a processing step.

        Args:
            document_type: The document type
            step: The processing step (e.g., 'translation_prompt')

        Returns:
            The prompt string
        """
        prompts = self.get_prompts(document_type)
        return getattr(prompts, step, "")

    def reset_to_defaults(self, document_type: DocumentClass) -> bool:
        """
        Reset prompts to defaults for a specific document type.

        Args:
            document_type: The document type to reset

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup before resetting
            self._create_backup(document_type)

            # Get default prompts
            default_prompts = self._get_default_prompts(document_type)

            # Save defaults
            return self.save_prompts(
                document_type,
                default_prompts,
                user="system",
                create_backup=False
            )

        except Exception as e:
            logger.error(f"Failed to reset prompts for {document_type.value}: {e}")
            return False

    def _create_backup(self, document_type: DocumentClass):
        """
        Create a backup of current prompts.

        Args:
            document_type: The document type to backup
        """
        try:
            config_file = self.config_dir / f"{document_type.value}.json"
            if config_file.exists():
                backup_dir = self.config_dir / "backups"
                backup_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"{document_type.value}_{timestamp}.json"

                shutil.copy2(config_file, backup_file)
                logger.info(f"Created backup: {backup_file}")

                # Keep only last 10 backups
                self._cleanup_old_backups(document_type)

        except Exception as e:
            logger.error(f"Failed to create backup for {document_type.value}: {e}")

    def _cleanup_old_backups(self, document_type: DocumentClass, keep_count: int = 10):
        """
        Remove old backup files, keeping only the most recent ones.

        Args:
            document_type: The document type
            keep_count: Number of backups to keep
        """
        try:
            backup_dir = self.config_dir / "backups"
            if not backup_dir.exists():
                return

            # Find all backups for this document type
            pattern = f"{document_type.value}_*.json"
            backups = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

            # Remove old backups
            for backup in backups[keep_count:]:
                backup.unlink()
                logger.debug(f"Removed old backup: {backup}")

        except Exception as e:
            logger.error(f"Failed to cleanup backups for {document_type.value}: {e}")

    def _get_default_prompts(self, document_type: DocumentClass) -> DocumentPrompts:
        """
        Get default prompts for a document type.

        Args:
            document_type: The document type

        Returns:
            Default DocumentPrompts object
        """
        # Try to load from defaults.json
        defaults_file = self.config_dir / "defaults.json"

        if defaults_file.exists():
            try:
                with open(defaults_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    universal = data.get("universal_prompts", {})

                    return DocumentPrompts(
                        document_type=document_type,
                        classification_prompt=universal.get("classification_prompt", "Classify this medical document."),
                        preprocessing_prompt=universal.get("preprocessing_prompt", "Remove personal data but keep medical information."),
                        translation_prompt=universal.get("translation_prompt", "Translate to patient-friendly language."),
                        fact_check_prompt=universal.get("fact_check_prompt", "Check medical accuracy."),
                        grammar_check_prompt=universal.get("grammar_check_prompt", "Correct grammar and spelling."),
                        language_translation_prompt=universal.get("language_translation_prompt", "Translate to {language}."),
                        final_check_prompt=universal.get("final_check_prompt", "Final quality check."),
                        version=1,
                        modified_by="system"
                    )
            except Exception as e:
                logger.error(f"Failed to load defaults: {e}")

        # Ultimate fallback - hardcoded defaults
        return DocumentPrompts(
            document_type=document_type,
            classification_prompt="Classify this medical document as ARZTBRIEF, BEFUNDBERICHT, or LABORWERTE.",
            preprocessing_prompt="Remove personal data but keep all medical information.",
            translation_prompt="Translate this medical text to patient-friendly language.",
            fact_check_prompt="Check this text for medical accuracy.",
            grammar_check_prompt="Correct German grammar and spelling.",
            language_translation_prompt="Translate this text to {language}.",
            final_check_prompt="Perform final quality check.",
            version=1,
            modified_by="system"
        )

    def export_prompts(self, document_type: Optional[DocumentClass] = None) -> Dict[str, Any]:
        """
        Export prompts for backup or sharing.

        Args:
            document_type: Specific document type or None for all

        Returns:
            Dictionary with prompt data
        """
        export_data = {
            "export_date": datetime.now().isoformat(),
            "version": 1,
            "prompts": {}
        }

        if document_type:
            prompts = self.get_prompts(document_type)
            export_data["prompts"][document_type.value] = {
                "classification_prompt": prompts.classification_prompt,
                "preprocessing_prompt": prompts.preprocessing_prompt,
                "translation_prompt": prompts.translation_prompt,
                "fact_check_prompt": prompts.fact_check_prompt,
                "grammar_check_prompt": prompts.grammar_check_prompt,
                "language_translation_prompt": prompts.language_translation_prompt,
                "final_check_prompt": prompts.final_check_prompt,
                "version": prompts.version
            }
        else:
            # Export all document types
            for doc_class in DocumentClass:
                prompts = self.get_prompts(doc_class)
                export_data["prompts"][doc_class.value] = {
                    "classification_prompt": prompts.classification_prompt,
                    "preprocessing_prompt": prompts.preprocessing_prompt,
                    "translation_prompt": prompts.translation_prompt,
                    "fact_check_prompt": prompts.fact_check_prompt,
                    "grammar_check_prompt": prompts.grammar_check_prompt,
                    "language_translation_prompt": prompts.language_translation_prompt,
                    "final_check_prompt": prompts.final_check_prompt,
                    "version": prompts.version
                }

        return export_data

    def import_prompts(
        self,
        import_data: Dict[str, Any],
        user: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Import prompts from exported data.

        Args:
            import_data: Dictionary with prompt data
            user: Username of the person importing

        Returns:
            Dictionary with import results for each document type
        """
        results = {}

        if "prompts" not in import_data:
            logger.error("Invalid import data: missing 'prompts' key")
            return results

        for doc_type_str, prompt_data in import_data["prompts"].items():
            try:
                # Convert string to DocumentClass
                doc_class = DocumentClass(doc_type_str)

                # Create DocumentPrompts object
                prompts = DocumentPrompts(
                    document_type=doc_class,
                    classification_prompt=prompt_data.get("classification_prompt", ""),
                    preprocessing_prompt=prompt_data.get("preprocessing_prompt", ""),
                    translation_prompt=prompt_data.get("translation_prompt", ""),
                    fact_check_prompt=prompt_data.get("fact_check_prompt", ""),
                    grammar_check_prompt=prompt_data.get("grammar_check_prompt", ""),
                    language_translation_prompt=prompt_data.get("language_translation_prompt", ""),
                    final_check_prompt=prompt_data.get("final_check_prompt", ""),
                    version=prompt_data.get("version", 1),
                    modified_by=user
                )

                # Save imported prompts
                success = self.save_prompts(doc_class, prompts, user=user)
                results[doc_type_str] = success

            except Exception as e:
                logger.error(f"Failed to import prompts for {doc_type_str}: {e}")
                results[doc_type_str] = False

        return results