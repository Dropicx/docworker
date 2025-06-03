from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class DocumentType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing" 
    EXTRACTING_TEXT = "extracting_text"
    TRANSLATING = "translating"
    COMPLETED = "completed"
    ERROR = "error"

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
    document_type_detected: str = Field(..., description="Erkannter Dokumenttyp")
    confidence_score: float = Field(ge=0, le=1, description="Vertrauensgrad der Übersetzung")
    processing_time_seconds: float = Field(..., description="Verarbeitungszeit in Sekunden")
    timestamp: datetime = Field(default_factory=datetime.now)

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