"""
Unified Database Models for Universal Prompt System

This module contains the final, unified database models that replace
the old document-specific system with a universal approach.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

# Define enums directly to avoid pydantic dependency

class DocumentClassEnum(str, Enum):
    ARZTBRIEF = "ARZTBRIEF"
    BEFUNDBERICHT = "BEFUNDBERICHT"
    LABORWERTE = "LABORWERTE"

class ProcessingStepEnum(str, Enum):
    MEDICAL_VALIDATION = "MEDICAL_VALIDATION"
    CLASSIFICATION = "CLASSIFICATION"
    PREPROCESSING = "PREPROCESSING"
    TRANSLATION = "TRANSLATION"
    FACT_CHECK = "FACT_CHECK"
    GRAMMAR_CHECK = "GRAMMAR_CHECK"
    LANGUAGE_TRANSLATION = "LANGUAGE_TRANSLATION"
    FINAL_CHECK = "FINAL_CHECK"
    FORMATTING = "FORMATTING"

Base = declarative_base()

class UniversalPromptsDB(Base):
    """
    Database model for universal prompts used across all document types.
    These prompts are used for steps that should be the same regardless of document type.
    """
    __tablename__ = "universal_prompts"

    id = Column(Integer, primary_key=True, index=True)

    # Universal prompts - same for all document types
    medical_validation_prompt = Column(Text, nullable=False)
    classification_prompt = Column(Text, nullable=False)
    preprocessing_prompt = Column(Text, nullable=False)
    grammar_check_prompt = Column(Text, nullable=False)
    language_translation_prompt = Column(Text, nullable=False)

    # Metadata
    version = Column(Integer, default=1, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

class DocumentSpecificPromptsDB(Base):
    """
    Database model for document-type-specific prompts.
    These prompts are tailored to specific document types.
    """
    __tablename__ = "document_specific_prompts"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(SQLEnum(DocumentClassEnum), nullable=False, unique=True, index=True)

    # Document-specific prompts - tailored to each document type
    translation_prompt = Column(Text, nullable=False)  # Different complexity levels per doc type
    fact_check_prompt = Column(Text, nullable=False)   # Domain-specific medical validation
    final_check_prompt = Column(Text, nullable=False)  # Type-specific quality criteria
    formatting_prompt = Column(Text, nullable=False)   # Type-specific formatting rules

    # Metadata
    version = Column(Integer, default=1, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)

class UniversalPipelineStepConfigDB(Base):
    """
    Database model for universal pipeline step configurations.
    These settings apply to all document types globally.
    """
    __tablename__ = "universal_pipeline_steps"

    id = Column(Integer, primary_key=True, index=True)
    step_name = Column(SQLEnum(ProcessingStepEnum), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    order = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Metadata
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)

class AILogInteractionDB(Base):
    """
    Database model for AI interaction logging.
    Logs all AI interactions for analysis and debugging.
    """
    __tablename__ = "ai_interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    processing_id = Column(String(255), nullable=False, index=True)
    step_name = Column(String(100), nullable=False, index=True)
    input_text = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    model_used = Column(String(100), nullable=True)
    document_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    log_metadata = Column(JSON, nullable=True)

class SystemSettingsDB(Base):
    """
    Database model for system-wide settings.
    """
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=False)  # 'string', 'int', 'float', 'bool', 'json'
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    updated_by = Column(String(255), nullable=True)

class UserSessionDB(Base):
    """
    Database model for user sessions.
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    user_id = Column(String, nullable=True)  # Optional user ID if user management is added

    def __repr__(self):
        return f"<UserSessionDB(token='{self.session_token[:8]}...', expires='{self.expires_at}')>"
