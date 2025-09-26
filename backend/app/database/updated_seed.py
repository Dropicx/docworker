"""
Updated database seeding script with new prompt fields
"""

import logging
from sqlalchemy import text
from app.database.connection import get_engine

logger = logging.getLogger(__name__)

def updated_seed_database():
    """Seed database with updated schema including new prompts"""
    try:
        engine = get_engine()

        with engine.connect() as conn:
            # Check if data already exists
            result = conn.execute(text("SELECT COUNT(*) FROM document_prompts"))
            existing_count = result.scalar()

            if existing_count > 0:
                logger.info(f"Database already has {existing_count} prompt records, skipping seeding...")
                return True

            logger.info("🌱 Seeding database with updated prompt structure...")

            # Medical validation prompt (universal)
            medical_validation_prompt = """Analysiere diesen Text und bestimme, ob er medizinischen Inhalt enthält.

KRITERIEN FÜR MEDIZINISCHEN INHALT:
- Diagnosen oder Symptome
- Medizinische Fachbegriffe
- Behandlungen oder Therapien
- Medikamente oder Dosierungen
- Laborwerte oder Messwerte
- Medizinische Abkürzungen
- Anatomische Begriffe

Antworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH"""

            # Formatting prompt (universal)
            formatting_prompt = """Formatiere diesen medizinischen Text für optimale Lesbarkeit.

FORMATIERUNG:
- Verwende klare Überschriften mit Emojis
- Erstelle Bullet Points für Listen (→)
- Hebe wichtige Informationen hervor
- Strukturiere den Text logisch
- Füge Leerzeilen zwischen Abschnitten ein
- Verwende einheitliche Formatierung

BEHALTE:
- Alle medizinischen Informationen
- Die Verständlichkeit
- Alle wichtigen Details

Antworte mit dem formatierten Text."""

            # Insert ARZTBRIEF prompts
            conn.execute(text("""
                INSERT INTO document_prompts (
                    document_type, medical_validation_prompt, classification_prompt, preprocessing_prompt,
                    translation_prompt, fact_check_prompt, grammar_check_prompt,
                    language_translation_prompt, final_check_prompt, formatting_prompt, version,
                    last_modified, modified_by
                ) VALUES (
                    'ARZTBRIEF',
                    :medical_validation_prompt,
                    'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief handelt.\n\nKRITERIEN FÜR ARZTBRIEF:\n- Briefe zwischen Ärzten\n- Entlassungsbriefe\n- Überweisungsschreiben\n- Konsiliarberichte\n- Therapieberichte\n- Arzt-zu-Arzt Kommunikation\n\nAntworte NUR mit: ARZTBRIEF oder NICHT_ARZTBRIEF',
                    'Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.\n\nZU ENTFERNENDE DATEN:\n- Namen von Patienten und Ärzten\n- Adressen und Telefonnummern\n- Geburtsdaten und Alter\n- Versicherungsnummern\n- Patientennummern\n- E-Mail-Adressen\n\nZU BEHALTENDE DATEN:\n- Alle medizinischen Informationen\n- Diagnosen und Symptome\n- Behandlungen und Therapien\n- Medikamente und Dosierungen\n- Laborwerte und Messwerte\n- Medizinische Abkürzungen\n\nErsetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT].',
                    'Übersetze diesen Arztbrief in einfache, verständliche Sprache für Patienten.\n\nZIELE:\n- Verständliche Sprache verwenden\n- Medizinische Fachbegriffe erklären\n- Strukturierte Darstellung\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang',
                    'Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.\n\nPRÜFPUNKTE:\n- Medizinische Fakten korrekt\n- Konsistenz der Informationen\n- Logische Zusammenhänge\n- Vollständigkeit der Angaben\n- Plausibilität der Werte\n\nBEI FEHLERN:\n- Korrigiere offensichtliche Fehler\n- Ergänze fehlende Informationen\n- Stelle Konsistenz her\n- Behalte Original bei Unsicherheit\n\nAntworte mit dem korrigierten Text.',
                    'Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.\n\nKORREKTUREN:\n- Rechtschreibfehler\n- Grammatikfehler\n- Zeichensetzung\n- Groß- und Kleinschreibung\n- Satzstellung\n- Wortwahl\n\nBEHALTE:\n- Medizinische Fachbegriffe\n- Originale Bedeutung\n- Struktur und Format\n\nAntworte mit dem korrigierten Text.',
                    'Übersetze diesen Text in {language}.\n\nÜBERSETZUNGSREGELN:\n- Verständliche Sprache verwenden\n- Medizinische Begriffe korrekt übersetzen\n- Struktur beibehalten\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang\n\nAntworte mit dem übersetzten Text.',
                    'Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.\n\nPRÜFPUNKTE:\n- Vollständigkeit der Informationen\n- Verständlichkeit der Sprache\n- Korrekte Grammatik und Rechtschreibung\n- Konsistenz der Darstellung\n- Patientenfreundliche Formulierung\n- Strukturierte Darstellung\n\nOPTIMIERUNGEN:\n- Verbessere die Verständlichkeit\n- Korrigiere verbleibende Fehler\n- Optimiere die Struktur\n- Stelle Konsistenz her\n\nAntworte mit dem optimierten Text.',
                    :formatting_prompt,
                    1,
                    CURRENT_TIMESTAMP,
                    'system_seed'
                ) RETURNING id
            """), {
                'medical_validation_prompt': medical_validation_prompt,
                'formatting_prompt': formatting_prompt
            })

            # Get the ID for pipeline steps
            result = conn.execute(text("SELECT id FROM document_prompts WHERE document_type = 'ARZTBRIEF'"))
            arztbrief_id = result.scalar()

            # Insert pipeline steps for ARZTBRIEF
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
                    INSERT INTO pipeline_step_configs (
                        document_prompts_id, step_name, enabled, "order", name, description
                    ) VALUES (:doc_id, :step_name, :enabled, :order, :name, :description)
                    ON CONFLICT (document_prompts_id, step_name) DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        "order" = EXCLUDED.order,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description
                """), {
                    'doc_id': arztbrief_id,
                    'step_name': step_name,
                    'enabled': enabled,
                    'order': order,
                    'name': name,
                    'description': description
                })

            # Insert BEFUNDBERICHT prompts
            conn.execute(text("""
                INSERT INTO document_prompts (
                    document_type, medical_validation_prompt, classification_prompt, preprocessing_prompt,
                    translation_prompt, fact_check_prompt, grammar_check_prompt,
                    language_translation_prompt, final_check_prompt, formatting_prompt, version,
                    last_modified, modified_by
                ) VALUES (
                    'BEFUNDBERICHT',
                    :medical_validation_prompt,
                    'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Befundbericht handelt.\n\nKRITERIEN FÜR BEFUNDBERICHT:\n- Medizinische Befunde\n- Untersuchungsergebnisse\n- Bildgebungsbefunde (MRT, CT, Röntgen)\n- Laborbefunde\n- Pathologiebefunde\n- Diagnostische Berichte\n\nAntworte NUR mit: BEFUNDBERICHT oder NICHT_BEFUNDBERICHT',
                    'Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.\n\nZU ENTFERNENDE DATEN:\n- Namen von Patienten und Ärzten\n- Adressen und Telefonnummern\n- Geburtsdaten und Alter\n- Versicherungsnummern\n- Patientennummern\n- E-Mail-Adressen\n\nZU BEHALTENDE DATEN:\n- Alle medizinischen Informationen\n- Diagnosen und Symptome\n- Behandlungen und Therapien\n- Medikamente und Dosierungen\n- Laborwerte und Messwerte\n- Medizinische Abkürzungen\n\nErsetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT].',
                    'Übersetze diesen Befundbericht in einfache, verständliche Sprache für Patienten.\n\nZIELE:\n- Verständliche Sprache verwenden\n- Medizinische Fachbegriffe erklären\n- Befunde klar strukturieren\n- Wichtige Ergebnisse hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Befunde am Anfang',
                    'Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.\n\nPRÜFPUNKTE:\n- Medizinische Fakten korrekt\n- Konsistenz der Informationen\n- Logische Zusammenhänge\n- Vollständigkeit der Angaben\n- Plausibilität der Werte\n\nBEI FEHLERN:\n- Korrigiere offensichtliche Fehler\n- Ergänze fehlende Informationen\n- Stelle Konsistenz her\n- Behalte Original bei Unsicherheit\n\nAntworte mit dem korrigierten Text.',
                    'Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.\n\nKORREKTUREN:\n- Rechtschreibfehler\n- Grammatikfehler\n- Zeichensetzung\n- Groß- und Kleinschreibung\n- Satzstellung\n- Wortwahl\n\nBEHALTE:\n- Medizinische Fachbegriffe\n- Originale Bedeutung\n- Struktur und Format\n\nAntworte mit dem korrigierten Text.',
                    'Übersetze diesen Text in {language}.\n\nÜBERSETZUNGSREGELN:\n- Verständliche Sprache verwenden\n- Medizinische Begriffe korrekt übersetzen\n- Struktur beibehalten\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang\n\nAntworte mit dem übersetzten Text.',
                    'Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.\n\nPRÜFPUNKTE:\n- Vollständigkeit der Informationen\n- Verständlichkeit der Sprache\n- Korrekte Grammatik und Rechtschreibung\n- Konsistenz der Darstellung\n- Patientenfreundliche Formulierung\n- Strukturierte Darstellung\n\nOPTIMIERUNGEN:\n- Verbessere die Verständlichkeit\n- Korrigiere verbleibende Fehler\n- Optimiere die Struktur\n- Stelle Konsistenz her\n\nAntworte mit dem optimierten Text.',
                    :formatting_prompt,
                    1,
                    CURRENT_TIMESTAMP,
                    'system_seed'
                ) RETURNING id
            """), {
                'medical_validation_prompt': medical_validation_prompt,
                'formatting_prompt': formatting_prompt
            })

            # Get the ID for pipeline steps
            result = conn.execute(text("SELECT id FROM document_prompts WHERE document_type = 'BEFUNDBERICHT'"))
            befundbericht_id = result.scalar()

            # Insert pipeline steps for BEFUNDBERICHT
            for step_name, enabled, order, name, description in pipeline_steps:
                conn.execute(text("""
                    INSERT INTO pipeline_step_configs (
                        document_prompts_id, step_name, enabled, "order", name, description
                    ) VALUES (:doc_id, :step_name, :enabled, :order, :name, :description)
                    ON CONFLICT (document_prompts_id, step_name) DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        "order" = EXCLUDED.order,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description
                """), {
                    'doc_id': befundbericht_id,
                    'step_name': step_name,
                    'enabled': enabled,
                    'order': order,
                    'name': name,
                    'description': description
                })

            # Insert LABORWERTE prompts
            conn.execute(text("""
                INSERT INTO document_prompts (
                    document_type, medical_validation_prompt, classification_prompt, preprocessing_prompt,
                    translation_prompt, fact_check_prompt, grammar_check_prompt,
                    language_translation_prompt, final_check_prompt, formatting_prompt, version,
                    last_modified, modified_by
                ) VALUES (
                    'LABORWERTE',
                    :medical_validation_prompt,
                    'Analysiere diesen medizinischen Text und bestimme, ob es sich um Laborwerte handelt.\n\nKRITERIEN FÜR LABORWERTE:\n- Blutwerte und Messwerte\n- Referenzbereiche\n- Laborparameter\n- Messwerte mit Einheiten\n- Laborergebnisse\n- Biochemische Werte\n\nAntworte NUR mit: LABORWERTE oder NICHT_LABORWERTE',
                    'Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.\n\nZU ENTFERNENDE DATEN:\n- Namen von Patienten und Ärzten\n- Adressen und Telefonnummern\n- Geburtsdaten und Alter\n- Versicherungsnummern\n- Patientennummern\n- E-Mail-Adressen\n\nZU BEHALTENDE DATEN:\n- Alle medizinischen Informationen\n- Diagnosen und Symptome\n- Behandlungen und Therapien\n- Medikamente und Dosierungen\n- Laborwerte und Messwerte\n- Medizinische Abkürzungen\n\nErsetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT].',
                    'Übersetze diese Laborwerte in einfache, verständliche Sprache für Patienten.\n\nZIELE:\n- Verständliche Sprache verwenden\n- Laborwerte erklären\n- Referenzbereiche verständlich machen\n- Wichtige Abweichungen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Tabellarische Darstellung\n- Kurze, verständliche Sätze\n- Wichtige Werte am Anfang',
                    'Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.\n\nPRÜFPUNKTE:\n- Medizinische Fakten korrekt\n- Konsistenz der Informationen\n- Logische Zusammenhänge\n- Vollständigkeit der Angaben\n- Plausibilität der Werte\n\nBEI FEHLERN:\n- Korrigiere offensichtliche Fehler\n- Ergänze fehlende Informationen\n- Stelle Konsistenz her\n- Behalte Original bei Unsicherheit\n\nAntworte mit dem korrigierten Text.',
                    'Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.\n\nKORREKTUREN:\n- Rechtschreibfehler\n- Grammatikfehler\n- Zeichensetzung\n- Groß- und Kleinschreibung\n- Satzstellung\n- Wortwahl\n\nBEHALTE:\n- Medizinische Fachbegriffe\n- Originale Bedeutung\n- Struktur und Format\n\nAntworte mit dem korrigierten Text.',
                    'Übersetze diesen Text in {language}.\n\nÜBERSETZUNGSREGELN:\n- Verständliche Sprache verwenden\n- Medizinische Begriffe korrekt übersetzen\n- Struktur beibehalten\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang\n\nAntworte mit dem übersetzten Text.',
                    'Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.\n\nPRÜFPUNKTE:\n- Vollständigkeit der Informationen\n- Verständlichkeit der Sprache\n- Korrekte Grammatik und Rechtschreibung\n- Konsistenz der Darstellung\n- Patientenfreundliche Formulierung\n- Strukturierte Darstellung\n\nOPTIMIERUNGEN:\n- Verbessere die Verständlichkeit\n- Korrigiere verbleibende Fehler\n- Optimiere die Struktur\n- Stelle Konsistenz her\n\nAntworte mit dem optimierten Text.',
                    :formatting_prompt,
                    1,
                    CURRENT_TIMESTAMP,
                    'system_seed'
                ) RETURNING id
            """), {
                'medical_validation_prompt': medical_validation_prompt,
                'formatting_prompt': formatting_prompt
            })

            # Get the ID for pipeline steps
            result = conn.execute(text("SELECT id FROM document_prompts WHERE document_type = 'LABORWERTE'"))
            laborwerte_id = result.scalar()

            # Insert pipeline steps for LABORWERTE
            for step_name, enabled, order, name, description in pipeline_steps:
                conn.execute(text("""
                    INSERT INTO pipeline_step_configs (
                        document_prompts_id, step_name, enabled, "order", name, description
                    ) VALUES (:doc_id, :step_name, :enabled, :order, :name, :description)
                    ON CONFLICT (document_prompts_id, step_name) DO UPDATE SET
                        enabled = EXCLUDED.enabled,
                        "order" = EXCLUDED.order,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description
                """), {
                    'doc_id': laborwerte_id,
                    'step_name': step_name,
                    'enabled': enabled,
                    'order': order,
                    'name': name,
                    'description': description
                })

            # Insert system settings
            system_settings = [
                ('app_version', '1.0.0', 'string', 'Current application version'),
                ('max_file_size_mb', '50', 'int', 'Maximum file size in MB'),
                ('max_processing_time_seconds', '300', 'int', 'Maximum processing time in seconds'),
                ('cleanup_interval_minutes', '60', 'int', 'Cleanup interval in minutes'),
                ('default_confidence_threshold', '0.7', 'float', 'Default confidence threshold for AI operations'),
                ('enable_ai_logging', 'true', 'bool', 'Enable comprehensive AI interaction logging'),
                ('medical_validation_enabled', 'true', 'bool', 'Enable medical content validation'),
                ('pipeline_steps_enabled', 'true', 'bool', 'Enable pipeline step management')
            ]

            for key, value, value_type, description in system_settings:
                conn.execute(text("""
                    INSERT INTO system_settings (key, value, value_type, description, is_encrypted, created_at, updated_at, updated_by)
                    VALUES (:key, :value, :value_type, :description, :is_encrypted, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'system_seed')
                """), {
                    'key': key,
                    'value': value,
                    'value_type': value_type,
                    'description': description,
                    'is_encrypted': False
                })

            conn.commit()
            logger.info("✅ Database seeded successfully with updated prompts!")
            return True

    except Exception as e:
        logger.error(f"❌ Failed to seed database: {e}")
        return False

if __name__ == "__main__":
    import sys

    print("🌱 Seeding database with updated prompt structure...")
    success = updated_seed_database()
    print("✅ Database seeded successfully" if success else "❌ Failed to seed database")
    sys.exit(0 if success else 1)