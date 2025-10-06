"""
System-Wide Database Models

This module contains database models for system settings and logging.
Legacy prompt models have been removed - use modular_pipeline_models instead.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

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
