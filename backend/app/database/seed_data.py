"""
Database seeding script to populate initial data
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session, sessionmaker

from app.database.connection import get_engine
from app.database.models import (
    DocumentPromptsDB, 
    PipelineStepConfigDB, 
    SystemSettingsDB,
    DocumentClassEnum,
    ProcessingStepEnum
)
from app.models.document_types import DocumentClass, DocumentPrompts, PipelineStepConfig

logger = logging.getLogger(__name__)

def seed_database():
    """Seed the database with initial data"""
    try:
        engine = get_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Seed document prompts
        seed_document_prompts(session)
        
        # Seed system settings
        seed_system_settings(session)
        
        session.commit()
        logger.info("✅ Database seeded successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to seed database: {e}")
        if 'session' in locals():
            session.rollback()
        return False
    finally:
        if 'session' in locals():
            session.close()

def seed_document_prompts(session: Session):
    """Seed document prompts for all document types"""
    
    # Default pipeline steps configuration
    default_pipeline_steps = {
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
    
    # Seed prompts for each document type
    for doc_class in DocumentClass:
        # Check if prompts already exist
        existing = session.query(DocumentPromptsDB).filter(
            DocumentPromptsDB.document_type == DocumentClassEnum(doc_class.value)
        ).first()
        
        if existing:
            logger.info(f"Prompts for {doc_class.value} already exist, skipping...")
            continue
        
        # Create document prompts
        db_prompts = DocumentPromptsDB(
            document_type=DocumentClassEnum(doc_class.value),
            classification_prompt=get_classification_prompt(doc_class),
            preprocessing_prompt=get_preprocessing_prompt(doc_class),
            translation_prompt=get_translation_prompt(doc_class),
            fact_check_prompt=get_fact_check_prompt(doc_class),
            grammar_check_prompt=get_grammar_check_prompt(doc_class),
            language_translation_prompt=get_language_translation_prompt(doc_class),
            final_check_prompt=get_final_check_prompt(doc_class),
            version=1,
            last_modified=datetime.now(),
            modified_by="system_seed"
        )
        
        session.add(db_prompts)
        session.flush()  # Get the ID
        
        # Create pipeline step configurations
        for step_name, step_config in default_pipeline_steps.items():
            db_step = PipelineStepConfigDB(
                document_prompts_id=db_prompts.id,
                step_name=ProcessingStepEnum(step_name),
                enabled=step_config.enabled,
                order=step_config.order,
                name=step_config.name,
                description=step_config.description
            )
            session.add(db_step)
        
        logger.info(f"✅ Seeded prompts for {doc_class.value}")

def seed_system_settings(session: Session):
    """Seed system settings"""
    
    system_settings = [
        {
            "key": "app_version",
            "value": "1.0.0",
            "value_type": "string",
            "description": "Current application version"
        },
        {
            "key": "max_file_size_mb",
            "value": "50",
            "value_type": "int",
            "description": "Maximum file size in MB"
        },
        {
            "key": "max_processing_time_seconds",
            "value": "300",
            "value_type": "int",
            "description": "Maximum processing time in seconds"
        },
        {
            "key": "cleanup_interval_minutes",
            "value": "60",
            "value_type": "int",
            "description": "Cleanup interval in minutes"
        },
        {
            "key": "default_confidence_threshold",
            "value": "0.7",
            "value_type": "float",
            "description": "Default confidence threshold for AI operations"
        },
        {
            "key": "enable_ai_logging",
            "value": "true",
            "value_type": "bool",
            "description": "Enable comprehensive AI interaction logging"
        },
        {
            "key": "medical_validation_enabled",
            "value": "true",
            "value_type": "bool",
            "description": "Enable medical content validation"
        },
        {
            "key": "pipeline_steps_enabled",
            "value": "true",
            "value_type": "bool",
            "description": "Enable pipeline step management"
        }
    ]
    
    for setting in system_settings:
        # Check if setting already exists
        existing = session.query(SystemSettingsDB).filter(
            SystemSettingsDB.key == setting["key"]
        ).first()
        
        if existing:
            logger.info(f"Setting {setting['key']} already exists, skipping...")
            continue
        
        db_setting = SystemSettingsDB(
            key=setting["key"],
            value=setting["value"],
            value_type=setting["value_type"],
            description=setting["description"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            updated_by="system_seed"
        )
        
        session.add(db_setting)
        logger.info(f"✅ Seeded setting: {setting['key']}")

def get_classification_prompt(doc_class: DocumentClass) -> str:
    """Get classification prompt for document type"""
    if doc_class == DocumentClass.ARZTBRIEF:
        return """Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief handelt.

KRITERIEN FÜR ARZTBRIEF:
- Briefe zwischen Ärzten
- Entlassungsbriefe
- Überweisungsschreiben
- Konsiliarberichte
- Therapieberichte
- Arzt-zu-Arzt Kommunikation

Antworte NUR mit: ARZTBRIEF oder NICHT_ARZTBRIEF"""
    
    elif doc_class == DocumentClass.BEFUNDBERICHT:
        return """Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Befundbericht handelt.

KRITERIEN FÜR BEFUNDBERICHT:
- Medizinische Befunde
- Untersuchungsergebnisse
- Bildgebungsbefunde (MRT, CT, Röntgen)
- Laborbefunde
- Pathologiebefunde
- Diagnostische Berichte

Antworte NUR mit: BEFUNDBERICHT oder NICHT_BEFUNDBERICHT"""
    
    else:  # LABORWERTE
        return """Analysiere diesen medizinischen Text und bestimme, ob es sich um Laborwerte handelt.

KRITERIEN FÜR LABORWERTE:
- Blutwerte und Messwerte
- Referenzbereiche
- Laborparameter
- Messwerte mit Einheiten
- Laborergebnisse
- Biochemische Werte

Antworte NUR mit: LABORWERTE oder NICHT_LABORWERTE"""

def get_preprocessing_prompt(doc_class: DocumentClass) -> str:
    """Get preprocessing prompt for document type"""
    return """Entferne alle persönlichen Daten aus diesem medizinischen Text, aber behalte alle medizinischen Informationen.

ZU ENTFERNENDE DATEN:
- Namen von Patienten und Ärzten
- Adressen und Telefonnummern
- Geburtsdaten und Alter
- Versicherungsnummern
- Patientennummern
- E-Mail-Adressen

ZU BEHALTENDE DATEN:
- Alle medizinischen Informationen
- Diagnosen und Symptome
- Behandlungen und Therapien
- Medikamente und Dosierungen
- Laborwerte und Messwerte
- Medizinische Abkürzungen

Ersetze persönliche Daten durch [ENTFERNT] oder [ANONYMISIERT]."""

def get_translation_prompt(doc_class: DocumentClass) -> str:
    """Get translation prompt for document type"""
    if doc_class == DocumentClass.ARZTBRIEF:
        return """Übersetze diesen Arztbrief in einfache, verständliche Sprache für Patienten.

ZIELE:
- Verständliche Sprache verwenden
- Medizinische Fachbegriffe erklären
- Strukturierte Darstellung
- Wichtige Informationen hervorheben
- Patientenfreundliche Formulierung

STRUKTUR:
- Klare Überschriften
- Bullet Points für Listen
- Kurze, verständliche Sätze
- Wichtige Informationen am Anfang"""
    
    elif doc_class == DocumentClass.BEFUNDBERICHT:
        return """Übersetze diesen Befundbericht in einfache, verständliche Sprache für Patienten.

ZIELE:
- Verständliche Sprache verwenden
- Medizinische Fachbegriffe erklären
- Befunde klar strukturieren
- Wichtige Ergebnisse hervorheben
- Patientenfreundliche Formulierung

STRUKTUR:
- Klare Überschriften
- Bullet Points für Listen
- Kurze, verständliche Sätze
- Wichtige Befunde am Anfang"""
    
    else:  # LABORWERTE
        return """Übersetze diese Laborwerte in einfache, verständliche Sprache für Patienten.

ZIELE:
- Verständliche Sprache verwenden
- Laborwerte erklären
- Referenzbereiche verständlich machen
- Wichtige Abweichungen hervorheben
- Patientenfreundliche Formulierung

STRUKTUR:
- Klare Überschriften
- Tabellarische Darstellung
- Kurze, verständliche Sätze
- Wichtige Werte am Anfang"""

def get_fact_check_prompt(doc_class: DocumentClass) -> str:
    """Get fact check prompt for document type"""
    return """Prüfe diesen medizinischen Text auf Korrektheit und Konsistenz.

PRÜFPUNKTE:
- Medizinische Fakten korrekt
- Konsistenz der Informationen
- Logische Zusammenhänge
- Vollständigkeit der Angaben
- Plausibilität der Werte

BEI FEHLERN:
- Korrigiere offensichtliche Fehler
- Ergänze fehlende Informationen
- Stelle Konsistenz her
- Behalte Original bei Unsicherheit

Antworte mit dem korrigierten Text."""

def get_grammar_check_prompt(doc_class: DocumentClass) -> str:
    """Get grammar check prompt for document type"""
    return """Korrigiere die deutsche Grammatik und Rechtschreibung in diesem Text.

KORREKTUREN:
- Rechtschreibfehler
- Grammatikfehler
- Zeichensetzung
- Groß- und Kleinschreibung
- Satzstellung
- Wortwahl

BEHALTE:
- Medizinische Fachbegriffe
- Originale Bedeutung
- Struktur und Format

Antworte mit dem korrigierten Text."""

def get_language_translation_prompt(doc_class: DocumentClass) -> str:
    """Get language translation prompt for document type"""
    return """Übersetze diesen Text in {language}.

ÜBERSETZUNGSREGELN:
- Verständliche Sprache verwenden
- Medizinische Begriffe korrekt übersetzen
- Struktur beibehalten
- Wichtige Informationen hervorheben
- Patientenfreundliche Formulierung

STRUKTUR:
- Klare Überschriften
- Bullet Points für Listen
- Kurze, verständliche Sätze
- Wichtige Informationen am Anfang

Antworte mit dem übersetzten Text."""

def get_final_check_prompt(doc_class: DocumentClass) -> str:
    """Get final check prompt for document type"""
    return """Führe eine finale Qualitätskontrolle dieses medizinischen Textes durch.

PRÜFPUNKTE:
- Vollständigkeit der Informationen
- Verständlichkeit der Sprache
- Korrekte Grammatik und Rechtschreibung
- Konsistenz der Darstellung
- Patientenfreundliche Formulierung
- Strukturierte Darstellung

OPTIMIERUNGEN:
- Verbessere die Verständlichkeit
- Korrigiere verbleibende Fehler
- Optimiere die Struktur
- Stelle Konsistenz her

Antworte mit dem optimierten Text."""

if __name__ == "__main__":
    import sys
    
    print("🌱 Seeding database with initial data...")
    success = seed_database()
    print("✅ Database seeded successfully" if success else "❌ Failed to seed database")
    sys.exit(0 if success else 1)
