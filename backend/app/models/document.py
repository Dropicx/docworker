from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class DocumentType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"  # In queue, waiting for worker
    PROCESSING = "processing"
    EXTRACTING_TEXT = "extracting_text"
    TRANSLATING = "translating"
    LANGUAGE_TRANSLATING = "language_translating"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"  # User cancelled processing
    TIMEOUT = "timeout"  # Processing exceeded time limit
    NON_MEDICAL_CONTENT = "non_medical_content"

class SupportedLanguage(str, Enum):
    # Sehr gut unterstützte Sprachen (beste Performance mit Llama 3.3)
    ENGLISH = "en"
    GERMAN = "de"  # Deutsch  
    FRENCH = "fr"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    
    # Gut unterstützte Sprachen
    RUSSIAN = "ru"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    HINDI = "hi"
    POLISH = "pl"
    CZECH = "cs"
    SWEDISH = "sv"
    NORWEGIAN = "no"
    DANISH = "da"

# Sprachname-Mapping für die UI
LANGUAGE_NAMES = {
    # Sehr gut unterstützte Sprachen
    SupportedLanguage.ENGLISH: "Englisch",
    SupportedLanguage.GERMAN: "Deutsch",
    SupportedLanguage.FRENCH: "Französisch",
    SupportedLanguage.SPANISH: "Spanisch",
    SupportedLanguage.ITALIAN: "Italienisch",
    SupportedLanguage.PORTUGUESE: "Portugiesisch",
    SupportedLanguage.DUTCH: "Niederländisch",
    
    # Gut unterstützte Sprachen
    SupportedLanguage.RUSSIAN: "Russisch",
    SupportedLanguage.CHINESE_SIMPLIFIED: "Chinesisch (Vereinfacht)",
    SupportedLanguage.CHINESE_TRADITIONAL: "Chinesisch (Traditionell)",
    SupportedLanguage.JAPANESE: "Japanisch",
    SupportedLanguage.KOREAN: "Koreanisch",
    SupportedLanguage.ARABIC: "Arabisch",
    SupportedLanguage.HINDI: "Hindi",
    SupportedLanguage.POLISH: "Polnisch",
    SupportedLanguage.CZECH: "Tschechisch",
    SupportedLanguage.SWEDISH: "Schwedisch",
    SupportedLanguage.NORWEGIAN: "Norwegisch",
    SupportedLanguage.DANISH: "Dänisch"
}

class ProcessingOptions(BaseModel):
    target_language: Optional[SupportedLanguage] = Field(None, description="Zielsprache für Übersetzung (optional)")

class UploadResponse(BaseModel):
    processing_id: str = Field(..., description="Eindeutige ID für die Verarbeitung")
    filename: str = Field(..., description="Ursprünglicher Dateiname")
    file_type: DocumentType = Field(..., description="Typ der hochgeladenen Datei")
    file_size: int = Field(..., description="Dateigröße in Bytes")
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    message: str = Field(default="Datei erfolgreich hochgeladen")

class ProcessingProgress(BaseModel):
    processing_id: str
    status: ProcessingStatus
    progress_percent: int = Field(ge=0, le=100)
    current_step: str
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class TranslationResult(BaseModel):
    processing_id: str
    original_text: str = Field(..., description="Ursprünglicher extrahierter Text")
    translated_text: str = Field(..., description="Übersetzter Text in einfacher Sprache")
    language_translated_text: Optional[str] = Field(None, description="In andere Sprache übersetzter Text")
    target_language: Optional[SupportedLanguage] = Field(None, description="Zielsprache der Übersetzung")
    document_type_detected: Optional[str] = Field(None, description="Erkannter Dokumenttyp")
    confidence_score: float = Field(ge=0, le=1, description="Vertrauensgrad der Übersetzung")
    language_confidence_score: Optional[float] = Field(None, description="Vertrauensgrad der Sprachübersetzung")
    processing_time_seconds: float = Field(..., description="Verarbeitungszeit in Sekunden")
    timestamp: datetime = Field(default_factory=datetime.now)

    # NEW: Dynamic branching metadata
    branching_path: Optional[List[Dict[str, Any]]] = Field(default=[], description="Complete decision tree of branching steps")
    document_class: Optional[Dict[str, Any]] = Field(None, description="Document classification details")
    total_steps: Optional[int] = Field(None, description="Total pipeline steps executed")
    pipeline_execution_time: Optional[float] = Field(None, description="Pipeline execution time in seconds")
    ocr_time_seconds: Optional[float] = Field(None, description="OCR processing time in seconds")
    ai_processing_time_seconds: Optional[float] = Field(None, description="AI pipeline processing time in seconds")

    class Config:
        # Allow extra fields (forward compatibility)
        extra = "allow"

class ErrorResponse(BaseModel):
    error: str
    message: str
    processing_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.now)
    services: Dict[str, str] = Field(default_factory=dict)
    memory_usage: Optional[Dict[str, Any]] = None

class ProcessingResponse(BaseModel):
    """Response model for multi-file processing results"""
    processing_id: str = Field(..., description="Unique processing identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    files_processed: int = Field(..., description="Number of files processed")
    total_files: int = Field(..., description="Total number of files to process")
    extracted_text: Optional[str] = Field(None, description="Combined extracted text from all files")
    translated_text: Optional[str] = Field(None, description="Translated text")
    confidence_score: Optional[float] = Field(None, description="Overall confidence score", ge=0, le=1)
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    file_details: Optional[List[Dict[str, Any]]] = Field(None, description="Details about each processed file")
    timestamp: datetime = Field(default_factory=datetime.now)

class CustomPrompts(BaseModel):
    """Custom prompts for document processing - aligned with unified system"""
    # Universal prompts (same for all document types)
    medical_validation_prompt: Optional[str] = Field(None, description="Prompt for medical content validation")
    classification_prompt: Optional[str] = Field(None, description="Prompt for document classification")
    preprocessing_prompt: Optional[str] = Field(None, description="Prompt for text preprocessing")
    language_translation_prompt: Optional[str] = Field(None, description="Prompt for language translation")
    ocr_preprocessing_prompt: Optional[str] = Field(None, description="Prompt for OCR text cleaning and preprocessing")

    # Document-specific prompts (vary by document type)
    translation_prompt: Optional[str] = Field(None, description="Document-specific translation prompt")
    fact_check_prompt: Optional[str] = Field(None, description="Medical fact checking prompt")
    grammar_check_prompt: Optional[str] = Field(None, description="Grammar and spelling correction prompt")
    final_check_prompt: Optional[str] = Field(None, description="Final quality check prompt")
    formatting_prompt: Optional[str] = Field(None, description="Document formatting prompt")

    class Config:
        extra = "allow"  # Allow additional prompt fields 