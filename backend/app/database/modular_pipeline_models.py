"""
Modular Pipeline Database Models

This module contains database models for the user-configurable modular pipeline system.
Users can configure OCR engines, create custom pipeline steps, manage available AI models,
and define custom document classes with their own pipeline branches.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON, Enum as SQLEnum, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
from app.database.unified_models import Base

# ==================== ENUMS ====================

class OCREngineEnum(str, Enum):
    """Available OCR engines"""
    PADDLEOCR = "PADDLEOCR"  # Fast CPU-based OCR
    VISION_LLM = "VISION_LLM"  # Slow but accurate (Qwen 2.5 VL)
    HYBRID = "HYBRID"  # Intelligent routing based on document quality
    # TESSERACT removed - poor quality

class StepExecutionStatus(str, Enum):
    """Pipeline step execution status"""
    PENDING = "PENDING"
    QUEUED = "QUEUED"  # In Redis queue, waiting for worker
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"  # User cancelled processing
    TIMEOUT = "TIMEOUT"  # Processing exceeded time limit
    TERMINATED = "TERMINATED"  # Pipeline stopped early due to stop condition

class ModelProvider(str, Enum):
    """AI model providers"""
    OVH = "OVH"  # OVH AI Endpoints
    OPENAI = "OPENAI"  # Future: OpenAI API
    ANTHROPIC = "ANTHROPIC"  # Future: Claude API
    LOCAL = "LOCAL"  # Future: Local models

# ==================== DATABASE MODELS ====================

class OCRConfigurationDB(Base):
    """
    OCR engine configuration (global setting).
    Users can select which OCR engine to use for text extraction.
    """
    __tablename__ = "ocr_configuration"

    id = Column(Integer, primary_key=True, index=True)

    # OCR engine selection
    selected_engine = Column(SQLEnum(OCREngineEnum), default=OCREngineEnum.PADDLEOCR, nullable=False)

    # Engine-specific settings (JSON for flexibility)
    # tesseract_config removed - Tesseract OCR deprecated
    paddleocr_config = Column(JSON, nullable=True)  # e.g., {"use_gpu": true, "lang": "german"}
    vision_llm_config = Column(JSON, nullable=True)  # e.g., {"model": "Qwen2.5-VL-72B-Instruct"}
    hybrid_config = Column(JSON, nullable=True)  # e.g., {"quality_threshold": 0.7}

    # Privacy settings
    pii_removal_enabled = Column(Boolean, default=True, nullable=False)  # Global PII removal toggle

    # Metadata
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<OCRConfigurationDB(engine='{self.selected_engine}')>"


class DocumentClassDB(Base):
    """
    Dynamic document classification types.
    Users can define custom document classes (e.g., ARZTBRIEF, BEFUNDBERICHT, LABORWERTE)
    and create separate pipeline branches for each class.
    """
    __tablename__ = "document_classes"

    id = Column(Integer, primary_key=True, index=True)

    # Class identification
    class_key = Column(String(100), nullable=False, unique=True, index=True)  # e.g., "ARZTBRIEF"
    display_name = Column(String(255), nullable=False)  # e.g., "Arztbrief"
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)  # emoji like "📨"

    # Examples and classification hints
    examples = Column(JSON, nullable=True)  # List of example documents
    strong_indicators = Column(JSON, nullable=True)  # Keywords for pattern matching
    weak_indicators = Column(JSON, nullable=True)

    # Status and permissions
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_system_class = Column(Boolean, default=False, nullable=False)  # Prevent deletion of core classes

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<DocumentClassDB(class_key='{self.class_key}', display_name='{self.display_name}')>"


class AvailableModelDB(Base):
    """
    Registry of available AI models for pipeline steps.
    Users can select from these models when creating pipeline steps.
    Includes pricing information for cost tracking.
    """
    __tablename__ = "available_models"

    id = Column(Integer, primary_key=True, index=True)

    # Model identification
    name = Column(String(255), nullable=False, unique=True, index=True)  # e.g., "Meta-Llama-3_3-70B-Instruct"
    display_name = Column(String(255), nullable=False)  # e.g., "Llama 3.3 70B (Main Model)"
    provider = Column(SQLEnum(ModelProvider), nullable=False)

    # Model capabilities
    description = Column(Text, nullable=True)
    max_tokens = Column(Integer, nullable=True)  # e.g., 8192
    supports_vision = Column(Boolean, default=False, nullable=False)

    # Pricing (USD per 1M tokens)
    price_input_per_1m_tokens = Column(Float, nullable=True)  # e.g., 0.54 (= $0.54 per 1M input tokens)
    price_output_per_1m_tokens = Column(Float, nullable=True)  # e.g., 0.81 (= $0.81 per 1M output tokens)

    # Model configuration
    model_config = Column(JSON, nullable=True)  # e.g., {"temperature": 0.7, "top_p": 0.9}

    # Availability
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<AvailableModelDB(name='{self.name}', provider='{self.provider}')>"


class DynamicPipelineStepDB(Base):
    """
    User-configurable pipeline steps.
    Each step has a custom prompt and selected AI model.
    Steps are executed in order based on the 'order' field.

    Pipeline Branching:
    - document_class_id = NULL: Universal step (runs for all documents)
    - document_class_id = ID: Class-specific step (runs only for that document class)
    - is_branching_step = True: Step that determines which branch to follow
    - post_branching = True: Universal step that runs AFTER document-specific processing
    """
    __tablename__ = "dynamic_pipeline_steps"

    id = Column(Integer, primary_key=True, index=True)

    # Step identification
    name = Column(String(255), nullable=False, index=True)  # e.g., "Medical Validation"
    description = Column(Text, nullable=True)

    # Execution order and status
    order = Column(Integer, nullable=False, index=True)  # 1, 2, 3, ... (OCR is always step 0)
    enabled = Column(Boolean, default=True, nullable=False)

    # Pipeline branching
    document_class_id = Column(Integer, ForeignKey('document_classes.id'), nullable=True, index=True)
    is_branching_step = Column(Boolean, default=False, nullable=False)
    branching_field = Column(String(100), nullable=True)  # Field to extract from output (e.g., "document_type")
    post_branching = Column(Boolean, default=False, nullable=False, index=True)  # Runs after doc-specific steps

    # Step configuration
    prompt_template = Column(Text, nullable=False)  # Custom prompt for this step
    selected_model_id = Column(Integer, nullable=False)  # FK to available_models

    # Advanced settings
    temperature = Column(Float, nullable=True, default=0.7)  # Model temperature
    max_tokens = Column(Integer, nullable=True)  # Override model default
    retry_on_failure = Column(Boolean, default=True, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Input/Output configuration
    input_from_previous_step = Column(Boolean, default=True, nullable=False)
    output_format = Column(String(50), nullable=True)  # e.g., "json", "markdown", "text"

    # Early termination conditions
    stop_conditions = Column(JSON, nullable=True)  # e.g., {"stop_on_values": ["NICHT_MEDIZINISCH"], "termination_reason": "Non-medical content detected", "termination_message": "Das hochgeladene Dokument enthält keinen medizinischen Inhalt."}

    # Conditional execution
    required_context_variables = Column(JSON, nullable=True)  # e.g., ["target_language"] - step will be skipped if these variables are not in context

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_modified = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    modified_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<DynamicPipelineStepDB(name='{self.name}', order={self.order}, enabled={self.enabled})>"


class PipelineJobDB(Base):
    """
    Pipeline job tracking for worker system.
    Tracks individual pipeline executions for monitoring and debugging.
    Worker-ready: designed for Redis queue integration.
    """
    __tablename__ = "pipeline_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job identification
    job_id = Column(String(255), nullable=False, unique=True, index=True)  # UUID
    processing_id = Column(String(255), nullable=False, index=True)  # Links to document processing

    # File storage (uploaded document)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # "pdf", "jpg", "png"
    file_size = Column(Integer, nullable=False)
    file_content = Column(LargeBinary, nullable=False)  # Binary file data

    # Upload metadata
    client_ip = Column(String(100), nullable=True)  # Client IP for security logging
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)

    # Job status
    status = Column(SQLEnum(StepExecutionStatus), default=StepExecutionStatus.PENDING, nullable=False, index=True)
    current_step_id = Column(Integer, nullable=True)  # Current pipeline step being executed
    progress_percent = Column(Integer, default=0, nullable=False)

    # Job configuration (worker-serializable)
    pipeline_config = Column(JSON, nullable=False)  # Snapshot of pipeline steps at job creation
    ocr_config = Column(JSON, nullable=False)  # Snapshot of OCR config at job creation

    # Execution details
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)

    # Results and errors
    result_data = Column(JSON, nullable=True)  # Final output
    error_message = Column(Text, nullable=True)
    error_step_id = Column(Integer, nullable=True)  # Step that caused failure

    # Worker information
    worker_id = Column(String(255), nullable=True)  # Worker that processed this job
    queue_name = Column(String(100), nullable=True)  # e.g., "ocr_queue", "ai_queue"

    # Performance metrics
    total_execution_time_seconds = Column(Float, nullable=True)
    ocr_time_seconds = Column(Float, nullable=True)
    ai_processing_time_seconds = Column(Float, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<PipelineJobDB(job_id='{self.job_id}', status='{self.status}', progress={self.progress_percent}%)>"


class PipelineStepExecutionDB(Base):
    """
    Individual step execution tracking within a pipeline job.
    Provides detailed logs for each step's execution.
    """
    __tablename__ = "pipeline_step_executions"

    id = Column(Integer, primary_key=True, index=True)

    # Links
    job_id = Column(String(255), nullable=False, index=True)  # FK to pipeline_jobs
    step_id = Column(Integer, nullable=False, index=True)  # FK to dynamic_pipeline_steps

    # Step details
    step_name = Column(String(255), nullable=False)
    step_order = Column(Integer, nullable=False)

    # Execution status
    status = Column(SQLEnum(StepExecutionStatus), default=StepExecutionStatus.PENDING, nullable=False)

    # Input/Output
    input_text = Column(Text, nullable=True)
    output_text = Column(Text, nullable=True)

    # Model information
    model_used = Column(String(255), nullable=True)
    prompt_used = Column(Text, nullable=True)

    # Execution metrics
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_time_seconds = Column(Float, nullable=True)

    # Quality metrics
    confidence_score = Column(Float, nullable=True)
    token_count_input = Column(Integer, nullable=True)
    token_count_output = Column(Integer, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Step-specific metadata (branching decisions, custom data)
    step_metadata = Column(JSON, nullable=True)  # Stores branching info, decisions, and step-specific data

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<PipelineStepExecutionDB(job_id='{self.job_id}', step='{self.step_name}', status='{self.status}')>"
