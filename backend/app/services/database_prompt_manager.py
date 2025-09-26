"""
Database-based prompt manager
"""

import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.models.document_types import DocumentClass, DocumentPrompts
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)

class DatabasePromptManager:
    """Database-based prompt manager"""
    
    def __init__(self, session: Session):
        self.session = session
        self.db_service = DatabaseService(session)

    def load_prompts(self, document_type: DocumentClass) -> DocumentPrompts:
        """Load prompts from database"""
        try:
            prompts = self.db_service.get_document_prompts(document_type)
            if prompts:
                return prompts
            
            # If no prompts found, create default ones
            logger.info(f"No prompts found for {document_type.value}, creating defaults")
            return self._create_default_prompts(document_type)
            
        except Exception as e:
            logger.error(f"Failed to load prompts for {document_type.value}: {e}")
            return self._create_default_prompts(document_type)

    def save_prompts(self, document_type: DocumentClass, prompts: DocumentPrompts) -> bool:
        """Save prompts to database"""
        try:
            return self.db_service.save_document_prompts(prompts)
        except Exception as e:
            logger.error(f"Failed to save prompts for {document_type.value}: {e}")
            return False

    def reset_prompts(self, document_type: DocumentClass) -> bool:
        """Reset prompts to default values"""
        try:
            # Delete existing prompts
            self.db_service.reset_document_prompts(document_type)
            
            # Create default prompts
            default_prompts = self._create_default_prompts(document_type)
            return self.save_prompts(document_type, default_prompts)
            
        except Exception as e:
            logger.error(f"Failed to reset prompts for {document_type.value}: {e}")
            return False

    def _create_default_prompts(self, document_type: DocumentClass) -> DocumentPrompts:
        """Create default prompts for a document type"""
        from app.models.document_types import PipelineStepConfig
        
        # Default pipeline steps
        default_steps = {
            "medical_validation": PipelineStepConfig(
                enabled=True, order=1, 
                name="Medical Content Validation", 
                description="Validate if document contains medical content"
            ),
            "classification": PipelineStepConfig(
                enabled=True, order=2, 
                name="Document Classification", 
                description="Classify document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)"
            ),
            "preprocessing": PipelineStepConfig(
                enabled=True, order=3, 
                name="Preprocessing", 
                description="Remove PII and clean text"
            ),
            "translation": PipelineStepConfig(
                enabled=True, order=4, 
                name="Translation", 
                description="Translate to simple language"
            ),
            "fact_check": PipelineStepConfig(
                enabled=True, order=5, 
                name="Fact Check", 
                description="Verify medical accuracy"
            ),
            "grammar_check": PipelineStepConfig(
                enabled=True, order=6, 
                name="Grammar Check", 
                description="Correct German grammar"
            ),
            "language_translation": PipelineStepConfig(
                enabled=True, order=7, 
                name="Language Translation", 
                description="Translate to target language"
            ),
            "final_check": PipelineStepConfig(
                enabled=True, order=8, 
                name="Final Check", 
                description="Final quality assurance"
            ),
            "formatting": PipelineStepConfig(
                enabled=True, order=9, 
                name="Formatting", 
                description="Apply text formatting"
            )
        }
        
        # Default prompts based on document type
        if document_type == DocumentClass.ARZTBRIEF:
            return DocumentPrompts(
                document_type=document_type,
                medical_validation_prompt="Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
                classification_prompt="Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief handelt.",
                preprocessing_prompt="Entferne persönliche Daten aber behalte alle medizinischen Informationen.",
                translation_prompt="Übersetze diesen Arztbrief in einfache, verständliche Sprache für Patienten.",
                fact_check_prompt="Prüfe die medizinischen Fakten in diesem Arztbrief auf Korrektheit.",
                grammar_check_prompt="Korrigiere die deutsche Grammatik und Rechtschreibung.",
                language_translation_prompt="Übersetze diesen Text in {language}.",
                final_check_prompt="Führe eine finale Qualitätskontrolle durch.",
                formatting_prompt="Formatiere diesen Text für optimale Lesbarkeit mit klaren Überschriften und Bullet Points.",
                pipeline_steps=default_steps,
                version=1,
                modified_by="system"
            )
        elif document_type == DocumentClass.BEFUNDBERICHT:
            return DocumentPrompts(
                document_type=document_type,
                medical_validation_prompt="Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
                classification_prompt="Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Befundbericht handelt.",
                preprocessing_prompt="Entferne persönliche Daten aber behalte alle medizinischen Informationen.",
                translation_prompt="Übersetze diesen Befundbericht in einfache, verständliche Sprache für Patienten.",
                fact_check_prompt="Prüfe die medizinischen Fakten in diesem Befundbericht auf Korrektheit.",
                grammar_check_prompt="Korrigiere die deutsche Grammatik und Rechtschreibung.",
                language_translation_prompt="Übersetze diesen Text in {language}.",
                final_check_prompt="Führe eine finale Qualitätskontrolle durch.",
                formatting_prompt="Formatiere diesen Text für optimale Lesbarkeit mit klaren Überschriften und Bullet Points.",
                pipeline_steps=default_steps,
                version=1,
                modified_by="system"
            )
        else:  # LABORWERTE
            return DocumentPrompts(
                document_type=document_type,
                medical_validation_prompt="Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
                classification_prompt="Analysiere diesen medizinischen Text und bestimme, ob es sich um Laborwerte handelt.",
                preprocessing_prompt="Entferne persönliche Daten aber behalte alle medizinischen Informationen.",
                translation_prompt="Übersetze diese Laborwerte in einfache, verständliche Sprache für Patienten.",
                fact_check_prompt="Prüfe die medizinischen Fakten in diesen Laborwerten auf Korrektheit.",
                grammar_check_prompt="Korrigiere die deutsche Grammatik und Rechtschreibung.",
                language_translation_prompt="Übersetze diesen Text in {language}.",
                final_check_prompt="Führe eine finale Qualitätskontrolle durch.",
                formatting_prompt="Formatiere diesen Text für optimale Lesbarkeit mit klaren Überschriften und Bullet Points.",
                pipeline_steps=default_steps,
                version=1,
                modified_by="system"
            )
