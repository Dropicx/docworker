"""
Modular Pipeline Database Seeding

This module seeds the database with default configuration for the modular pipeline system.
"""

import logging
import json
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

            # Default OCR configuration: Tesseract (current production setup)
            tesseract_config = {
                "lang": "deu+eng",
                "psm": 3,  # Automatic page segmentation
                "oem": 3   # Default OCR Engine Mode
            }

            paddleocr_config = {
                "use_gpu": True,
                "lang": "german",
                "det_algorithm": "DB",
                "rec_algorithm": "SVTR_LCNet"
            }

            vision_llm_config = {
                "model": "Qwen2.5-VL-72B-Instruct",
                "max_tokens": 4096,
                "temperature": 0.1
            }

            hybrid_config = {
                "quality_threshold": 0.7,
                "use_vision_for_complex": True,
                "fallback_engine": "TESSERACT"
            }

            conn.execute(text("""
                INSERT INTO ocr_configuration (
                    selected_engine, paddleocr_config,
                    vision_llm_config, hybrid_config, pii_removal_enabled,
                    last_modified, modified_by
                ) VALUES (
                    :selected_engine, :paddleocr_config,
                    :vision_llm_config, :hybrid_config, :pii_removal_enabled,
                    CURRENT_TIMESTAMP, :modified_by
                )
            """), {
                'selected_engine': 'PADDLEOCR',
                'paddleocr_config': json.dumps(paddleocr_config),
                'vision_llm_config': json.dumps(vision_llm_config),
                'hybrid_config': json.dumps(hybrid_config),
                'pii_removal_enabled': True,
                'modified_by': 'system_seed'
            })

            # ==================== AVAILABLE MODELS ====================
            logger.info("🤖 Inserting available AI models...")

            models = [
                {
                    'name': 'Meta-Llama-3_3-70B-Instruct',
                    'display_name': 'Llama 3.3 70B (Main Model)',
                    'provider': 'OVH',
                    'description': 'High-performance language model for medical translation and analysis',
                    'max_tokens': 8192,
                    'supports_vision': False,
                    'model_config': json.dumps({
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'frequency_penalty': 0.0,
                        'presence_penalty': 0.0
                    }),
                    'is_enabled': True
                },
                {
                    'name': 'Mistral-Nemo-Instruct-2407',
                    'display_name': 'Mistral Nemo (Preprocessing)',
                    'provider': 'OVH',
                    'description': 'Fast and efficient model for preprocessing and classification tasks',
                    'max_tokens': 4096,
                    'supports_vision': False,
                    'model_config': json.dumps({
                        'temperature': 0.5,
                        'top_p': 0.9,
                        'frequency_penalty': 0.0,
                        'presence_penalty': 0.0
                    }),
                    'is_enabled': True
                },
                {
                    'name': 'Qwen2.5-VL-72B-Instruct',
                    'display_name': 'Qwen 2.5 VL 72B (Vision OCR)',
                    'provider': 'OVH',
                    'description': 'Vision language model for OCR and image analysis (slow but accurate)',
                    'max_tokens': 4096,
                    'supports_vision': True,
                    'model_config': json.dumps({
                        'temperature': 0.1,
                        'top_p': 0.9,
                        'max_pixels': 1280 * 28 * 28
                    }),
                    'is_enabled': True
                }
            ]

            for model in models:
                conn.execute(text("""
                    INSERT INTO available_models (
                        name, display_name, provider, description, max_tokens,
                        supports_vision, model_config, is_enabled,
                        created_at, last_modified, modified_by
                    ) VALUES (
                        :name, :display_name, :provider, :description, :max_tokens,
                        :supports_vision, :model_config, :is_enabled,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, :modified_by
                    )
                """), {
                    **model,
                    'modified_by': 'system_seed'
                })

            # ==================== DYNAMIC PIPELINE STEPS ====================
            logger.info("⚙️ Inserting default pipeline steps...")

            # Get model IDs for reference
            llama_result = conn.execute(text("SELECT id FROM available_models WHERE name = 'Meta-Llama-3_3-70B-Instruct'"))
            llama_id = llama_result.scalar()

            mistral_result = conn.execute(text("SELECT id FROM available_models WHERE name = 'Mistral-Nemo-Instruct-2407'"))
            mistral_id = mistral_result.scalar()

            pipeline_steps = [
                {
                    'name': 'Medical Content Validation',
                    'description': 'Validates if document contains medical content (Universal Branching Step)',
                    'order': 1,
                    'enabled': True,
                    'prompt_template': 'Analysiere den folgenden Text und bestimme, ob er medizinische Inhalte enthält.\n\nText:\n{input_text}\n\nAntworte NUR mit: MEDIZINISCH oder NICHT_MEDIZINISCH',
                    'selected_model_id': mistral_id,
                    'temperature': 0.3,
                    'max_tokens': 100,
                    'retry_on_failure': True,
                    'max_retries': 3,
                    'input_from_previous_step': True,
                    'output_format': 'text',
                    'is_branching_step': True,
                    'branching_field': 'medical_validation',
                    'document_class_id': None,  # Universal step
                    'stop_conditions': {
                        'stop_on_values': ['NICHT_MEDIZINISCH'],
                        'termination_reason': 'Non-medical content detected',
                        'termination_message': 'Das hochgeladene Dokument enthält keinen medizinischen Inhalt. Bitte laden Sie ein medizinisches Dokument (z.B. Arztbrief, Befundbericht, Laborwerte) hoch.'
                    }
                },
                {
                    'name': 'Document Classification',
                    'description': 'Classifies document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE) - Routes to class-specific pipeline',
                    'order': 2,
                    'enabled': True,
                    'prompt_template': 'Analysiere diesen medizinischen Text und bestimme, ob es sich um einen Arztbrief, einen Befundbericht oder Laborwerte handelt.\n\nText:\n{input_text}\n\nAntworte NUR mit dem erkannten Typ: ARZTBRIEF, BEFUNDBERICHT oder LABORWERTE',
                    'selected_model_id': mistral_id,
                    'temperature': 0.3,
                    'max_tokens': 200,
                    'retry_on_failure': True,
                    'max_retries': 3,
                    'input_from_previous_step': True,
                    'output_format': 'text',
                    'is_branching_step': True,
                    'branching_field': 'document_type',
                    'document_class_id': None  # Universal step
                },
                {
                    'name': 'PII Preprocessing',
                    'description': 'Removes personal identifiers while preserving medical information',
                    'order': 3,
                    'enabled': True,
                    'prompt_template': 'Entferne aus dem folgenden medizinischen Text alle persönlichen Identifikatoren (Namen, Adressen, Geburtsdaten, Telefonnummern, E-Mail-Adressen, Patientennummern), aber behalte alle medizinischen Informationen und den Kontext bei.\n\nErsetze entfernte PII durch \'[ENTFERNT]\'.\n\nText:\n{input_text}\n\nGib nur den bereinigten Text zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.5,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'text'
                },
                {
                    'name': 'Patient-Friendly Translation',
                    'description': 'Translates medical text into simple, patient-friendly language',
                    'order': 4,
                    'enabled': True,
                    'prompt_template': 'Übersetze diesen medizinischen Text in einfache, patientenfreundliche Sprache.\n\nVerwende kurze Sätze und vermeide medizinische Fachbegriffe. Strukturiere den Text mit klaren Abschnitten.\n\nText:\n{input_text}\n\nGib nur die vereinfachte Übersetzung zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.7,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'text'
                },
                {
                    'name': 'Medical Fact Check',
                    'description': 'Verifies medical accuracy and completeness',
                    'order': 5,
                    'enabled': True,
                    'prompt_template': 'Überprüfe diesen medizinischen Text auf Korrektheit und Vollständigkeit.\n\nAchte besonders auf Diagnosen, Behandlungsempfehlungen und Medikamentennamen.\n\nText:\n{input_text}\n\nGib den Text mit korrigierten medizinischen Informationen zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.5,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'text'
                },
                {
                    'name': 'Grammar and Spelling Check',
                    'description': 'Corrects German grammar and spelling',
                    'order': 6,
                    'enabled': True,
                    'prompt_template': 'Korrigiere Grammatik und Rechtschreibung in diesem Text.\n\nAchte auf korrekte medizinische Terminologie und professionelle Formulierung.\n\nText:\n{input_text}\n\nGib nur den korrigierten Text zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.3,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'text'
                },
                {
                    'name': 'Language Translation',
                    'description': 'Translates text to target language',
                    'order': 7,
                    'enabled': True,
                    'prompt_template': 'Übersetze den folgenden Text EXAKT in {target_language}.\n\nAchte auf präzise medizinische Terminologie, wo angebracht, aber halte den Ton patientenfreundlich.\n\nText:\n{input_text}\n\nGib nur die Übersetzung zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.7,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'text'
                },
                {
                    'name': 'Final Quality Check',
                    'description': 'Final quality assurance and completeness check',
                    'order': 8,
                    'enabled': True,
                    'prompt_template': 'Führe eine finale Qualitätskontrolle dieses Textes durch.\n\nPrüfe auf Verständlichkeit, Vollständigkeit und patientenfreundliche Formulierung.\n\nText:\n{input_text}\n\nGib den final geprüften Text zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.5,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'text'
                },
                {
                    'name': 'Text Formatting',
                    'description': 'Applies markdown formatting and structure',
                    'order': 9,
                    'enabled': True,
                    'prompt_template': 'Formatiere diesen Text mit klaren Überschriften, Abschnitten und einer logischen Struktur.\n\nVerwende Markdown-Formatierung:\n- Überschriften mit #\n- Bullet Points für Listen\n- Fettschrift für wichtige Begriffe\n\nText:\n{input_text}\n\nGib nur den formatierten Markdown-Text zurück.',
                    'selected_model_id': llama_id,
                    'temperature': 0.3,
                    'max_tokens': 4096,
                    'retry_on_failure': True,
                    'max_retries': 2,
                    'input_from_previous_step': True,
                    'output_format': 'markdown'
                }
            ]

            for step in pipeline_steps:
                conn.execute(text("""
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
                """), {
                    **step,
                    'is_branching_step': step.get('is_branching_step', False),
                    'branching_field': step.get('branching_field', None),
                    'document_class_id': step.get('document_class_id', None),
                    'post_branching': step.get('post_branching', False),
                    'stop_conditions': json.dumps(step.get('stop_conditions')) if step.get('stop_conditions') else None,
                    'required_context_variables': json.dumps(step.get('required_context_variables')) if step.get('required_context_variables') else None,
                    'modified_by': 'system_seed'
                })

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
