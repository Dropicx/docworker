#!/usr/bin/env python3
"""
Migration script to move from document-specific prompts to universal system.
This script will:
1. Extract universal prompts from document_prompts table
2. Insert them into universal_prompts table
3. Remove universal prompts from document_prompts table
4. Keep only document-specific prompts in document_prompts
"""

import os
import sys
import logging
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app.database.connection import get_database_url, get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_to_universal_system():
    """Migrate from document-specific to universal prompt system."""
    
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as session:
            logger.info("🚀 Starting migration to universal prompt system...")
            
            # Step 1: Check if universal_prompts table exists
            database_url = get_database_url()
            if 'postgresql' in database_url:
                result = session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'universal_prompts'
                    );
                """))
            else:  # SQLite
                result = session.execute(text("""
                    SELECT EXISTS (
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='universal_prompts'
                    );
                """))
            universal_table_exists = result.scalar()
            
            if not universal_table_exists:
                logger.error("❌ universal_prompts table does not exist. Please run the optimized models migration first.")
                return False
            
            # Step 2: Get universal prompts from any document type (they should be the same)
            logger.info("📋 Extracting universal prompts from document_prompts...")
            
            result = session.execute(text("""
                SELECT 
                    classification_prompt,
                    preprocessing_prompt,
                    grammar_check_prompt,
                    language_translation_prompt
                FROM document_prompts 
                WHERE document_type = 'ARZTBRIEF'
                LIMIT 1
            """))
            
            universal_data = result.fetchone()
            if not universal_data:
                logger.error("❌ No document prompts found to migrate")
                return False
            
            # Step 3: Insert universal prompts
            logger.info("🌐 Inserting universal prompts...")
            
            session.execute(text("""
                INSERT INTO universal_prompts (
                    medical_validation_prompt,
                    classification_prompt, 
                    preprocessing_prompt,
                    grammar_check_prompt,
                    language_translation_prompt,
                    version,
                    last_modified,
                    modified_by
                ) VALUES (
                    :medical_validation,
                    :classification,
                    :preprocessing,
                    :grammar_check,
                    :language_translation,
                    1,
                    CURRENT_TIMESTAMP,
                    'migration_script'
                )
                ON CONFLICT (id) DO UPDATE SET
                    medical_validation_prompt = EXCLUDED.medical_validation_prompt,
                    classification_prompt = EXCLUDED.classification_prompt,
                    preprocessing_prompt = EXCLUDED.preprocessing_prompt,
                    grammar_check_prompt = EXCLUDED.grammar_check_prompt,
                    language_translation_prompt = EXCLUDED.language_translation_prompt,
                    version = EXCLUDED.version + 1,
                    last_modified = CURRENT_TIMESTAMP,
                    modified_by = 'migration_script'
            """), {
                'medical_validation': 'Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält.\n\nKRITERIEN FÜR MEDIZINISCHE INHALTE:\n- Medizinische Fachbegriffe (Diagnosen, Symptome, Behandlungen)\n- Medizinische Abkürzungen (z.B. CT, MRT, EKG, HbA1c)\n- Medizinische Messwerte mit Einheiten (z.B. mg/dl, mmol/l, mmHg)\n- Anatomische Begriffe (Organe, Körperteile, Systeme)\n- Medizinische Verfahren (Operationen, Untersuchungen, Therapien)\n- Medikamentennamen oder Wirkstoffe\n- Krankheitsbilder oder Beschwerden\n\nAntworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH',
                'classification': universal_data[0],  # classification_prompt
                'preprocessing': universal_data[1],   # preprocessing_prompt
                'grammar_check': universal_data[2],   # grammar_check_prompt
                'language_translation': universal_data[3]  # language_translation_prompt
            })
            
            # Step 4: Update document_prompts to remove universal prompts
            logger.info("📝 Updating document_prompts to keep only document-specific prompts...")
            
            # Update all document types to remove universal prompts
            session.execute(text("""
                UPDATE document_prompts SET
                    classification_prompt = 'MIGRATED_TO_UNIVERSAL',
                    preprocessing_prompt = 'MIGRATED_TO_UNIVERSAL', 
                    grammar_check_prompt = 'MIGRATED_TO_UNIVERSAL',
                    language_translation_prompt = 'MIGRATED_TO_UNIVERSAL',
                    last_modified = CURRENT_TIMESTAMP,
                    modified_by = 'migration_script'
                WHERE document_type IN ('ARZTBRIEF', 'BEFUNDBERICHT', 'LABORWERTE')
            """))
            
            # Step 5: Update pipeline steps to reflect universal vs document-specific
            logger.info("🔧 Updating pipeline step configurations...")
            
            # Mark universal steps as universal in pipeline_step_configs
            universal_step_names = ['MEDICAL_VALIDATION', 'CLASSIFICATION', 'PREPROCESSING', 'GRAMMAR_CHECK', 'LANGUAGE_TRANSLATION']
            
            for step_name in universal_step_names:
                session.execute(text("""
                    UPDATE pipeline_step_configs SET
                        name = name || ' (Universal)',
                        description = description || ' - Now handled by universal system'
                    WHERE step_name = :step_name
                """), {'step_name': step_name})
            
            session.commit()
            logger.info("✅ Migration completed successfully!")
            
            # Step 6: Show summary
            logger.info("📊 Migration Summary:")
            logger.info("   - Universal prompts moved to universal_prompts table")
            logger.info("   - Document-specific prompts kept in document_prompts table")
            logger.info("   - Pipeline steps updated to reflect universal vs document-specific")
            logger.info("   - Old universal prompts marked as 'MIGRATED_TO_UNIVERSAL'")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        session.rollback()
        return False

if __name__ == "__main__":
    success = migrate_to_universal_system()
    if success:
        logger.info("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Migration failed!")
        sys.exit(1)
