from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class DocumentClass(str, Enum):
    """
    Three main document types for medical document classification
    """
    ARZTBRIEF = "ARZTBRIEF"  # Doctor's letters, discharge summaries, referrals
    BEFUNDBERICHT = "BEFUNDBERICHT"  # Medical reports, examination findings, imaging results
    LABORWERTE = "LABORWERTE"  # Lab results, blood tests, measurements

class PipelineStepConfig(BaseModel):
    """
    Configuration for individual pipeline steps
    """
    enabled: bool = Field(default=True, description="Whether this step is enabled")
    order: int = Field(..., description="Order of execution in the pipeline")
    name: str = Field(..., description="Human-readable name of the step")
    description: str = Field(..., description="Description of what this step does")

class DocumentPrompts(BaseModel):
    """
    Complete set of prompts for each document type
    Each step in the processing pipeline has its own customizable prompt
    """
    document_type: DocumentClass = Field(..., description="Type of medical document")

    # Processing pipeline prompts
    classification_prompt: str = Field(..., description="Prompt for AI-based document classification")
    preprocessing_prompt: str = Field(..., description="Prompt for data cleaning and PII removal")
    translation_prompt: str = Field(..., description="Main prompt for medical text simplification")
    fact_check_prompt: str = Field(..., description="Prompt for verifying medical accuracy")
    grammar_check_prompt: str = Field(..., description="Prompt for German grammar correction")
    language_translation_prompt: str = Field(..., description="Prompt for target language translation")
    final_check_prompt: str = Field(..., description="Prompt for final quality assurance")

    # Pipeline step configuration
    pipeline_steps: Dict[str, PipelineStepConfig] = Field(
        default_factory=lambda: {
            "MEDICAL_VALIDATION": PipelineStepConfig(enabled=True, order=1, name="Medical Content Validation", description="Validate if document contains medical content"),
            "CLASSIFICATION": PipelineStepConfig(enabled=True, order=2, name="Document Classification", description="Classify document type (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)"),
            "PREPROCESSING": PipelineStepConfig(enabled=True, order=3, name="Preprocessing", description="Remove PII and clean text"),
            "TRANSLATION": PipelineStepConfig(enabled=True, order=4, name="Translation", description="Translate to simple language"),
            "FACT_CHECK": PipelineStepConfig(enabled=True, order=5, name="Fact Check", description="Verify medical accuracy"),
            "GRAMMAR_CHECK": PipelineStepConfig(enabled=True, order=6, name="Grammar Check", description="Correct German grammar"),
            "LANGUAGE_TRANSLATION": PipelineStepConfig(enabled=True, order=7, name="Language Translation", description="Translate to target language"),
            "FINAL_CHECK": PipelineStepConfig(enabled=True, order=8, name="Final Check", description="Final quality assurance"),
            "FORMATTING": PipelineStepConfig(enabled=True, order=9, name="Formatting", description="Apply text formatting")
        },
        description="Configuration for each pipeline step"
    )

    # Metadata
    version: int = Field(default=1, description="Version number of the prompt set")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification timestamp")
    modified_by: Optional[str] = Field(None, description="User who last modified the prompts")

class DocumentClassificationResult(BaseModel):
    """
    Result of document classification
    """
    document_class: DocumentClass = Field(..., description="Detected document class")
    confidence: float = Field(ge=0, le=1, description="Confidence score of classification")
    method: str = Field(..., description="Classification method used (pattern|ai)")
    processing_hints: Optional[Dict[str, Any]] = Field(None, description="Hints for processing based on document type")

class PromptTestRequest(BaseModel):
    """
    Request for testing a prompt with sample text
    """
    prompt: str = Field(..., description="The prompt to test")
    sample_text: str = Field(..., description="Sample text to test the prompt with")
    model: Optional[str] = Field(None, description="Specific model to use for testing")
    temperature: float = Field(default=0.3, ge=0, le=1, description="Temperature for generation")
    max_tokens: int = Field(default=1000, ge=100, le=4000, description="Maximum tokens to generate")

class PromptTestResponse(BaseModel):
    """
    Response from prompt testing
    """
    result: str = Field(..., description="Generated result from the prompt")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    processing_time: float = Field(..., description="Processing time in seconds")
    model_used: str = Field(..., description="Model that was used")

# Document type descriptions for UI
DOCUMENT_TYPE_DESCRIPTIONS = {
    DocumentClass.ARZTBRIEF: {
        "name": "Arztbrief",
        "description": "Briefe zwischen Ärzten, Entlassungsbriefe, Überweisungen",
        "examples": ["Entlassungsbrief", "Überweisungsschreiben", "Konsiliarbericht", "Therapiebericht"],
        "icon": "📨"
    },
    DocumentClass.BEFUNDBERICHT: {
        "name": "Befundbericht",
        "description": "Medizinische Befunde, Untersuchungsergebnisse, Bildgebung",
        "examples": ["MRT-Befund", "CT-Bericht", "Ultraschallbefund", "Pathologiebefund"],
        "icon": "🔬"
    },
    DocumentClass.LABORWERTE: {
        "name": "Laborwerte",
        "description": "Laborergebnisse, Blutwerte, Messwerte mit Referenzbereichen",
        "examples": ["Blutbild", "Urinanalyse", "Hormonwerte", "Tumormarker"],
        "icon": "🧪"
    }
}

# Classification keywords for pattern matching
CLASSIFICATION_PATTERNS = {
    DocumentClass.ARZTBRIEF: {
        "strong_indicators": [
            "sehr geehrte", "liebe kollegin", "lieber kollege",
            "mit freundlichen grüßen", "hochachtungsvoll", "gez.",
            "entlassung", "entlassen", "überweisung", "überweisen",
            "vorstellung", "konsil", "therapiebericht"
        ],
        "weak_indicators": [
            "patient wurde", "anamnese", "diagnose", "therapie",
            "empfehlung", "weiteres vorgehen", "rückfragen"
        ]
    },
    DocumentClass.BEFUNDBERICHT: {
        "strong_indicators": [
            "befund", "befundbericht", "untersuchung vom",
            "röntgen", "ct", "mrt", "mri", "ultraschall", "sonographie",
            "szintigraphie", "pet", "angiographie", "mammographie",
            "darstellung", "kontrastmittel", "schnittbild", "aufnahme"
        ],
        "weak_indicators": [
            "auffällig", "unauffällig", "verdacht", "hinweis",
            "tumor", "metastase", "zyste", "knoten", "herd",
            "fraktur", "läsion", "infiltrat", "erguss"
        ]
    },
    DocumentClass.LABORWERTE: {
        "strong_indicators": [
            "laborwerte", "blutwerte", "blutbild", "hämatologie",
            "mg/dl", "mmol/l", "µg/l", "u/l", "g/dl", "pg/ml",
            "referenzbereich", "normalbereich", "norm", "referenz",
            "hba1c", "cholesterin", "ldl", "hdl", "triglyceride",
            "kreatinin", "gfr", "tsh", "psa", "ck", "troponin"
        ],
        "weak_indicators": [
            "erhöht", "erniedrigt", "normal", "pathologisch",
            "urin", "urinstatus", "urinkultur",
            "bakterien", "keime", "resistenz", "antibiogramm"
        ]
    }
}