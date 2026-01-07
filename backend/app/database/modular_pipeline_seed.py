"""
Modular Pipeline Database Seeding

This module seeds the database with default configuration for the modular pipeline system.
"""

import json
import logging

from sqlalchemy import text

from app.database.connection import get_engine

logger = logging.getLogger(__name__)


def seed_modular_pipeline():
    """Seed database with default modular pipeline configuration."""
    try:
        engine = get_engine()

        with engine.connect() as conn:
            logger.info("🌱 Starting modular pipeline seeding...")

            # Check if OCR configuration already exists
            result = conn.execute(text("SELECT COUNT(*) FROM ocr_configuration"))
            ocr_config_count = result.scalar()

            if ocr_config_count > 0:
                logger.info("ℹ️ Modular pipeline configuration already exists, skipping seeding")
                return True

            # ==================== OCR CONFIGURATION ====================
            logger.info("🔍 Inserting default OCR configuration...")

            # Default OCR configuration
            # Primary: Mistral OCR (fast, accurate)
            # Fallback: PaddleOCR via Hetzner (EXTERNAL_OCR_URL)

            mistral_ocr_config = {
                "model": "mistral-ocr-latest",
            }

            paddleocr_config = {
                "url": "https://ocr.fra-la.de",
                "timeout": 180,
            }

            conn.execute(
                text("""
                INSERT INTO ocr_configuration (
                    selected_engine, mistral_ocr_config, paddleocr_config,
                    pii_removal_enabled, last_modified, modified_by
                ) VALUES (
                    :selected_engine, :mistral_ocr_config, :paddleocr_config,
                    :pii_removal_enabled, CURRENT_TIMESTAMP, :modified_by
                )
            """),
                {
                    "selected_engine": "MISTRAL_OCR",
                    "mistral_ocr_config": json.dumps(mistral_ocr_config),
                    "paddleocr_config": json.dumps(paddleocr_config),
                    "pii_removal_enabled": True,
                    "modified_by": "system_seed",
                },
            )

            # ==================== AVAILABLE MODELS ====================
            logger.info("🤖 Inserting available AI models...")

            models = [
                # OVH AI Endpoints models
                {
                    "name": "Meta-Llama-3_3-70B-Instruct",
                    "display_name": "Llama 3.3 70B (Main Model)",
                    "provider": "OVH",
                    "description": "High-performance language model for medical translation and analysis",
                    "max_tokens": 8192,
                    "supports_vision": False,
                    "price_input_per_1m_tokens": 0.54,
                    "price_output_per_1m_tokens": 0.81,
                    "model_config": json.dumps(
                        {
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "frequency_penalty": 0.0,
                            "presence_penalty": 0.0,
                        }
                    ),
                    "is_enabled": True,
                },
                {
                    "name": "Mistral-Nemo-Instruct-2407",
                    "display_name": "Mistral Nemo OVH (Preprocessing)",
                    "provider": "OVH",
                    "description": "Fast and efficient model for preprocessing and classification tasks (OVH hosted)",
                    "max_tokens": 4096,
                    "supports_vision": False,
                    "price_input_per_1m_tokens": 0.13,
                    "price_output_per_1m_tokens": 0.13,
                    "model_config": json.dumps(
                        {
                            "temperature": 0.5,
                            "top_p": 0.9,
                            "frequency_penalty": 0.0,
                            "presence_penalty": 0.0,
                        }
                    ),
                    "is_enabled": True,
                },
                {
                    "name": "Qwen2.5-VL-72B-Instruct",
                    "display_name": "Qwen 2.5 VL 72B (Vision OCR)",
                    "provider": "OVH",
                    "description": "Vision language model for OCR and image analysis (slow but accurate)",
                    "max_tokens": 4096,
                    "supports_vision": True,
                    "price_input_per_1m_tokens": None,
                    "price_output_per_1m_tokens": None,
                    "model_config": json.dumps(
                        {"temperature": 0.1, "top_p": 0.9, "max_pixels": 1280 * 28 * 28}
                    ),
                    "is_enabled": True,
                },
                # Mistral AI API models (direct)
                {
                    "name": "mistral-large-latest",
                    "display_name": "Mistral Large 3",
                    "provider": "MISTRAL",
                    "description": "Mistral Large 3 - High-quality model for complex medical translations",
                    "max_tokens": 131072,
                    "supports_vision": False,
                    "price_input_per_1m_tokens": 0.50,
                    "price_output_per_1m_tokens": 1.50,
                    "model_config": json.dumps({"temperature": 0.7}),
                    "is_enabled": True,
                },
                {
                    "name": "open-mistral-nemo",
                    "display_name": "Mistral NeMo",
                    "provider": "MISTRAL",
                    "description": "Mistral NeMo - Fast and efficient model for preprocessing tasks",
                    "max_tokens": 128000,
                    "supports_vision": False,
                    "price_input_per_1m_tokens": 0.13,
                    "price_output_per_1m_tokens": 0.13,
                    "model_config": json.dumps({"temperature": 0.5}),
                    "is_enabled": True,
                },
                {
                    "name": "ministral-8b-latest",
                    "display_name": "Ministral 3 8B",
                    "provider": "MISTRAL",
                    "description": "Ministral 3 8B - Compact and fast model for simple tasks",
                    "max_tokens": 128000,
                    "supports_vision": False,
                    "price_input_per_1m_tokens": 0.15,
                    "price_output_per_1m_tokens": 0.15,
                    "model_config": json.dumps({"temperature": 0.5}),
                    "is_enabled": True,
                },
            ]

            for model in models:
                conn.execute(
                    text("""
                    INSERT INTO available_models (
                        name, display_name, provider, description, max_tokens,
                        supports_vision, model_config, is_enabled,
                        price_input_per_1m_tokens, price_output_per_1m_tokens,
                        created_at, last_modified, modified_by
                    ) VALUES (
                        :name, :display_name, :provider, :description, :max_tokens,
                        :supports_vision, :model_config, :is_enabled,
                        :price_input_per_1m_tokens, :price_output_per_1m_tokens,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :modified_by
                    )
                """),
                    {**model, "modified_by": "system_seed"},
                )

            # ==================== DYNAMIC PIPELINE STEPS ====================
            logger.info("⚙️ Inserting default pipeline steps...")

            # Get model IDs for reference
            llama_result = conn.execute(
                text("SELECT id FROM available_models WHERE name = 'Meta-Llama-3_3-70B-Instruct'")
            )
            llama_id = llama_result.scalar()

            mistral_result = conn.execute(
                text("SELECT id FROM available_models WHERE name = 'Mistral-Nemo-Instruct-2407'")
            )
            mistral_id = mistral_result.scalar()

            # Get document class IDs for document-specific steps
            arztbrief_result = conn.execute(
                text("SELECT id FROM document_classes WHERE class_key = 'ARZTBRIEF'")
            )
            arztbrief_id = arztbrief_result.scalar()

            befundbericht_result = conn.execute(
                text("SELECT id FROM document_classes WHERE class_key = 'BEFUNDBERICHT'")
            )
            befundbericht_id = befundbericht_result.scalar()

            laborwerte_result = conn.execute(
                text("SELECT id FROM document_classes WHERE class_key = 'LABORWERTE'")
            )
            laborwerte_id = laborwerte_result.scalar()

            pipeline_steps = [
                {
                    "name": "Medical Content Validation",
                    "description": "Validates if document contains medical content (Universal Branching Step)",
                    "order": 1,
                    "enabled": True,
                    "prompt_template": "Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält.\n\nText:\n{input_text}\n\nAntworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH",
                    "selected_model_id": mistral_id,
                    "temperature": 0.3,
                    "max_tokens": 100,
                    "retry_on_failure": True,
                    "max_retries": 3,
                    "input_from_previous_step": True,
                    "output_format": "text",
                    "is_branching_step": True,
                    "branching_field": "medical_validation",
                    "document_class_id": None,  # Universal step
                    "stop_conditions": {
                        "stop_on_values": ["NICHT_MEDIZINISCH"],
                        "termination_reason": "Non-medical content detected",
                        "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument (z.B. Arztbrief, Befundbericht, Laborwerte) hoch.",
                    },
                },
                {
                    "name": "Document Classification",
                    "description": "Classifies document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE) - Routes to class-specific pipeline",
                    "order": 2,
                    "enabled": True,
                    "prompt_template": "Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief, einen Befundbericht oder Laborwerte handelt.\n\nText:\n{input_text}\n\nAntworte NUR mit dem erkannten Typ: ARZTBRIEF, BEFUNDBERICHT oder LABORWERTE",
                    "selected_model_id": mistral_id,
                    "temperature": 0.3,
                    "max_tokens": 200,
                    "retry_on_failure": True,
                    "max_retries": 3,
                    "input_from_previous_step": True,
                    "output_format": "text",
                    "is_branching_step": True,
                    "branching_field": "document_type",
                    "document_class_id": None,  # Universal step
                },
                # NOTE: PII removal now happens LOCALLY via AdvancedPrivacyFilter
                # BEFORE pipeline execution (GDPR-compliant, no PII sent to cloud)
                # ==================== DOCUMENT-SPECIFIC TRANSLATION STEPS ====================
                # These run ONLY for their specific document class
                {
                    "name": "Vereinfachung Arztbrief",
                    "description": "Patient-friendly translation for doctor's letters (ARZTBRIEF only)",
                    "order": 10,
                    "enabled": True,
                    "prompt_template": """Du bist ein erfahrener Medizinjournalist, der komplexe medizinische Arztbriefe für Patienten verständlich aufbereitet.

DEINE AUFGABE:
Wandle den folgenden Arztbrief in eine patientenfreundliche Version um, die auch medizinische Laien verstehen können.

RICHTLINIEN:

1. STRUKTUR:
   - Verwende klare Überschriften mit ## für Hauptabschnitte
   - Gliedere in logische Abschnitte mit passenden Emojis:
     • 📋 Zusammenfassung
     • 🩺 Diagnosen
     • 💊 Medikamente & Behandlung
     • ⚠️ Wichtige Hinweise
     • ✅ Nächste Schritte
   - Nutze Aufzählungspunkte für bessere Lesbarkeit

2. SPRACHE:
   - Erkläre jeden medizinischen Fachbegriff in Klammern oder direkt im Text
   - Verwende einfache, klare Sätze
   - Bei Empfehlungen: Unterscheide klar zwischen einmaliger Diagnostik und dauerhafter Behandlung
   - Schreibe in einem beruhigenden, aber informativen Ton

3. WERTE & BEFUNDE:
   - Bei abweichenden Werten: Nenne den Normalbereich zum Vergleich (z.B. "Ihr Wert: 19 ng/ml – optimal wären über 30")
   - Markiere kritische Werte mit **fett** und ⚠️ oder ❗
   - Erkläre bei Auffälligkeiten ehrlich, ob Handlungsbedarf besteht oder nur Beobachtung nötig ist

4. INHALT:
   - Behalte ALLE Informationen bei - nichts weglassen, nichts hinzufügen
   - Übernimm konkrete Empfehlungen aus dem Original wörtlich (Ernährung, Lebensstil, Medikamente)
   - Erkläre, was Diagnosen für den Alltag bedeuten können
   - Schreibe neutral - NIEMALS "wir", keine Kontaktdaten

5. FORMAT:
   - Ausgabe direkt in Markdown (OHNE ```markdown Codeblöcke!)
   - Beginne DIREKT mit ## 📋 Zusammenfassung
   - Verwende nur EINE Raute-Ebene pro Überschrift

ARZTBRIEF:
{input_text}

Gib nur die vereinfachte Version zurück, ohne einleitende Kommentare.""",
                    "selected_model_id": llama_id,
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "markdown",
                    "document_class_id": arztbrief_id,  # ARZTBRIEF only
                },
                {
                    "name": "Vereinfachung Befundbericht",
                    "description": "Patient-friendly translation for medical reports (BEFUNDBERICHT only)",
                    "order": 10,
                    "enabled": True,
                    "prompt_template": """Du bist ein erfahrener Radiologe und Medizinjournalist, der komplexe medizinische Befundberichte für Patienten verständlich erklärt.

DEINE AUFGABE:
Wandle den folgenden Befundbericht in eine patientenfreundliche Version um, die auch medizinische Laien verstehen können.

RICHTLINIEN:

1. STRUKTUR:
   - Beginne mit einer kurzen Zusammenfassung des Hauptergebnisses (2-3 Sätze)
   - Gliedere nach Abschnitten mit passenden Emojis:
     • 📋 Zusammenfassung
     • 🔬 Was wurde untersucht?
     • 🔍 Was wurde gefunden?
     • 💡 Was bedeutet das für Sie?
     • ✅ Nächste Schritte

2. SPRACHE:
   - Übersetze Fachbegriffe in Alltagssprache (z.B. "Hepatomegalie" → "vergrößerte Leber")
   - Nutze Vergleiche für Größen ("etwa so groß wie eine Kirsche")
   - Unterscheide klar: Ist etwas nur zur Kontrolle oder braucht es Behandlung?

3. BEFUNDE EINORDNEN:
   - Bei Auffälligkeiten: Ehrlich sagen ob besorgniserregend oder eher harmlos
   - Bei "wahrscheinlich gutartig": Erkläre, dass Kontrolle Sicherheit gibt
   - Markiere kritische Befunde mit **fett** und ⚠️ oder ❗
   - "Unauffällig" = normal, gesund – das klar kommunizieren

4. INHALT:
   - Behalte ALLE Informationen bei - nichts weglassen, nichts hinzufügen
   - Übernimm Empfehlungen aus dem Original wörtlich
   - Schreibe neutral - NIEMALS "wir", keine Kontaktdaten

5. FORMAT:
   - Ausgabe direkt in Markdown (OHNE ```markdown Codeblöcke!)
   - Beginne DIREKT mit ## 📋 Zusammenfassung
   - Verwende nur EINE Raute-Ebene pro Überschrift

BEFUNDBERICHT:
{input_text}

Gib nur die vereinfachte Version zurück, ohne einleitende Kommentare.""",
                    "selected_model_id": llama_id,
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "markdown",
                    "document_class_id": befundbericht_id,  # BEFUNDBERICHT only
                },
                {
                    "name": "Vereinfachung Laborwerte",
                    "description": "Patient-friendly translation for lab results (LABORWERTE only)",
                    "order": 10,
                    "enabled": True,
                    "prompt_template": """Du bist ein erfahrener Labormediziner und Gesundheitskommunikator, der Laborergebnisse für Patienten verständlich erklärt.

DEINE AUFGABE:
Wandle die folgenden Laborwerte in eine patientenfreundliche Erklärung um.

RICHTLINIEN:

1. STRUKTUR:
   - Beginne mit Gesamteinschätzung (1-2 Sätze)
   - Gliedere nach Kategorien mit Emojis:
     • 📋 Gesamtübersicht
     • 🩸 Blutbild
     • 🫀 Herz-Kreislauf
     • 🫁 Leber & Nieren
     • ✅ Zusammenfassung

2. JEDEN WERT ERKLÄREN:
   - **Ihr Ergebnis** vs. **Normalbereich** (z.B. "Ihr Wert: 19 ng/ml – optimal wären über 30")
   - Bei Grenzwerten: Klar sagen dass es an der Grenze liegt
   - Bewertung mit Symbol: ✅ Normal | ⚠️ Leicht auffällig | ❗ Deutlich außerhalb
   - Kurz erklären was der Wert misst und warum er wichtig ist

3. KRITISCHE WERTE HERVORHEBEN:
   - Auffällige Werte mit **fett** und ⚠️/❗ markieren
   - Bei Abweichungen: Mögliche Ursachen nennen (ohne Panikmache)
   - Ehrlich einordnen: Handlungsbedarf oder nur Beobachtung?

4. INHALT:
   - Behalte ALLE Werte bei - nichts weglassen, nichts hinzufügen
   - Übernimm konkrete Empfehlungen wörtlich (Ernährung, Lebensstil)
   - Schreibe neutral - NIEMALS "wir", keine Kontaktdaten

5. FORMAT:
   - Ausgabe direkt in Markdown (OHNE ```markdown Codeblöcke!)
   - Beginne DIREKT mit ## 📋 Ihre Laborwerte
   - Verwende nur EINE Raute-Ebene pro Überschrift

LABORWERTE:
{input_text}

Gib nur die vereinfachte Version zurück, ohne einleitende Kommentare.""",
                    "selected_model_id": llama_id,
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "markdown",
                    "document_class_id": laborwerte_id,  # LABORWERTE only
                },
                {
                    "name": "Finaler Check auf Richtigkeit",
                    "description": "Final quality check for medical accuracy (ARZTBRIEF)",
                    "order": 20,
                    "enabled": True,
                    "prompt_template": """Du bist ein medizinischer Qualitätsprüfer. Deine Aufgabe ist es, die vereinfachte Version eines medizinischen Dokuments auf Korrektheit zu prüfen.

PRÜFKRITERIEN:

1. MEDIZINISCHE KORREKTHEIT:
   - Sind alle Diagnosen aus dem Original korrekt wiedergegeben?
   - Sind alle Laborwerte/Messwerte identisch?
   - Sind Medikamente und Dosierungen korrekt?
   - Wurden keine falschen medizinischen Informationen hinzugefügt (Halluzinationen)?

2. VOLLSTÄNDIGKEIT:
   - Sind alle wichtigen Informationen aus dem Original enthalten?
   - Wurden keine relevanten Befunde weggelassen?

3. KEINE HINZUFÜGUNGEN:
   - Enthält der Text KEINE erfundenen Diagnosen, Werte oder Behandlungen?
   - Wurden keine spekulativen Aussagen als Fakten dargestellt?

4. FORMAT-PRÜFUNG:
   - Sind alle Emojis korrekt verwendet? (✅ ⚠️ ❗ 💊 🩺 etc.)
   - Ist die Struktur klar und übersichtlich?
   - Sind die Markdown-Überschriften korrekt (nur ## nicht ## ##)?

VERGLEICHE:

ORIGINALDOKUMENT:
{original_text}

VEREINFACHTE VERSION:
{input_text}

DEINE AUFGABE:
- Wenn alles korrekt ist: Gib die vereinfachte Version unverändert zurück
- Wenn Fehler gefunden werden: Korrigiere diese Fehler in der vereinfachten Version

WICHTIG:
- Behalte den patientenfreundlichen Stil bei
- Behalte alle Emojis und die Markdown-Formatierung bei
- Ändere nur faktische Fehler, keine stilistischen Aspekte
- Füge keine neuen Informationen hinzu
- Ausgabe direkt in Markdown (OHNE umschließende ```markdown Codeblöcke!)
- Verwende nur EINE Raute-Ebene pro Überschrift (also ## nicht ## ##)

Gib nur das finale Ergebnis im Markdown-Format zurück, ohne Kommentare oder Erklärungen zu deiner Prüfung. Beginne direkt mit dem Inhalt.""",
                    "selected_model_id": llama_id,
                    "temperature": 0.5,
                    "max_tokens": 8192,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "markdown",
                    "document_class_id": arztbrief_id,  # ARZTBRIEF quality check
                    "post_branching": True,  # Runs after document-specific translation
                },
                # ==================== GENERIC FALLBACK STEP (if no class-specific) ====================
                {
                    "name": "Patient-Friendly Translation",
                    "description": "Generic translation for unclassified documents",
                    "order": 3,
                    "enabled": True,
                    "prompt_template": "Übersetze diesen medizinischen Text in einfache, patientenfreundliche Sprache.\n\nVerwende kurze Sätze und vermeide medizinische Fachbegriffe. Strukturiere den Text mit klaren Abschnitten.\n\nText:\n{input_text}\n\nGib nur die vereinfachte Übersetzung zurück.",
                    "selected_model_id": llama_id,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "text",
                },
                {
                    "name": "Medical Fact Check",
                    "description": "Verifies medical accuracy and completeness",
                    "order": 4,
                    "enabled": True,
                    "prompt_template": "Überprüfe diesen medizinischen Text auf Korrektheit und Vollständigkeit.\n\nAchte besonders auf Diagnosen, Behandlungsempfehlungen und Medikamentennamen.\n\nText:\n{input_text}\n\nGib den Text mit korrigierten medizinischen Informationen zurück.",
                    "selected_model_id": llama_id,
                    "temperature": 0.5,
                    "max_tokens": 4096,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "text",
                },
                {
                    "name": "Grammar and Spelling Check",
                    "description": "Corrects German grammar and spelling",
                    "order": 5,
                    "enabled": True,
                    "prompt_template": "Korrigiere Grammatik und Rechtschreibung in diesem Text.\n\nAchte auf korrekte medizinische Terminologie und professionelle Formulierung.\n\nText:\n{input_text}\n\nGib nur den korrigierten Text zurück.",
                    "selected_model_id": llama_id,
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "text",
                },
                {
                    "name": "Language Translation",
                    "description": "Translates text to target language",
                    "order": 6,
                    "enabled": True,
                    "prompt_template": "Übersetze den folgenden Text EXAKT in {target_language}.\n\nAchte auf präzise medizinische Terminologie, wo angebracht, aber halte den Ton patientenfreundlich.\n\nText:\n{input_text}\n\nGib nur die Übersetzung zurück.",
                    "selected_model_id": llama_id,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "text",
                },
                {
                    "name": "Final Quality Check",
                    "description": "Final quality assurance and completeness check",
                    "order": 7,
                    "enabled": True,
                    "prompt_template": "Führe eine finale Qualitätskontrolle dieses Textes durch.\n\nPrüfe auf Verständlichkeit, Vollständigkeit und patientenfreundliche Formulierung.\n\nText:\n{input_text}\n\nGib den final geprüften Text zurück.",
                    "selected_model_id": llama_id,
                    "temperature": 0.5,
                    "max_tokens": 4096,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "text",
                },
                {
                    "name": "Text Formatting",
                    "description": "Applies markdown formatting and structure",
                    "order": 8,
                    "enabled": True,
                    "prompt_template": "Formatiere diesen Text mit klaren Überschriften, Abschnitten und einer logischen Struktur.\n\nVerwende Markdown-Formatierung:\n- Überschriften mit #\n- Bullet Points für Listen\n- Fettschrift für wichtige Begriffe\n\nText:\n{input_text}\n\nGib nur den formatierten Markdown-Text zurück.",
                    "selected_model_id": llama_id,
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "retry_on_failure": True,
                    "max_retries": 2,
                    "input_from_previous_step": True,
                    "output_format": "markdown",
                },
            ]

            for step in pipeline_steps:
                conn.execute(
                    text("""
                    INSERT INTO dynamic_pipeline_steps (
                        name, description, "order", enabled, prompt_template,
                        selected_model_id, temperature, max_tokens,
                        retry_on_failure, max_retries, input_from_previous_step,
                        output_format, is_branching_step, branching_field, document_class_id,
                        post_branching, stop_conditions, required_context_variables,
                        created_at, last_modified, modified_by
                    ) VALUES (
                        :name, :description, :order, :enabled, :prompt_template,
                        :selected_model_id, :temperature, :max_tokens,
                        :retry_on_failure, :max_retries, :input_from_previous_step,
                        :output_format, :is_branching_step, :branching_field, :document_class_id,
                        :post_branching, :stop_conditions, :required_context_variables,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :modified_by
                    )
                """),
                    {
                        **step,
                        "is_branching_step": step.get("is_branching_step", False),
                        "branching_field": step.get("branching_field", None),
                        "document_class_id": step.get("document_class_id", None),
                        "post_branching": step.get("post_branching", False),
                        "stop_conditions": json.dumps(step.get("stop_conditions"))
                        if step.get("stop_conditions")
                        else None,
                        "required_context_variables": json.dumps(
                            step.get("required_context_variables")
                        )
                        if step.get("required_context_variables")
                        else None,
                        "modified_by": "system_seed",
                    },
                )

            conn.commit()
            logger.info("✅ Modular pipeline seeding completed successfully")
            return True

    except Exception as e:
        logger.error(f"❌ Failed to seed modular pipeline: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    print("🌱 Seeding modular pipeline database...")
    success = seed_modular_pipeline()
    print("✅ Seeding completed" if success else "❌ Seeding failed")
    sys.exit(0 if success else 1)
