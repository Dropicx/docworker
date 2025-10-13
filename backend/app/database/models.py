"""
Database models using SQLAlchemy
"""

from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class DocumentClassEnum(str, Enum):
    """Document class enumeration for database"""
    ARZTBRIEF = "ARZTBRIEF"
    BEFUNDBERICHT = "BEFUNDBERICHT"
    LABORWERTE = "LABORWERTE"

class ProcessingStepEnum(str, Enum):
    """Processing step enumeration for database"""
    TEXT_EXTRACTION = "TEXT_EXTRACTION"  # Enhanced OCR with conditional routing - STEP 0
    MEDICAL_VALIDATION = "MEDICAL_VALIDATION"  # STEP 1
    CLASSIFICATION = "CLASSIFICATION"  # STEP 2
    PREPROCESSING = "PREPROCESSING"  # STEP 3
    TRANSLATION = "TRANSLATION"  # STEP 4
    FACT_CHECK = "FACT_CHECK"  # STEP 5
    GRAMMAR_CHECK = "GRAMMAR_CHECK"  # STEP 6
    LANGUAGE_TRANSLATION = "LANGUAGE_TRANSLATION"  # STEP 7
    FINAL_CHECK = "FINAL_CHECK"  # STEP 8
    FORMATTING = "FORMATTING"  # STEP 9

# DocumentPromptsDB and PipelineStepConfigDB removed - replaced by unified system
# Use DocumentSpecificPromptsDB and UniversalPipelineStepConfigDB from app.database.unified_models instead

class AIInteractionLog(Base):
    """Database model for comprehensive AI interaction logging"""
    __tablename__ = "ai_interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    processing_id = Column(String(255), nullable=False, index=True)
    step_name = Column(SQLEnum(ProcessingStepEnum), nullable=False, index=True)
    document_type = Column(SQLEnum(DocumentClassEnum), nullable=True, index=True)

    # Input data
    input_text = Column(Text, nullable=True)
    input_length = Column(Integer, nullable=True)
    input_metadata = Column(JSON, nullable=True)  # Additional input context

    # AI request details
    model_used = Column(String(255), nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    prompt_used = Column(Text, nullable=True)

    # Output data
    output_text = Column(Text, nullable=True)
    output_length = Column(Integer, nullable=True)
    output_metadata = Column(JSON, nullable=True)  # Additional output context

    # Performance metrics
    processing_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    token_count = Column(Integer, nullable=True)

    # Status and error handling
    status = Column(String(50), nullable=False, default="success")  # success, error, skipped
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    # Additional context
    user_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    request_id = Column(String(255), nullable=True, index=True)

class SystemSettingsDB(Base):
    """Database model for system-wide settings"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    value_type = Column(String(50), nullable=False, default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)

class UserSessionsDB(Base):
    """Database model for user authentication sessions"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Session metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Additional context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
