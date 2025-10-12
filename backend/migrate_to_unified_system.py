#!/usr/bin/env python3
"""
Migration Script: Old System → Unified Universal System

This script migrates from the old document-specific prompt system
to the new unified universal prompt system.
"""

import logging
import os
import sys
from datetime import datetime
from enum import Enum
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the Python path to allow imports from 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.database.unified_models import Base as UnifiedBase
from app.database.models import Base as OldBase, DocumentPromptsDB, PipelineStepConfigDB
# Define DocumentClass directly to avoid pydantic dependency
class DocumentClass(str, Enum):
    ARZTBRIEF = "ARZTBRIEF"
    BEFUNDBERICHT = "BEFUNDBERICHT"
    LABORWERTE = "LABORWERTE"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_to_unified_system():
    """Migrate from old system to unified universal system."""
    
    try:
        # Get database connection
        engine = create_engine(settings.database_url)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with Session() as session:
            logger.info("🚀 Starting migration to unified universal system...")
            
            # Step 1: Create new unified tables
            logger.info("📋 Creating unified database tables...")
            UnifiedBase.metadata.create_all(bind=engine)
            logger.info("✅ Unified tables created successfully")
            
            # Step 2: Migrate universal prompts
            logger.info("🌐 Migrating universal prompts...")
            migrate_universal_prompts(session)
            
            # Step 3: Migrate document-specific prompts
            logger.info("📝 Migrating document-specific prompts...")
            migrate_document_specific_prompts(session)
            
            # Step 4: Migrate pipeline step configurations
            logger.info("⚙️ Migrating pipeline step configurations...")
            migrate_pipeline_steps(session)
            
            # Step 5: Create default data if needed
            logger.info("🌱 Creating default data...")
            create_default_data(session)
            
            session.commit()
            logger.info("✅ Migration completed successfully!")
            
            # Step 6: Verify migration
            logger.info("🔍 Verifying migration...")
            verify_migration(session)
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def migrate_universal_prompts(session):
    """Migrate universal prompts from old system."""
    from app.database.unified_models import UniversalPromptsDB
    
    # Check if universal prompts already exist
    existing = session.query(UniversalPromptsDB).first()
    if existing:
        logger.info("ℹ️ Universal prompts already exist, skipping migration")
        return
    
    # Get prompts from old system (use ARZTBRIEF as template)
    old_prompts = session.query(DocumentPromptsDB).filter_by(
        document_type="ARZTBRIEF"
    ).first()
    
    if old_prompts:
        # Migrate from old system
        universal_prompts = UniversalPromptsDB(
            medical_validation_prompt=old_prompts.medical_validation_prompt,
            classification_prompt=old_prompts.classification_prompt,
            preprocessing_prompt=old_prompts.preprocessing_prompt,
            grammar_check_prompt=old_prompts.grammar_check_prompt,
            language_translation_prompt=old_prompts.language_translation_prompt,
            version=1,
            last_modified=datetime.now(),
            modified_by="migration_script",
            is_active=True
        )
    else:
        # Create default universal prompts
        universal_prompts = UniversalPromptsDB(
            medical_validation_prompt="Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
            classification_prompt="Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief, einen Befundbericht oder Laborwerte handelt. Antworte NUR mit dem erkannten Typ (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE).",
            preprocessing_prompt="Entferne aus dem folgenden medizinischen Text alle persönlichen Identifikatoren (Namen, Adressen, Geburtsdaten, Telefonnummern, E-Mail-Adressen, Patientennummern), aber behalte alle medizinischen Informationen und den Kontext bei. Ersetze entfernte PII durch '[ENTFERNT]'.",
            grammar_check_prompt="Korrigiere die deutsche Grammatik, Rechtschreibung und Zeichensetzung im folgenden Text. Achte auf einen flüssigen und professionellen Stil. Gib nur den korrigierten Text zurück.",
            language_translation_prompt="Übersetze den folgenden Text EXAKT in {language}. Achte auf präzise medizinische Terminologie, wo angebracht, aber halte den Ton patientenfreundlich. Gib nur die Übersetzung zurück.",
            version=1,
            last_modified=datetime.now(),
            modified_by="migration_script",
            is_active=True
        )
    
    session.add(universal_prompts)
    logger.info("✅ Universal prompts migrated successfully")

def migrate_document_specific_prompts(session):
    """Migrate document-specific prompts from old system."""
    from app.database.unified_models import DocumentSpecificPromptsDB
    
    # Get all old document prompts
    old_prompts = session.query(DocumentPromptsDB).all()
    
    for old_prompt in old_prompts:
        # Check if document-specific prompts already exist
        existing = session.query(DocumentSpecificPromptsDB).filter_by(
            document_type=old_prompt.document_type
        ).first()
        
        if existing:
            logger.info(f"ℹ️ Document-specific prompts for {old_prompt.document_type} already exist, skipping")
            continue
        
        # Create document-specific prompts
        specific_prompts = DocumentSpecificPromptsDB(
            document_type=old_prompt.document_type,
            translation_prompt=old_prompt.translation_prompt,
            fact_check_prompt=old_prompt.fact_check_prompt,
            final_check_prompt=old_prompt.final_check_prompt,
            formatting_prompt=old_prompt.formatting_prompt,
            version=old_prompt.version,
            last_modified=datetime.now(),
            modified_by="migration_script"
        )
        
        session.add(specific_prompts)
        logger.info(f"✅ Document-specific prompts for {old_prompt.document_type} migrated successfully")

def migrate_pipeline_steps(session):
    """Migrate pipeline step configurations."""
    from app.database.unified_models import UniversalPipelineStepConfigDB
    
    # Check if pipeline steps already exist
    existing = session.query(UniversalPipelineStepConfigDB).first()
    if existing:
        logger.info("ℹ️ Pipeline steps already exist, skipping migration")
        return
    
    # Create default pipeline steps
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
            modified_by="migration_script"
        )
        session.add(step)
    
    logger.info("✅ Pipeline steps migrated successfully")

def create_default_data(session):
    """Create default data if needed."""
    from app.database.unified_models import SystemSettingsDB
    
    # Create default system settings
    default_settings = [
        ("app_version", "2.0.0", "string", "Current application version", False),
        ("max_file_size_mb", "50", "int", "Maximum file size in MB", False),
        ("max_processing_time_seconds", "300", "int", "Maximum processing time in seconds", False),
        ("cleanup_interval_minutes", "60", "int", "Cleanup interval in minutes", False),
        ("default_confidence_threshold", "0.7", "float", "Default confidence threshold for AI operations", False),
        ("enable_ai_logging", "true", "bool", "Enable comprehensive AI interaction logging", False),
        ("settings_access_code", "milan", "string", "Access code for settings page", True),
        ("use_optimized_pipeline", "true", "bool", "Use optimized pipeline processing", False),
        ("pipeline_cache_timeout", "300", "int", "Pipeline cache timeout in seconds", False),
        ("enable_medical_validation", "true", "bool", "Enable medical content validation", False),
        ("enable_classification", "true", "bool", "Enable document classification", False),
        ("enable_preprocessing", "true", "bool", "Enable text preprocessing", False),
        ("enable_translation", "true", "bool", "Enable translation", False),
        ("enable_fact_check", "true", "bool", "Enable fact checking", False),
        ("enable_grammar_check", "true", "bool", "Enable grammar checking", False),
        ("enable_language_translation", "true", "bool", "Enable language translation", False),
        ("enable_final_check", "true", "bool", "Enable final quality check", False),
        ("enable_formatting", "true", "bool", "Enable text formatting", False)
    ]
    
    for key, value, value_type, description, is_encrypted in default_settings:
        existing = session.query(SystemSettingsDB).filter_by(key=key).first()
        if not existing:
            setting = SystemSettingsDB(
                key=key,
                value=value,
                value_type=value_type,
                description=description,
                is_encrypted=is_encrypted,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                updated_by="migration_script"
            )
            session.add(setting)
    
    logger.info("✅ Default system settings created")

def verify_migration(session):
    """Verify that migration was successful."""
    from app.database.unified_models import UniversalPromptsDB, DocumentSpecificPromptsDB, UniversalPipelineStepConfigDB
    
    # Check universal prompts
    universal_count = session.query(UniversalPromptsDB).count()
    logger.info(f"📊 Universal prompts: {universal_count} records")
    
    # Check document-specific prompts
    specific_count = session.query(DocumentSpecificPromptsDB).count()
    logger.info(f"📊 Document-specific prompts: {specific_count} records")
    
    # Check pipeline steps
    steps_count = session.query(UniversalPipelineStepConfigDB).count()
    logger.info(f"📊 Pipeline steps: {steps_count} records")
    
    # Check system settings
    from app.database.unified_models import SystemSettingsDB
    settings_count = session.query(SystemSettingsDB).count()
    logger.info(f"📊 System settings: {settings_count} records")
    
    logger.info("🎉 Migration verification completed!")

if __name__ == "__main__":
    if migrate_to_unified_system():
        logger.info("🎉 Migration to unified universal system completed successfully!")
    else:
        logger.error("💥 Migration to unified universal system failed!")
        sys.exit(1)
