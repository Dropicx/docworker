"""
Unified Database Seeding

This module seeds the database with the new unified universal prompt system.
"""

import logging
from datetime import datetime
from sqlalchemy import text
from app.database.connection import get_engine

logger = logging.getLogger(__name__)

def unified_seed_database():
    """Seed database with unified universal prompt system."""
    try:
        engine = get_engine()
        
        with engine.connect() as conn:
            logger.info("🌱 Starting unified database seeding...")
            
            # Check if universal prompts already exist
            result = conn.execute(text("SELECT COUNT(*) FROM universal_prompts"))
            universal_count = result.scalar()
            
            if universal_count > 0:
                logger.info("ℹ️ Universal prompts already exist, skipping seeding")
                return True
            
            # Insert universal prompts
            logger.info("🌐 Inserting universal prompts...")
            conn.execute(text("""
                INSERT INTO universal_prompts (
                    medical_validation_prompt, classification_prompt, preprocessing_prompt,
                    language_translation_prompt, version, last_modified, modified_by, is_active
                ) VALUES (
                    :medical_validation_prompt, :classification_prompt, :preprocessing_prompt,
                    :language_translation_prompt, :version, CURRENT_TIMESTAMP, :modified_by, :is_active
                )
            """), {
                'medical_validation_prompt': 'Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält. Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH',
                'classification_prompt': 'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief, einen Befundbericht oder Laborwerte handelt. Antworte NUR mit dem erkannten Typ (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE).',
                'preprocessing_prompt': 'Entferne aus dem folgenden medizinischen Text alle persönlichen Identifikatoren (Namen, Adressen, Geburtsdaten, Telefonnummern, E-Mail-Adressen, Patientennummern), aber behalte alle medizinischen Informationen und den Kontext bei. Ersetze entfernte PII durch \'[ENTFERNT]\'.',
                'language_translation_prompt': 'Übersetze den folgenden Text EXAKT in {language}. Achte auf präzise medizinische Terminologie, wo angebracht, aber halte den Ton patientenfreundlich. Gib nur die Übersetzung zurück.',
                'version': 1,
                'modified_by': 'system_seed',
                'is_active': True
            })
            
            # Insert document-specific prompts for ARZTBRIEF
            logger.info("📝 Inserting document-specific prompts for ARZTBRIEF...")
            conn.execute(text("""
                INSERT INTO document_specific_prompts (
                    document_type, translation_prompt, fact_check_prompt, grammar_check_prompt, final_check_prompt, formatting_prompt,
                    version, last_modified, modified_by
                ) VALUES (
                    :document_type, :translation_prompt, :fact_check_prompt, :grammar_check_prompt, :final_check_prompt, :formatting_prompt,
                    :version, CURRENT_TIMESTAMP, :modified_by
                )
            """), {
                'document_type': 'ARZTBRIEF',
                'translation_prompt': 'Übersetze diesen Arztbrief in einfache, patientenfreundliche Sprache. Verwende kurze Sätze und vermeide medizinische Fachbegriffe. Strukturiere den Text mit klaren Abschnitten.',
                'fact_check_prompt': 'Überprüfe diesen Arztbrief auf medizinische Korrektheit und Vollständigkeit. Achte besonders auf Diagnosen, Behandlungsempfehlungen und Medikamentennamen.',
                'grammar_check_prompt': 'Korrigiere Grammatik und Rechtschreibung in diesem Arztbrief. Achte auf korrekte medizinische Terminologie und professionelle Formulierung.',
                'final_check_prompt': 'Führe eine finale Qualitätskontrolle dieses Arztbriefes durch. Prüfe auf Verständlichkeit, Vollständigkeit und patientenfreundliche Formulierung.',
                'formatting_prompt': 'Formatiere diesen Arztbrief mit klaren Überschriften, Abschnitten und einer logischen Struktur. Verwende Bullet Points für Listen und Medikamente.',
                'version': 1,
                'modified_by': 'system_seed'
            })
            
            # Insert document-specific prompts for BEFUNDBERICHT
            logger.info("📝 Inserting document-specific prompts for BEFUNDBERICHT...")
            conn.execute(text("""
                INSERT INTO document_specific_prompts (
                    document_type, translation_prompt, fact_check_prompt, grammar_check_prompt, final_check_prompt, formatting_prompt,
                    version, last_modified, modified_by
                ) VALUES (
                    :document_type, :translation_prompt, :fact_check_prompt, :grammar_check_prompt, :final_check_prompt, :formatting_prompt,
                    :version, CURRENT_TIMESTAMP, :modified_by
                )
            """), {
                'document_type': 'BEFUNDBERICHT',
                'translation_prompt': 'Übersetze diesen Befundbericht in verständliche Sprache. Erkläre medizinische Befunde in einfachen Worten und strukturiere die Informationen übersichtlich.',
                'fact_check_prompt': 'Überprüfe diesen Befundbericht auf medizinische Genauigkeit. Achte besonders auf Laborwerte, Messungen und diagnostische Befunde.',
                'grammar_check_prompt': 'Korrigiere Grammatik und Rechtschreibung in diesem Befundbericht. Achte auf präzise medizinische Formulierungen und korrekte Fachbegriffe.',
                'final_check_prompt': 'Führe eine finale Qualitätskontrolle dieses Befundberichtes durch. Prüfe auf Vollständigkeit der Befunde und Verständlichkeit der Erklärungen.',
                'formatting_prompt': 'Formatiere diesen Befundbericht mit klaren Abschnitten für verschiedene Befunde. Verwende Tabellen für Laborwerte und strukturierte Listen.',
                'version': 1,
                'modified_by': 'system_seed'
            })
            
            # Insert document-specific prompts for LABORWERTE
            logger.info("📝 Inserting document-specific prompts for LABORWERTE...")
            conn.execute(text("""
                INSERT INTO document_specific_prompts (
                    document_type, translation_prompt, fact_check_prompt, grammar_check_prompt, final_check_prompt, formatting_prompt,
                    version, last_modified, modified_by
                ) VALUES (
                    :document_type, :translation_prompt, :fact_check_prompt, :grammar_check_prompt, :final_check_prompt, :formatting_prompt,
                    :version, CURRENT_TIMESTAMP, :modified_by
                )
            """), {
                'document_type': 'LABORWERTE',
                'translation_prompt': 'Übersetze diese Laborwerte in verständliche Sprache. Erkläre was jeder Wert bedeutet und ob er normal, erhöht oder erniedrigt ist.',
                'fact_check_prompt': 'Überprüfe diese Laborwerte auf Plausibilität und Vollständigkeit. Achte auf Referenzbereiche und Einheiten.',
                'grammar_check_prompt': 'Korrigiere Grammatik und Rechtschreibung in diesen Laborwerten. Achte auf korrekte medizinische Terminologie und Einheiten.',
                'final_check_prompt': 'Führe eine finale Qualitätskontrolle dieser Laborwerte durch. Prüfe auf Vollständigkeit und Verständlichkeit der Erklärungen.',
                'formatting_prompt': 'Formatiere diese Laborwerte in einer übersichtlichen Tabelle mit Werten, Referenzbereichen und Erklärungen.',
                'version': 1,
                'modified_by': 'system_seed'
            })
            
            # Insert universal pipeline steps
            logger.info("⚙️ Inserting universal pipeline steps...")
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
                conn.execute(text("""
                    INSERT INTO universal_pipeline_steps (
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
                    'modified_by': 'system_seed'
                })
            
            # Insert system settings
            logger.info("⚙️ Inserting system settings...")
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
                conn.execute(text("""
                    INSERT INTO system_settings (key, value, value_type, description, is_encrypted, created_at, updated_at, updated_by)
                    VALUES (:key, :value, :value_type, :description, :is_encrypted, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :updated_by)
                """), {
                    'key': key,
                    'value': value,
                    'value_type': value_type,
                    'description': description,
                    'is_encrypted': is_encrypted,
                    'updated_by': 'system_seed'
                })
            
            conn.commit()
            logger.info("✅ Unified database seeded successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to seed unified database: {e}")
        return False

def fix_incomplete_database():
    """Fix existing databases with missing or incomplete data."""
    try:
        engine = get_engine()

        with engine.connect() as conn:
            logger.info("🔧 Starting database completeness check and repair...")

            # 1. Check and fix document-specific prompts missing grammar_check_prompt
            logger.info("🔍 Checking document-specific prompts for missing grammar_check_prompt...")

            # Get document types that exist but are missing grammar_check_prompt
            result = conn.execute(text("""
                SELECT document_type FROM document_specific_prompts
                WHERE grammar_check_prompt IS NULL OR grammar_check_prompt = ''
            """))
            incomplete_docs = [row[0] for row in result.fetchall()]

            if incomplete_docs:
                logger.info(f"📝 Found {len(incomplete_docs)} document types with missing grammar_check_prompt: {incomplete_docs}")

                # Update ARZTBRIEF
                if 'ARZTBRIEF' in incomplete_docs:
                    conn.execute(text("""
                        UPDATE document_specific_prompts
                        SET grammar_check_prompt = :grammar_check_prompt,
                            last_modified = CURRENT_TIMESTAMP,
                            modified_by = :modified_by
                        WHERE document_type = 'ARZTBRIEF'
                    """), {
                        'grammar_check_prompt': 'Korrigiere Grammatik und Rechtschreibung in diesem Arztbrief. Achte auf korrekte medizinische Terminologie und professionelle Formulierung.',
                        'modified_by': 'system_repair'
                    })
                    logger.info("✅ Fixed grammar_check_prompt for ARZTBRIEF")

                # Update BEFUNDBERICHT
                if 'BEFUNDBERICHT' in incomplete_docs:
                    conn.execute(text("""
                        UPDATE document_specific_prompts
                        SET grammar_check_prompt = :grammar_check_prompt,
                            last_modified = CURRENT_TIMESTAMP,
                            modified_by = :modified_by
                        WHERE document_type = 'BEFUNDBERICHT'
                    """), {
                        'grammar_check_prompt': 'Korrigiere Grammatik und Rechtschreibung in diesem Befundbericht. Achte auf präzise medizinische Formulierungen und korrekte Fachbegriffe.',
                        'modified_by': 'system_repair'
                    })
                    logger.info("✅ Fixed grammar_check_prompt for BEFUNDBERICHT")

                # Update LABORWERTE
                if 'LABORWERTE' in incomplete_docs:
                    conn.execute(text("""
                        UPDATE document_specific_prompts
                        SET grammar_check_prompt = :grammar_check_prompt,
                            last_modified = CURRENT_TIMESTAMP,
                            modified_by = :modified_by
                        WHERE document_type = 'LABORWERTE'
                    """), {
                        'grammar_check_prompt': 'Korrigiere Grammatik und Rechtschreibung in diesen Laborwerten. Achte auf korrekte medizinische Terminologie und Einheiten.',
                        'modified_by': 'system_repair'
                    })
                    logger.info("✅ Fixed grammar_check_prompt for LABORWERTE")

            # 2. Check and fix missing pipeline steps
            logger.info("🔍 Checking universal pipeline steps completeness...")
            result = conn.execute(text("SELECT COUNT(*) FROM universal_pipeline_steps"))
            pipeline_count = result.scalar()

            expected_steps = [
                'MEDICAL_VALIDATION', 'CLASSIFICATION', 'PREPROCESSING', 'TRANSLATION',
                'FACT_CHECK', 'GRAMMAR_CHECK', 'LANGUAGE_TRANSLATION', 'FINAL_CHECK', 'FORMATTING'
            ]

            if pipeline_count < len(expected_steps):
                logger.info(f"⚙️ Found {pipeline_count} pipeline steps, expected {len(expected_steps)}. Adding missing steps...")

                # Get existing step names
                result = conn.execute(text("SELECT step_name FROM universal_pipeline_steps"))
                existing_steps = [row[0] for row in result.fetchall()]

                # Define all steps with metadata
                all_steps = [
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

                # Add missing steps
                for step_name, enabled, order, name, description in all_steps:
                    if step_name not in existing_steps:
                        conn.execute(text("""
                            INSERT INTO universal_pipeline_steps (
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
                            'modified_by': 'system_repair'
                        })
                        logger.info(f"✅ Added missing pipeline step: {step_name}")

            # 3. Check and fix missing document-specific prompts for all document types
            logger.info("🔍 Checking document-specific prompts for all document types...")
            result = conn.execute(text("SELECT document_type FROM document_specific_prompts"))
            existing_doc_types = [row[0] for row in result.fetchall()]

            required_doc_types = ['ARZTBRIEF', 'BEFUNDBERICHT', 'LABORWERTE']
            missing_doc_types = [dt for dt in required_doc_types if dt not in existing_doc_types]

            if missing_doc_types:
                logger.info(f"📝 Found missing document types: {missing_doc_types}")
                # This would trigger the full seeding for missing document types
                # For now, just log it - the main seed function can handle this

            conn.commit()
            logger.info("✅ Database repair completed successfully!")
            return True

    except Exception as e:
        logger.error(f"❌ Failed to repair database: {e}")
        return False
