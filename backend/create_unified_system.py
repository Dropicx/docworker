#!/usr/bin/env python3
"""
Create Unified Universal System

This script creates the new unified universal prompt system from scratch.
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_unified_system():
    """Create the unified universal system from scratch."""
    
    try:
        # Get database connection
        engine = create_engine(settings.database_url)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with Session() as session:
            logger.info("🚀 Creating unified universal system...")
            
            # Step 1: Create new unified tables
            logger.info("📋 Creating unified database tables...")
            UnifiedBase.metadata.create_all(bind=engine)
            logger.info("✅ Unified tables created successfully")
            
            # Step 2: Create default data
            logger.info("🌱 Creating default data...")
            create_default_data(session)
            
            session.commit()
            logger.info("✅ Unified system created successfully!")
            
            # Step 3: Verify creation
            logger.info("🔍 Verifying system...")
            verify_system(session)
            
            return True
            
    except Exception as e:
        logger.error(f"❌ System creation failed: {e}")
        return False

def create_default_data(session):
    """Create default data for the unified system."""
    
    # Insert universal prompts
    logger.info("🌐 Creating universal prompts...")
    session.execute(text("""
        INSERT OR IGNORE INTO universal_prompts (
            medical_validation_prompt, classification_prompt, preprocessing_prompt,
            grammar_check_prompt, language_translation_prompt, version, last_modified, modified_by, is_active
        ) VALUES (
            :medical_validation_prompt, :classification_prompt, :preprocessing_prompt,
            :grammar_check_prompt, :language_translation_prompt, :version, CURRENT_TIMESTAMP, :modified_by, :is_active
        )
    """), {
        'medical_validation_prompt': 'Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH',
        'classification_prompt': 'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief, einen Befundbericht oder Laborwerte handelt. Antworte NUR mit dem erkannten Typ (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE).',
        'preprocessing_prompt': 'Entferne aus dem folgenden medizinischen Text alle persönlichen Identifikatoren (Namen, Adressen, Geburtsdaten, Telefonnummern, E-Mail-Adressen, Patientennummern), aber behalte alle medizinischen Informationen und den Kontext bei. Ersetze entfernte PII durch \'[ENTFERNT]\'.',
        'grammar_check_prompt': 'Korrigiere die deutsche Grammatik, Rechtschreibung und Zeichensetzung im folgenden Text. Achte auf einen flüssigen und professionellen Stil. Gib nur den korrigierten Text zurück.',
        'language_translation_prompt': 'Übersetze den folgenden Text EXAKT in {language}. Achte auf präzise medizinische Terminologie, wo angebracht, aber halte den Ton patientenfreundlich. Gib nur die Übersetzung zurück.',
        'version': 1,
        'modified_by': 'system_creation',
        'is_active': True
    })
    
    # Insert document-specific prompts for ARZTBRIEF
    logger.info("📝 Creating document-specific prompts for ARZTBRIEF...")
    session.execute(text("""
        INSERT OR IGNORE INTO document_specific_prompts (
            document_type, translation_prompt, fact_check_prompt, final_check_prompt, formatting_prompt,
            version, last_modified, modified_by
        ) VALUES (
            :document_type, :translation_prompt, :fact_check_prompt, :final_check_prompt, :formatting_prompt,
            :version, CURRENT_TIMESTAMP, :modified_by
        )
    """), {
        'document_type': 'ARZTBRIEF',
        'translation_prompt': 'Übersetze diesen Arztbrief in einfache, patientenfreundliche Sprache. Verwende kurze Sätze und vermeide medizinische Fachbegriffe. Strukturiere den Text mit klaren Abschnitten.',
        'fact_check_prompt': 'Überprüfe diesen Arztbrief auf medizinische Korrektheit und Vollständigkeit. Achte besonders auf Diagnosen, Behandlungsempfehlungen und Medikamentennamen.',
        'final_check_prompt': 'Führe eine finale Qualitätskontrolle dieses Arztbriefes durch. Prüfe auf Verständlichkeit, Vollständigkeit und patientenfreundliche Formulierung.',
        'formatting_prompt': 'Formatiere diesen Arztbrief mit klaren Überschriften, Abschnitten und einer logischen Struktur. Verwende Bullet Points für Listen und Medikamente.',
        'version': 1,
        'modified_by': 'system_creation'
    })
    
    # Insert document-specific prompts for BEFUNDBERICHT
    logger.info("📝 Creating document-specific prompts for BEFUNDBERICHT...")
    session.execute(text("""
        INSERT OR IGNORE INTO document_specific_prompts (
            document_type, translation_prompt, fact_check_prompt, final_check_prompt, formatting_prompt,
            version, last_modified, modified_by
        ) VALUES (
            :document_type, :translation_prompt, :fact_check_prompt, :final_check_prompt, :formatting_prompt,
            :version, CURRENT_TIMESTAMP, :modified_by
        )
    """), {
        'document_type': 'BEFUNDBERICHT',
        'translation_prompt': 'Übersetze diesen Befundbericht in verständliche Sprache. Erkläre medizinische Befunde in einfachen Worten und strukturiere die Informationen übersichtlich.',
        'fact_check_prompt': 'Überprüfe diesen Befundbericht auf medizinische Genauigkeit. Achte besonders auf Laborwerte, Messungen und diagnostische Befunde.',
        'final_check_prompt': 'Führe eine finale Qualitätskontrolle dieses Befundberichtes durch. Prüfe auf Vollständigkeit der Befunde und Verständlichkeit der Erklärungen.',
        'formatting_prompt': 'Formatiere diesen Befundbericht mit klaren Abschnitten für verschiedene Befunde. Verwende Tabellen für Laborwerte und strukturierte Listen.',
        'version': 1,
        'modified_by': 'system_creation'
    })
    
    # Insert document-specific prompts for LABORWERTE
    logger.info("📝 Creating document-specific prompts for LABORWERTE...")
    session.execute(text("""
        INSERT OR IGNORE INTO document_specific_prompts (
            document_type, translation_prompt, fact_check_prompt, final_check_prompt, formatting_prompt,
            version, last_modified, modified_by
        ) VALUES (
            :document_type, :translation_prompt, :fact_check_prompt, :final_check_prompt, :formatting_prompt,
            :version, CURRENT_TIMESTAMP, :modified_by
        )
    """), {
        'document_type': 'LABORWERTE',
        'translation_prompt': 'Übersetze diese Laborwerte in verständliche Sprache. Erkläre was jeder Wert bedeutet und ob er normal, erhöht oder erniedrigt ist.',
        'fact_check_prompt': 'Überprüfe diese Laborwerte auf Plausibilität und Vollständigkeit. Achte auf Referenzbereiche und Einheiten.',
        'final_check_prompt': 'Führe eine finale Qualitätskontrolle dieser Laborwerte durch. Prüfe auf Vollständigkeit und Verständlichkeit der Erklärungen.',
        'formatting_prompt': 'Formatiere diese Laborwerte in einer übersichtlichen Tabelle mit Werten, Referenzbereichen und Erklärungen.',
        'version': 1,
        'modified_by': 'system_creation'
    })
    
    # Insert universal pipeline steps
    logger.info("⚙️ Creating universal pipeline steps...")
    pipeline_steps = [
        ('MEDICAL_VALIDATION', True, 1, 'Medical Content Validation', 'Validate if document contains medical content'),
        ('CLASSIFICATION', True, 2, 'Document Classification', 'Classify document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)'),
        ('PREPROCESSING', True, 3, 'Preprocessing', 'Remove PII and clean text'),
        ('TRANSLATION', True, 4, 'Translation', 'Translate to simple language'),
        ('FACT_CHECK', True, 5, 'Fact Check', 'Verify medical accuracy'),
        ('GRAMMAR_CHECK', True, 6, 'Grammar Check', 'Correct German grammar'),
        ('LANGUAGE_TRANSLATION', True, 7, 'Language Translation', 'Translate to target language'),
        ('FINAL_CHECK', True, 8, 'Final Check', 'Final quality assurance'),
        ('FORMATTING', True, 9, 'Formatting', 'Apply text formatting')
    ]
    
    for step_name, enabled, order, name, description in pipeline_steps:
        session.execute(text("""
            INSERT OR IGNORE INTO universal_pipeline_steps (
                step_name, enabled, "order", name, description, last_modified, modified_by
            ) VALUES (
                :step_name, :enabled, :order, :name, :description, CURRENT_TIMESTAMP, :modified_by
            )
        """), {
            'step_name': step_name,
            'enabled': enabled,
            'order': order,
            'name': name,
            'description': description,
            'modified_by': 'system_creation'
        })
    
    # Insert system settings
    logger.info("⚙️ Creating system settings...")
    system_settings = [
        ('app_version', '2.0.0', 'string', 'Current application version', False),
        ('max_file_size_mb', '50', 'int', 'Maximum file size in MB', False),
        ('max_processing_time_seconds', '300', 'int', 'Maximum processing time in seconds', False),
        ('cleanup_interval_minutes', '60', 'int', 'Cleanup interval in minutes', False),
        ('default_confidence_threshold', '0.7', 'float', 'Default confidence threshold for AI operations', False),
        ('enable_ai_logging', 'true', 'bool', 'Enable comprehensive AI interaction logging', False),
        ('settings_access_code', 'milan', 'string', 'Access code for settings page', True),
        ('use_optimized_pipeline', 'true', 'bool', 'Use optimized pipeline processing', False),
        ('pipeline_cache_timeout', '300', 'int', 'Pipeline cache timeout in seconds', False),
        ('enable_medical_validation', 'true', 'bool', 'Enable medical content validation', False),
        ('enable_classification', 'true', 'bool', 'Enable document classification', False),
        ('enable_preprocessing', 'true', 'bool', 'Enable text preprocessing', False),
        ('enable_translation', 'true', 'bool', 'Enable translation', False),
        ('enable_fact_check', 'true', 'bool', 'Enable fact checking', False),
        ('enable_grammar_check', 'true', 'bool', 'Enable grammar checking', False),
        ('enable_language_translation', 'true', 'bool', 'Enable language translation', False),
        ('enable_final_check', 'true', 'bool', 'Enable final quality check', False),
        ('enable_formatting', 'true', 'bool', 'Enable text formatting', False)
    ]
    
    for key, value, value_type, description, is_encrypted in system_settings:
        session.execute(text("""
            INSERT OR IGNORE INTO system_settings (key, value, value_type, description, is_encrypted, created_at, updated_at, updated_by)
            VALUES (:key, :value, :value_type, :description, :is_encrypted, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :updated_by)
        """), {
            'key': key,
            'value': value,
            'value_type': value_type,
            'description': description,
            'is_encrypted': is_encrypted,
            'updated_by': 'system_creation'
        })

def verify_system(session):
    """Verify that the system was created successfully."""
    
    # Check universal prompts
    result = session.execute(text("SELECT COUNT(*) FROM universal_prompts")).scalar()
    logger.info(f"📊 Universal prompts: {result} records")
    
    # Check document-specific prompts
    result = session.execute(text("SELECT COUNT(*) FROM document_specific_prompts")).scalar()
    logger.info(f"📊 Document-specific prompts: {result} records")
    
    # Check pipeline steps
    result = session.execute(text("SELECT COUNT(*) FROM universal_pipeline_steps")).scalar()
    logger.info(f"📊 Pipeline steps: {result} records")
    
    # Check system settings
    result = session.execute(text("SELECT COUNT(*) FROM system_settings")).scalar()
    logger.info(f"📊 System settings: {result} records")
    
    logger.info("🎉 System verification completed!")

if __name__ == "__main__":
    if create_unified_system():
        logger.info("🎉 Unified universal system created successfully!")
    else:
        logger.error("💥 Unified universal system creation failed!")
        sys.exit(1)
