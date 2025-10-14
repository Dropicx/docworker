"""
Optimized database models for universal vs document-specific prompts
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.document_types import DocumentClassEnum, ProcessingStepEnum

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
    grammar_check_prompt = Column(Text, nullable=False)  # Usually same for all
    language_translation_prompt = Column(
        Text, nullable=False
    )  # Template with {language} placeholder

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
    fact_check_prompt = Column(Text, nullable=False)  # Domain-specific medical validation
    final_check_prompt = Column(Text, nullable=False)  # Type-specific quality criteria
    formatting_prompt = Column(Text, nullable=False)  # Type-specific formatting rules

    # Metadata
    version = Column(Integer, default=1, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)

    # Relationships
    pipeline_steps = relationship(
        "OptimizedPipelineStepDB", back_populates="document_prompts", cascade="all, delete-orphan"
    )


class OptimizedPipelineStepDB(Base):
    """
    Optimized pipeline step configuration with universal/specific designation
    """

    __tablename__ = "optimized_pipeline_steps"

    id = Column(Integer, primary_key=True, index=True)
    document_prompts_id = Column(
        Integer, ForeignKey("document_specific_prompts.id"), nullable=True
    )  # Null for universal steps

    step_name = Column(SQLEnum(ProcessingStepEnum), nullable=False)
    is_universal = Column(
        Boolean, nullable=False
    )  # True for universal steps, False for doc-specific
    enabled = Column(Boolean, default=True, nullable=False)
    order = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Performance tracking
    avg_processing_time_ms = Column(Float, nullable=True)
    success_rate_percentage = Column(Float, nullable=True)
    cache_hit_rate_percentage = Column(Float, nullable=True)

    # Relationships
    document_prompts = relationship("DocumentSpecificPromptsDB", back_populates="pipeline_steps")


class PipelineConfigurationDB(Base):
    """
    Central pipeline configuration managing the flow
    """

    __tablename__ = "pipeline_configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)  # e.g., "optimized_v2", "legacy"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)

    # Configuration settings
    use_universal_prompts = Column(Boolean, default=True, nullable=False)
    enable_parallel_processing = Column(Boolean, default=True, nullable=False)
    cache_timeout_seconds = Column(Integer, default=300, nullable=False)

    # Pipeline flow definition
    pipeline_flow = Column(JSON, nullable=False)  # Ordered list of steps with their configurations

    # Performance settings
    max_concurrent_steps = Column(Integer, default=3, nullable=False)
    step_timeout_seconds = Column(Integer, default=120, nullable=False)

    # Metadata
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)


# Migration helper for existing data
class LegacyDocumentPromptsDB(Base):
    """
    Legacy model for backward compatibility during migration
    """

    __tablename__ = "legacy_document_prompts"

    id = Column(Integer, primary_key=True, index=True)
    document_type = Column(SQLEnum(DocumentClassEnum), nullable=False, unique=True, index=True)

    # All prompts in one table (legacy approach)
    medical_validation_prompt = Column(Text, nullable=False)
    classification_prompt = Column(Text, nullable=False)
    preprocessing_prompt = Column(Text, nullable=False)
    translation_prompt = Column(Text, nullable=False)
    fact_check_prompt = Column(Text, nullable=False)
    grammar_check_prompt = Column(Text, nullable=False)
    language_translation_prompt = Column(Text, nullable=False)
    final_check_prompt = Column(Text, nullable=False)
    formatting_prompt = Column(Text, nullable=False)

    # Metadata
    version = Column(Integer, default=1, nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)
    migrated_to_optimized = Column(Boolean, default=False, nullable=False)
    migration_date = Column(DateTime, nullable=True)
