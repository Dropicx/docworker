#!/usr/bin/env python3
"""
Railway-specific database seeding script
Run this on Railway to populate the production database
"""

import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def seed_railway_database():
    """Seed the Railway PostgreSQL database"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Get database URL from Railway
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
        
        print(f"🔗 Connecting to Railway database...")
        
        # Connect to database
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("✅ Connected to Railway database")
        
        # Check if data already exists
        cur.execute("SELECT COUNT(*) FROM document_prompts")
        existing_prompts = cur.fetchone()['count']
        
        if existing_prompts > 0:
            print(f"📊 Database already has {existing_prompts} prompt records, skipping seeding...")
            return True
        
        print("🌱 Seeding database with initial data...")
        
        # Insert document prompts for ARZTBRIEF
        print("📝 Seeding ARZTBRIEF prompts...")
        cur.execute("""
            INSERT INTO document_prompts (
                document_type, classification_prompt, preprocessing_prompt, 
                translation_prompt, fact_check_prompt, grammar_check_prompt,
                language_translation_prompt, final_check_prompt, version, 
                last_modified, modified_by
            ) VALUES (
                'arztbrief',
                'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief handelt.\n\nKRITERIEN FÜR ARZTBRIEF:\n- Briefe zwischen Ärzten\n- Entlassungsbriefe\n- Überweisungsschreiben\n- Konsiliarberichte\n- Therapieberichte\n- Arzt-zu-Arzt Kommunikation\n\nAntworte NUR mit: ARZTBRIEF oder NICHT_ARZTBRIEF',
                'Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.\n\nZU ENTFERNENDE DATEN:\n- Namen von Patienten und Ärzten\n- Adressen und Telefonnummern\n- Geburtsdaten und Alter\n- Versicherungsnummern\n- Patientennummern\n- E-Mail-Adressen\n\nZU BEHALTENDE DATEN:\n- Alle medizinischen Informationen\n- Diagnosen und Symptome\n- Behandlungen und Therapien\n- Medikamente und Dosierungen\n- Laborwerte und Messwerte\n- Medizinische Abkürzungen\n\nErsetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT].',
                'Übersetze diesen Arztbrief in einfache, verständliche Sprache für Patienten.\n\nZIELE:\n- Verständliche Sprache verwenden\n- Medizinische Fachbegriffe erklären\n- Strukturierte Darstellung\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang',
                'Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.\n\nPRÜFPUNKTE:\n- Medizinische Fakten korrekt\n- Konsistenz der Informationen\n- Logische Zusammenhänge\n- Vollständigkeit der Angaben\n- Plausibilität der Werte\n\nBEI FEHLERN:\n- Korrigiere offensichtliche Fehler\n- Ergänze fehlende Informationen\n- Stelle Konsistenz her\n- Behalte Original bei Unsicherheit\n\nAntworte mit dem korrigierten Text.',
                'Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.\n\nKORREKTUREN:\n- Rechtschreibfehler\n- Grammatikfehler\n- Zeichensetzung\n- Groß- und Kleinschreibung\n- Satzstellung\n- Wortwahl\n\nBEHALTE:\n- Medizinische Fachbegriffe\n- Originale Bedeutung\n- Struktur und Format\n\nAntworte mit dem korrigierten Text.',
                'Übersetze diesen Text in {language}.\n\nÜBERSETZUNGSREGELN:\n- Verständliche Sprache verwenden\n- Medizinische Begriffe korrekt übersetzen\n- Struktur beibehalten\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang\n\nAntworte mit dem übersetzten Text.',
                'Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.\n\nPRÜFPUNKTE:\n- Vollständigkeit der Informationen\n- Verständlichkeit der Sprache\n- Korrekte Grammatik und Rechtschreibung\n- Konsistenz der Darstellung\n- Patientenfreundliche Formulierung\n- Strukturierte Darstellung\n\nOPTIMIERUNGEN:\n- Verbessere die Verständlichkeit\n- Korrigiere verbleibende Fehler\n- Optimiere die Struktur\n- Stelle Konsistenz her\n\nAntworte mit dem optimierten Text.',
                1,
                NOW(),
                'system_seed'
            ) RETURNING id
        """)
        arztbrief_id = cur.fetchone()['id']
        
        # Insert pipeline steps for ARZTBRIEF
        pipeline_steps = [
            ('medical_validation', True, 1, 'Medical Content Validation', 'Validate if document contains medical content'),
            ('classification', True, 2, 'Document Classification', 'Classify document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)'),
            ('preprocessing', True, 3, 'Preprocessing', 'Remove PII and clean text'),
            ('translation', True, 4, 'Translation', 'Translate to simple language'),
            ('fact_check', True, 5, 'Fact Check', 'Verify medical accuracy'),
            ('grammar_check', True, 6, 'Grammar Check', 'Correct German grammar'),
            ('language_translation', True, 7, 'Language Translation', 'Translate to target language'),
            ('final_check', True, 8, 'Final Check', 'Final quality assurance'),
            ('formatting', True, 9, 'Formatting', 'Apply text formatting')
        ]
        
        for step_name, enabled, order, name, description in pipeline_steps:
            cur.execute("""
                INSERT INTO pipeline_step_configs (
                    document_prompts_id, step_name, enabled, "order", name, description
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (arztbrief_id, step_name, enabled, order, name, description))
        
        # Insert document prompts for BEFUNDBERICHT
        print("📝 Seeding BEFUNDBERICHT prompts...")
        cur.execute("""
            INSERT INTO document_prompts (
                document_type, classification_prompt, preprocessing_prompt, 
                translation_prompt, fact_check_prompt, grammar_check_prompt,
                language_translation_prompt, final_check_prompt, version, 
                last_modified, modified_by
            ) VALUES (
                'befundbericht',
                'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Befundbericht handelt.\n\nKRITERIEN FÜR BEFUNDBERICHT:\n- Medizinische Befunde\n- Untersuchungsergebnisse\n- Bildgebungsbefunde (MRT, CT, Röntgen)\n- Laborbefunde\n- Pathologiebefunde\n- Diagnostische Berichte\n\nAntworte NUR mit: BEFUNDBERICHT oder NICHT_BEFUNDBERICHT',
                'Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.\n\nZU ENTFERNENDE DATEN:\n- Namen von Patienten und Ärzten\n- Adressen und Telefonnummern\n- Geburtsdaten und Alter\n- Versicherungsnummern\n- Patientennummern\n- E-Mail-Adressen\n\nZU BEHALTENDE DATEN:\n- Alle medizinischen Informationen\n- Diagnosen und Symptome\n- Behandlungen und Therapien\n- Medikamente und Dosierungen\n- Laborwerte und Messwerte\n- Medizinische Abkürzungen\n\nErsetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT].',
                'Übersetze diesen Befundbericht in einfache, verständliche Sprache für Patienten.\n\nZIELE:\n- Verständliche Sprache verwenden\n- Medizinische Fachbegriffe erklären\n- Befunde klar strukturieren\n- Wichtige Ergebnisse hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Befunde am Anfang',
                'Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.\n\nPRÜFPUNKTE:\n- Medizinische Fakten korrekt\n- Konsistenz der Informationen\n- Logische Zusammenhänge\n- Vollständigkeit der Angaben\n- Plausibilität der Werte\n\nBEI FEHLERN:\n- Korrigiere offensichtliche Fehler\n- Ergänze fehlende Informationen\n- Stelle Konsistenz her\n- Behalte Original bei Unsicherheit\n\nAntworte mit dem korrigierten Text.',
                'Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.\n\nKORREKTUREN:\n- Rechtschreibfehler\n- Grammatikfehler\n- Zeichensetzung\n- Groß- und Kleinschreibung\n- Satzstellung\n- Wortwahl\n\nBEHALTE:\n- Medizinische Fachbegriffe\n- Originale Bedeutung\n- Struktur und Format\n\nAntworte mit dem korrigierten Text.',
                'Übersetze diesen Text in {language}.\n\nÜBERSETZUNGSREGELN:\n- Verständliche Sprache verwenden\n- Medizinische Begriffe korrekt übersetzen\n- Struktur beibehalten\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang\n\nAntworte mit dem übersetzten Text.',
                'Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.\n\nPRÜFPUNKTE:\n- Vollständigkeit der Informationen\n- Verständlichkeit der Sprache\n- Korrekte Grammatik und Rechtschreibung\n- Konsistenz der Darstellung\n- Patientenfreundliche Formulierung\n- Strukturierte Darstellung\n\nOPTIMIERUNGEN:\n- Verbessere die Verständlichkeit\n- Korrigiere verbleibende Fehler\n- Optimiere die Struktur\n- Stelle Konsistenz her\n\nAntworte mit dem optimierten Text.',
                1,
                NOW(),
                'system_seed'
            ) RETURNING id
        """)
        befundbericht_id = cur.fetchone()['id']
        
        # Insert pipeline steps for BEFUNDBERICHT
        for step_name, enabled, order, name, description in pipeline_steps:
            cur.execute("""
                INSERT INTO pipeline_step_configs (
                    document_prompts_id, step_name, enabled, "order", name, description
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (befundbericht_id, step_name, enabled, order, name, description))
        
        # Insert document prompts for LABORWERTE
        print("📝 Seeding LABORWERTE prompts...")
        cur.execute("""
            INSERT INTO document_prompts (
                document_type, classification_prompt, preprocessing_prompt, 
                translation_prompt, fact_check_prompt, grammar_check_prompt,
                language_translation_prompt, final_check_prompt, version, 
                last_modified, modified_by
            ) VALUES (
                'laborwerte',
                'Analysiere diesen medizinischen Text und bestimme, ob es sich um Laborwerte handelt.\n\nKRITERIEN FÜR LABORWERTE:\n- Blutwerte und Messwerte\n- Referenzbereiche\n- Laborparameter\n- Messwerte mit Einheiten\n- Laborergebnisse\n- Biochemische Werte\n\nAntworte NUR mit: LABORWERTE oder NICHT_LABORWERTE',
                'Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.\n\nZU ENTFERNENDE DATEN:\n- Namen von Patienten und Ärzten\n- Adressen und Telefonnummern\n- Geburtsdaten und Alter\n- Versicherungsnummern\n- Patientennummern\n- E-Mail-Adressen\n\nZU BEHALTENDE DATEN:\n- Alle medizinischen Informationen\n- Diagnosen und Symptome\n- Behandlungen und Therapien\n- Medikamente und Dosierungen\n- Laborwerte und Messwerte\n- Medizinische Abkürzungen\n\nErsetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT].',
                'Übersetze diese Laborwerte in einfache, verständliche Sprache für Patienten.\n\nZIELE:\n- Verständliche Sprache verwenden\n- Laborwerte erklären\n- Referenzbereiche verständlich machen\n- Wichtige Abweichungen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Tabellarische Darstellung\n- Kurze, verständliche Sätze\n- Wichtige Werte am Anfang',
                'Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.\n\nPRÜFPUNKTE:\n- Medizinische Fakten korrekt\n- Konsistenz der Informationen\n- Logische Zusammenhänge\n- Vollständigkeit der Angaben\n- Plausibilität der Werte\n\nBEI FEHLERN:\n- Korrigiere offensichtliche Fehler\n- Ergänze fehlende Informationen\n- Stelle Konsistenz her\n- Behalte Original bei Unsicherheit\n\nAntworte mit dem korrigierten Text.',
                'Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.\n\nKORREKTUREN:\n- Rechtschreibfehler\n- Grammatikfehler\n- Zeichensetzung\n- Groß- und Kleinschreibung\n- Satzstellung\n- Wortwahl\n\nBEHALTE:\n- Medizinische Fachbegriffe\n- Originale Bedeutung\n- Struktur und Format\n\nAntworte mit dem korrigierten Text.',
                'Übersetze diesen Text in {language}.\n\nÜBERSETZUNGSREGELN:\n- Verständliche Sprache verwenden\n- Medizinische Begriffe korrekt übersetzen\n- Struktur beibehalten\n- Wichtige Informationen hervorheben\n- Patientenfreundliche Formulierung\n\nSTRUKTUR:\n- Klare Überschriften\n- Bullet Points für Listen\n- Kurze, verständliche Sätze\n- Wichtige Informationen am Anfang\n\nAntworte mit dem übersetzten Text.',
                'Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.\n\nPRÜFPUNKTE:\n- Vollständigkeit der Informationen\n- Verständlichkeit der Sprache\n- Korrekte Grammatik und Rechtschreibung\n- Konsistenz der Darstellung\n- Patientenfreundliche Formulierung\n- Strukturierte Darstellung\n\nOPTIMIERUNGEN:\n- Verbessere die Verständlichkeit\n- Korrigiere verbleibende Fehler\n- Optimiere die Struktur\n- Stelle Konsistenz her\n\nAntworte mit dem optimierten Text.',
                1,
                NOW(),
                'system_seed'
            ) RETURNING id
        """)
        laborwerte_id = cur.fetchone()['id']
        
        # Insert pipeline steps for LABORWERTE
        for step_name, enabled, order, name, description in pipeline_steps:
            cur.execute("""
                INSERT INTO pipeline_step_configs (
                    document_prompts_id, step_name, enabled, "order", name, description
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (laborwerte_id, step_name, enabled, order, name, description))
        
        # Insert system settings
        print("⚙️ Seeding system settings...")
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
            cur.execute("""
                INSERT INTO system_settings (key, value, value_type, description, created_at, updated_at, updated_by)
                VALUES (%s, %s, %s, %s, NOW(), NOW(), 'system_seed')
            """, (key, value, value_type, description))
        
        # Commit all changes
        conn.commit()
        
        print("✅ Database seeded successfully!")
        print("📊 Initial data includes:")
        print("   - Default prompts for ARZTBRIEF, BEFUNDBERICHT, LABORWERTE")
        print("   - Pipeline step configurations for all document types")
        print("   - System settings")
        print("   - Medical content validation prompts")
        
        return True
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = seed_railway_database()
    sys.exit(0 if success else 1)
