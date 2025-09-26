"""
Unified Prompt Manager

This is the new, unified prompt management system that replaces
all old document-specific and file-based prompt systems.
It only uses the database and provides a clean, universal interface.
"""

import logging
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.document_types import DocumentClass
from app.database.unified_models import (
    UniversalPromptsDB, 
    DocumentSpecificPromptsDB, 
    UniversalPipelineStepConfigDB
)

logger = logging.getLogger(__name__)

class UnifiedPromptManager:
    """
    Unified prompt manager that handles both universal and document-specific prompts.
    This replaces all old prompt management systems.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    # ==================== UNIVERSAL PROMPTS ====================
    
    def get_universal_prompts(self) -> Optional[UniversalPromptsDB]:
        """Get universal prompts from database."""
        try:
            return self.session.query(UniversalPromptsDB).filter_by(is_active=True).first()
        except Exception as e:
            logger.error(f"Failed to get universal prompts: {e}")
            return None
    
    def save_universal_prompts(self, prompts: UniversalPromptsDB) -> bool:
        """Save universal prompts to database."""
        try:
            # Update existing or create new
            existing = self.session.query(UniversalPromptsDB).filter_by(is_active=True).first()
            if existing:
                # Update existing
                for key, value in prompts.__dict__.items():
                    if not key.startswith('_') and key != 'id':
                        setattr(existing, key, value)
                existing.last_modified = datetime.now()
            else:
                # Create new
                prompts.last_modified = datetime.now()
                self.session.add(prompts)
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save universal prompts: {e}")
            self.session.rollback()
            return False
    
    def create_default_universal_prompts(self) -> UniversalPromptsDB:
        """Create default universal prompts."""
        return UniversalPromptsDB(
            medical_validation_prompt="Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
            classification_prompt="Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief, einen Befundbericht oder Laborwerte handelt. Antworte NUR mit dem erkannten Typ (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE).",
            preprocessing_prompt="Entferne aus dem folgenden medizinischen Text alle persönlichen Identifikatoren (Namen, Adressen, Geburtsdaten, Telefonnummern, E-Mail-Adressen, Patientennummern), aber behalte alle medizinischen Informationen und den Kontext bei. Ersetze entfernte PII durch '[ENTFERNT]'.",
            grammar_check_prompt="Korrigiere die deutsche Grammatik, Rechtschreibung und Zeichensetzung im folgenden Text. Achte auf einen flüssigen und professionellen Stil. Gib nur den korrigierten Text zurück.",
            language_translation_prompt="Übersetze den folgenden Text EXAKT in {language}. Achte auf präzise medizinische Terminologie, wo angebracht, aber halte den Ton patientenfreundlich. Gib nur die Übersetzung zurück.",
            version=1,
            last_modified=datetime.now(),
            modified_by="system_default",
            is_active=True
        )
    
    # ==================== DOCUMENT-SPECIFIC PROMPTS ====================
    
    def get_document_specific_prompts(self, document_type: DocumentClass) -> Optional[DocumentSpecificPromptsDB]:
        """Get document-specific prompts for a document type."""
        try:
            return self.session.query(DocumentSpecificPromptsDB).filter_by(
                document_type=document_type.value.upper()
            ).first()
        except Exception as e:
            logger.error(f"Failed to get document-specific prompts for {document_type.value}: {e}")
            return None
    
    def save_document_specific_prompts(self, document_type: DocumentClass, prompts: DocumentSpecificPromptsDB) -> bool:
        """Save document-specific prompts to database."""
        try:
            # Update existing or create new
            existing = self.session.query(DocumentSpecificPromptsDB).filter_by(
                document_type=document_type.value.upper()
            ).first()
            
            if existing:
                # Update existing
                for key, value in prompts.__dict__.items():
                    if not key.startswith('_') and key != 'id':
                        setattr(existing, key, value)
                existing.last_modified = datetime.now()
            else:
                # Create new
                prompts.document_type = document_type.value.upper()
                prompts.last_modified = datetime.now()
                self.session.add(prompts)
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save document-specific prompts for {document_type.value}: {e}")
            self.session.rollback()
            return False
    
    def create_default_document_specific_prompts(self, document_type: DocumentClass) -> DocumentSpecificPromptsDB:
        """Create default document-specific prompts for a document type."""
        # Different prompts based on document type
        if document_type == DocumentClass.ARZTBRIEF:
            return DocumentSpecificPromptsDB(
                translation_prompt="Übersetze diesen Arztbrief in einfache, patientenfreundliche Sprache. Verwende kurze Sätze und vermeide medizinische Fachbegriffe. Strukturiere den Text mit klaren Abschnitten.",
                fact_check_prompt="Überprüfe diesen Arztbrief auf medizinische Korrektheit und Vollständigkeit. Achte besonders auf Diagnosen, Behandlungsempfehlungen und Medikamentennamen.",
                final_check_prompt="Führe eine finale Qualitätskontrolle dieses Arztbriefes durch. Prüfe auf Verständlichkeit, Vollständigkeit und patientenfreundliche Formulierung.",
                formatting_prompt="Formatiere diesen Arztbrief mit klaren Überschriften, Abschnitten und einer logischen Struktur. Verwende Bullet Points für Listen und Medikamente."
            )
        elif document_type == DocumentClass.BEFUNDBERICHT:
            return DocumentSpecificPromptsDB(
                translation_prompt="Übersetze diesen Befundbericht in verständliche Sprache. Erkläre medizinische Befunde in einfachen Worten und strukturiere die Informationen übersichtlich.",
                fact_check_prompt="Überprüfe diesen Befundbericht auf medizinische Genauigkeit. Achte besonders auf Laborwerte, Messungen und diagnostische Befunde.",
                final_check_prompt="Führe eine finale Qualitätskontrolle dieses Befundberichtes durch. Prüfe auf Vollständigkeit der Befunde und Verständlichkeit der Erklärungen.",
                formatting_prompt="Formatiere diesen Befundbericht mit klaren Abschnitten für verschiedene Befunde. Verwende Tabellen für Laborwerte und strukturierte Listen."
            )
        else:  # LABORWERTE
            return DocumentSpecificPromptsDB(
                translation_prompt="Übersetze diese Laborwerte in verständliche Sprache. Erkläre was jeder Wert bedeutet und ob er normal, erhöht oder erniedrigt ist.",
                fact_check_prompt="Überprüfe diese Laborwerte auf Plausibilität und Vollständigkeit. Achte auf Referenzbereiche und Einheiten.",
                final_check_prompt="Führe eine finale Qualitätskontrolle dieser Laborwerte durch. Prüfe auf Vollständigkeit und Verständlichkeit der Erklärungen.",
                formatting_prompt="Formatiere diese Laborwerte in einer übersichtlichen Tabelle mit Werten, Referenzbereichen und Erklärungen."
            )
    
    # ==================== PIPELINE STEP CONFIGURATION ====================
    
    def get_pipeline_steps(self) -> List[UniversalPipelineStepConfigDB]:
        """Get all pipeline step configurations."""
        try:
            return self.session.query(UniversalPipelineStepConfigDB).order_by(
                UniversalPipelineStepConfigDB.order
            ).all()
        except Exception as e:
            logger.error(f"Failed to get pipeline steps: {e}")
            return []
    
    def update_pipeline_step(self, step_name: str, enabled: bool) -> bool:
        """Update a pipeline step configuration."""
        try:
            step = self.session.query(UniversalPipelineStepConfigDB).filter_by(
                step_name=step_name.upper()
            ).first()
            
            if step:
                step.enabled = enabled
                step.last_modified = datetime.now()
                step.modified_by = "unified_manager"
                self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update pipeline step {step_name}: {e}")
            self.session.rollback()
            return False
    
    def create_default_pipeline_steps(self) -> bool:
        """Create default pipeline step configurations."""
        try:
            # Check if steps already exist
            if self.session.query(UniversalPipelineStepConfigDB).count() > 0:
                return True
            
            steps = [
                ("MEDICAL_VALIDATION", True, 1, "Medical Content Validation", "Validate if document contains medical content"),
                ("CLASSIFICATION", True, 2, "Document Classification", "Classify document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)"),
                ("PREPROCESSING", True, 3, "Preprocessing", "Remove PII and clean text"),
                ("TRANSLATION", True, 4, "Translation", "Translate to simple language"),
                ("FACT_CHECK", True, 5, "Fact Check", "Verify medical accuracy"),
                ("GRAMMAR_CHECK", True, 6, "Grammar Check", "Correct German grammar"),
                ("LANGUAGE_TRANSLATION", True, 7, "Language Translation", "Translate to target language"),
                ("FINAL_CHECK", True, 8, "Final Check", "Final quality assurance"),
                ("FORMATTING", True, 9, "Formatting", "Apply text formatting")
            ]
            
            for step_name, enabled, order, name, description in steps:
                step = UniversalPipelineStepConfigDB(
                    step_name=step_name,
                    enabled=enabled,
                    order=order,
                    name=name,
                    description=description,
                    last_modified=datetime.now(),
                    modified_by="system_default"
                )
                self.session.add(step)
            
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to create default pipeline steps: {e}")
            self.session.rollback()
            return False
    
    # ==================== COMBINED PROMPT ACCESS ====================
    
    def get_combined_prompts(self, document_type: DocumentClass) -> Dict[str, str]:
        """
        Get combined prompts for a document type.
        Returns universal prompts + document-specific prompts as a single dictionary.
        """
        try:
            # Get universal prompts
            universal = self.get_universal_prompts()
            if not universal:
                universal = self.create_default_universal_prompts()
                self.save_universal_prompts(universal)
            
            # Get document-specific prompts
            specific = self.get_document_specific_prompts(document_type)
            if not specific:
                specific = self.create_default_document_specific_prompts(document_type)
                self.save_document_specific_prompts(document_type, specific)
            
            # Combine prompts
            combined = {
                # Universal prompts
                "medical_validation_prompt": universal.medical_validation_prompt,
                "classification_prompt": universal.classification_prompt,
                "preprocessing_prompt": universal.preprocessing_prompt,
                "grammar_check_prompt": universal.grammar_check_prompt,
                "language_translation_prompt": universal.language_translation_prompt,
                
                # Document-specific prompts
                "translation_prompt": specific.translation_prompt,
                "fact_check_prompt": specific.fact_check_prompt,
                "final_check_prompt": specific.final_check_prompt,
                "formatting_prompt": specific.formatting_prompt
            }
            
            return combined
        except Exception as e:
            logger.error(f"Failed to get combined prompts for {document_type.value}: {e}")
            return {}
    
    def is_pipeline_step_enabled(self, step_name: str, document_type: DocumentClass = None) -> bool:
        """Check if a pipeline step is enabled."""
        try:
            # First check universal pipeline steps
            universal_step = self.session.query(UniversalPipelineStepConfigDB).filter_by(
                step_name=step_name.upper()
            ).first()
            
            if universal_step:
                return universal_step.enabled
            
            # If not found in universal steps, check document-specific steps
            if document_type:
                from app.database.models import PipelineStepConfigDB
                doc_specific_step = self.session.query(PipelineStepConfigDB).join(
                    DocumentPromptsDB, PipelineStepConfigDB.document_prompts_id == DocumentPromptsDB.id
                ).filter(
                    DocumentPromptsDB.document_type == document_type,
                    PipelineStepConfigDB.step_name == step_name.upper()
                ).first()
                
                if doc_specific_step:
                    return doc_specific_step.enabled
            
            # Default to enabled if not found
            return True
        except Exception as e:
            logger.error(f"Failed to check pipeline step {step_name}: {e}")
            return True
