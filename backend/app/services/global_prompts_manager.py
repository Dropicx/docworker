"""
Global Prompts Manager - Manages universal prompts used across all document types
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class GlobalPrompts:
    """Container for global/universal prompts"""
    medical_validation_prompt: str
    classification_prompt: str
    preprocessing_prompt: str
    grammar_check_prompt: str
    language_translation_prompt: str
    version: int = 1
    last_modified: Optional[str] = None
    modified_by: Optional[str] = None

class GlobalPromptsManager:
    """
    Manages universal prompts that are used across all document types.
    These prompts handle preprocessing steps that should be consistent regardless of document type.
    """

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the global prompts manager.

        Args:
            config_dir: Directory containing global prompt configuration
        """
        self.config_dir = Path(config_dir or "app/config/prompts")
        self.global_prompts_file = self.config_dir / "global_prompts.json"
        self.ensure_config_directory()
        self._prompts_cache: Optional[GlobalPrompts] = None
        self._load_global_prompts()

    def ensure_config_directory(self):
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Global prompts configuration directory: {self.config_dir}")

    def _load_global_prompts(self) -> GlobalPrompts:
        """Load global prompts from file or create defaults."""
        try:
            if self.global_prompts_file.exists():
                with open(self.global_prompts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._prompts_cache = GlobalPrompts(
                    medical_validation_prompt=data.get("medical_validation_prompt", self._get_default_medical_validation()),
                    classification_prompt=data.get("classification_prompt", self._get_default_classification()),
                    preprocessing_prompt=data.get("preprocessing_prompt", self._get_default_preprocessing()),
                    grammar_check_prompt=data.get("grammar_check_prompt", self._get_default_grammar_check()),
                    language_translation_prompt=data.get("language_translation_prompt", self._get_default_language_translation()),
                    version=data.get("version", 1),
                    last_modified=data.get("last_modified"),
                    modified_by=data.get("modified_by")
                )

                logger.info("✅ Global prompts loaded from file")
                return self._prompts_cache

        except Exception as e:
            logger.error(f"❌ Failed to load global prompts: {e}")

        # Create defaults if file doesn't exist or loading fails
        logger.info("📝 Creating default global prompts")
        return self._create_default_global_prompts()

    def _create_default_global_prompts(self) -> GlobalPrompts:
        """Create default global prompts."""
        default_prompts = GlobalPrompts(
            medical_validation_prompt=self._get_default_medical_validation(),
            classification_prompt=self._get_default_classification(),
            preprocessing_prompt=self._get_default_preprocessing(),
            grammar_check_prompt=self._get_default_grammar_check(),
            language_translation_prompt=self._get_default_language_translation(),
            version=1,
            last_modified=datetime.now().isoformat(),
            modified_by="system"
        )

        # Save defaults to file
        self._save_global_prompts(default_prompts)
        self._prompts_cache = default_prompts
        return default_prompts

    def _get_default_medical_validation(self) -> str:
        """Get default medical validation prompt."""
        return """Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält.

KRITERIEN FÜR MEDIZINISCHEN INHALT:
- Diagnosen oder Symptome
- Medizinische Fachbegriffe
- Behandlungen oder Therapien
- Medikamente oder Dosierungen
- Laborwerte oder Messwerte
- Medizinische Abkürzungen
- Anatomische Begriffe
- Arztbriefe oder Befundberichte
- Medizinische Untersuchungen

NICHT-MEDIZINISCHE INHALTE:
- Allgemeine Texte ohne medizinischen Bezug
- Reine administrative Informationen
- Marketingtexte
- Literatur ohne medizinischen Kontext

Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH"""

    def _get_default_classification(self) -> str:
        """Get default classification prompt."""
        return """Analysiere diesen medizinischen Text und klassifiziere ihn in eine der folgenden Kategorien:

ARZTBRIEF:
- Kommunikation zwischen Ärzten
- Entlassungsbriefe
- Überweisungsschreiben
- Konsiliarbetrichte
- Therapieberichte

BEFUNDBERICHT:
- Untersuchungsergebnisse
- Bildgebungsbefunde (MRT, CT, Ultraschall)
- Pathologiebefunde
- EKG-Befunde
- Funktionsdiagnostik

LABORWERTE:
- Blutwerte mit Referenzbereichen
- Urinanalyse
- Hormonwerte
- Tumormarker
- Mikrobiologische Befunde

Antworte NUR mit der Kategorie: ARZTBRIEF, BEFUNDBERICHT oder LABORWERTE"""

    def _get_default_preprocessing(self) -> str:
        """Get default preprocessing prompt."""
        return """Entferne alle persönlichen und identifizierbaren Daten aus diesem medizinischen Text, behalte aber ALLE medizinischen Informationen bei.

ENTFERNE FOLGENDE DATEN:
- Namen (Vor- und Nachnamen)
- Adressen und Postleitzahlen
- Telefonnummern
- E-Mail-Adressen
- Geburtsdaten
- Versichertennummern
- Patientennummern
- Aktenzeichen
- Arztpraxis/Krankenhaus-spezifische IDs

BEHALTE ALLE MEDIZINISCHEN INFORMATIONEN:
- Diagnosen und ICD-Codes
- Symptombeschreibungen
- Laborwerte und Messwerte
- Medikamente und Dosierungen
- Behandlungsverläufe
- Untersuchungsergebnisse
- Medizinische Fachbegriffe
- Zeitangaben ohne Personenbezug
- Referenzbereiche

ERSETZUNG:
- Ersetze entfernte Daten durch generische Platzhalter wie [Patient], [Arzt], [Datum], etc.
- Behalte die Textstruktur und Lesbarkeit bei

Gib den anonymisierten Text zurück."""

    def _get_default_grammar_check(self) -> str:
        """Get default grammar check prompt."""
        return """Korrigiere Grammatik, Rechtschreibung und Interpunktion in diesem deutschen medizinischen Text.

BEACHTE:
- Ändere KEINE medizinischen Informationen oder Fachbegriffe
- Korrigiere nur sprachliche Fehler
- Behalte die ursprüngliche Bedeutung bei
- Verbessere die Lesbarkeit durch korrekte Grammatik
- Achte auf korrekte Zeichensetzung
- Verwende einheitliche medizinische Terminologie

KORRIGIERE:
- Rechtschreibfehler
- Grammatikfehler
- Zeichensetzungsfehler
- Unvollständige Sätze
- Inkonsistente Schreibweisen

Gib den sprachlich korrigierten Text zurück."""

    def _get_default_language_translation(self) -> str:
        """Get default language translation prompt."""
        return """Übersetze diesen medizinischen Text akkurat in {language}.

WICHTIGE ANFORDERUNGEN:
- Behalte ALLE medizinischen Informationen exakt bei
- Übersetze medizinische Fachbegriffe korrekt
- Bewahre die Struktur und Formatierung
- Verwende die korrekte medizinische Terminologie der Zielsprache
- Behalte Zahlen, Dosierungen und Messwerte unverändert
- Achte auf kulturelle Anpassungen bei Bedarf

BEHALTE UNVERÄNDERT:
- Medikamentennamen (falls international gebräuchlich)
- ICD-Codes
- Laborwerte und Referenzbereiche
- Dosierungsangaben
- Medizinische Abkürzungen (wenn üblich)

Gib den übersetzten Text zurück."""

    def get_global_prompts(self) -> GlobalPrompts:
        """Get current global prompts."""
        if self._prompts_cache is None:
            return self._load_global_prompts()
        return self._prompts_cache

    def update_global_prompts(
        self,
        prompts: GlobalPrompts,
        user: Optional[str] = None
    ) -> bool:
        """
        Update global prompts.

        Args:
            prompts: Updated global prompts
            user: Username of the person making the change

        Returns:
            True if successful, False otherwise
        """
        try:
            # Update metadata
            prompts.version += 1
            prompts.last_modified = datetime.now().isoformat()
            prompts.modified_by = user or "admin"

            # Save to file
            success = self._save_global_prompts(prompts)
            if success:
                self._prompts_cache = prompts
                logger.info(f"✅ Global prompts updated by {user or 'unknown'} (version {prompts.version})")

            return success

        except Exception as e:
            logger.error(f"❌ Failed to update global prompts: {e}")
            return False

    def _save_global_prompts(self, prompts: GlobalPrompts) -> bool:
        """Save global prompts to file."""
        try:
            # Convert to dictionary for JSON serialization
            data = asdict(prompts)

            # Create backup if file exists
            if self.global_prompts_file.exists():
                self._create_backup()

            # Save to file
            with open(self.global_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Global prompts saved to {self.global_prompts_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save global prompts: {e}")
            return False

    def _create_backup(self):
        """Create a backup of the current global prompts file."""
        try:
            if self.global_prompts_file.exists():
                backup_dir = self.config_dir / "backups"
                backup_dir.mkdir(exist_ok=True)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"global_prompts_{timestamp}.json"

                # Copy current file to backup
                import shutil
                shutil.copy2(self.global_prompts_file, backup_file)
                logger.info(f"📂 Created global prompts backup: {backup_file}")

                # Cleanup old backups (keep last 10)
                self._cleanup_old_backups()

        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")

    def _cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backup files, keeping only the most recent ones."""
        try:
            backup_dir = self.config_dir / "backups"
            if not backup_dir.exists():
                return

            # Find all global prompts backups
            backups = sorted(
                backup_dir.glob("global_prompts_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove old backups
            for backup in backups[keep_count:]:
                backup.unlink()
                logger.debug(f"🗑️ Removed old backup: {backup}")

        except Exception as e:
            logger.error(f"❌ Failed to cleanup backups: {e}")

    def reset_to_defaults(self) -> bool:
        """Reset global prompts to default values."""
        try:
            logger.info("🔄 Resetting global prompts to defaults")

            # Create backup before resetting
            if self.global_prompts_file.exists():
                self._create_backup()

            # Create and save defaults
            default_prompts = GlobalPrompts(
                medical_validation_prompt=self._get_default_medical_validation(),
                classification_prompt=self._get_default_classification(),
                preprocessing_prompt=self._get_default_preprocessing(),
                grammar_check_prompt=self._get_default_grammar_check(),
                language_translation_prompt=self._get_default_language_translation(),
                version=1,
                last_modified=datetime.now().isoformat(),
                modified_by="system_reset"
            )

            success = self._save_global_prompts(default_prompts)
            if success:
                self._prompts_cache = default_prompts

            return success

        except Exception as e:
            logger.error(f"❌ Failed to reset global prompts: {e}")
            return False

    def export_global_prompts(self) -> Dict[str, Any]:
        """Export global prompts for backup or sharing."""
        try:
            prompts = self.get_global_prompts()
            return {
                "export_date": datetime.now().isoformat(),
                "version": 1,
                "type": "global_prompts",
                "prompts": asdict(prompts)
            }

        except Exception as e:
            logger.error(f"❌ Failed to export global prompts: {e}")
            return {}

    def import_global_prompts(
        self,
        import_data: Dict[str, Any],
        user: Optional[str] = None
    ) -> bool:
        """Import global prompts from exported data."""
        try:
            if "prompts" not in import_data:
                logger.error("Invalid import data: missing 'prompts' key")
                return False

            prompts_data = import_data["prompts"]

            # Create GlobalPrompts object from imported data
            prompts = GlobalPrompts(
                medical_validation_prompt=prompts_data.get("medical_validation_prompt", self._get_default_medical_validation()),
                classification_prompt=prompts_data.get("classification_prompt", self._get_default_classification()),
                preprocessing_prompt=prompts_data.get("preprocessing_prompt", self._get_default_preprocessing()),
                grammar_check_prompt=prompts_data.get("grammar_check_prompt", self._get_default_grammar_check()),
                language_translation_prompt=prompts_data.get("language_translation_prompt", self._get_default_language_translation()),
                version=prompts_data.get("version", 1),
                last_modified=datetime.now().isoformat(),
                modified_by=user or "import"
            )

            return self.update_global_prompts(prompts, user)

        except Exception as e:
            logger.error(f"❌ Failed to import global prompts: {e}")
            return False

    def get_prompt_by_type(self, prompt_type: str) -> Optional[str]:
        """Get a specific global prompt by type."""
        prompts = self.get_global_prompts()

        prompt_map = {
            "medical_validation": prompts.medical_validation_prompt,
            "classification": prompts.classification_prompt,
            "preprocessing": prompts.preprocessing_prompt,
            "grammar_check": prompts.grammar_check_prompt,
            "language_translation": prompts.language_translation_prompt
        }

        return prompt_map.get(prompt_type)

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about global prompts usage."""
        prompts = self.get_global_prompts()

        return {
            "version": prompts.version,
            "last_modified": prompts.last_modified,
            "modified_by": prompts.modified_by,
            "prompts_count": 5,  # Number of global prompts
            "average_prompt_length": sum([
                len(prompts.medical_validation_prompt),
                len(prompts.classification_prompt),
                len(prompts.preprocessing_prompt),
                len(prompts.grammar_check_prompt),
                len(prompts.language_translation_prompt)
            ]) // 5,
            "file_exists": self.global_prompts_file.exists(),
            "file_size_kb": self.global_prompts_file.stat().st_size // 1024 if self.global_prompts_file.exists() else 0
        }