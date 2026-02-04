"""
Pytest Configuration and Shared Fixtures

This module provides shared fixtures for all test files including:
- Database session fixtures (in-memory SQLite)
- Test data factories
- Mock patterns for repositories and services
- Cleanup utilities
"""

import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typing import Generator

from app.database.unified_models import Base, AILogInteractionDB, SystemSettingsDB, UserSessionDB
from app.database.modular_pipeline_models import (
    OCRConfigurationDB,
    DocumentClassDB,
    AvailableModelDB,
    DynamicPipelineStepDB,
    PipelineJobDB,
    PipelineStepExecutionDB,
    OCREngineEnum,
    StepExecutionStatus,
    ModelProvider,
)


# ==================== DATABASE FIXTURES ====================


@pytest.fixture(scope="function")
def test_db_engine():
    """
    Create in-memory SQLite database engine for testing.

    Uses function scope so each test gets a fresh database.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create database session for testing.

    Automatically rolls back after each test to ensure isolation.

    Usage:
        def test_something(db_session):
            user = User(name="Test")
            db_session.add(user)
            db_session.commit()
    """
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ==================== MODEL FACTORY FIXTURES ====================


@pytest.fixture
def create_ai_log_interaction(db_session):
    """
    Factory for creating AI log interaction test data.

    Usage:
        log = create_ai_log_interaction(processing_id="test-123")
    """

    def _create(
        processing_id: str = "test-processing-id",
        step_name: str = "test_step",
        input_tokens: int = 100,
        output_tokens: int = 50,
        total_tokens: int = 150,
        input_cost_usd: float = 0.001,
        output_cost_usd: float = 0.002,
        total_cost_usd: float = 0.003,
        model_provider: str = "OVH",
        model_name: str = "Meta-Llama-3_3-70B-Instruct",
        document_type: str = "ARZTBRIEF",
        **kwargs,
    ) -> AILogInteractionDB:
        log = AILogInteractionDB(
            processing_id=processing_id,
            step_name=step_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost_usd=input_cost_usd,
            output_cost_usd=output_cost_usd,
            total_cost_usd=total_cost_usd,
            model_provider=model_provider,
            model_name=model_name,
            document_type=document_type,
            **kwargs,
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)
        return log

    return _create


@pytest.fixture
def create_system_setting(db_session):
    """
    Factory for creating system settings test data.

    Usage:
        setting = create_system_setting(key="feature.enabled", value="true")
    """

    def _create(
        key: str = "test.setting",
        value: str = "test_value",
        value_type: str = "string",
        description: str = "Test setting",
        is_encrypted: bool = False,
        **kwargs,
    ) -> SystemSettingsDB:
        setting = SystemSettingsDB(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            is_encrypted=is_encrypted,
            **kwargs,
        )
        db_session.add(setting)
        db_session.commit()
        db_session.refresh(setting)
        return setting

    return _create


@pytest.fixture
def create_user_session(db_session):
    """
    Factory for creating user session test data.

    Usage:
        session = create_user_session(session_token="abc123")
    """

    def _create(
        session_token: str = "test-session-token",
        expires_at: datetime = None,
        user_id: str = None,
        **kwargs,
    ) -> UserSessionDB:
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

        session = UserSessionDB(
            session_token=session_token, expires_at=expires_at, user_id=user_id, **kwargs
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    return _create


@pytest.fixture
def create_ocr_configuration(db_session):
    """
    Factory for creating OCR configuration test data.

    Usage:
        config = create_ocr_configuration(selected_engine=OCREngineEnum.PADDLEOCR)
    """

    def _create(
        selected_engine: OCREngineEnum = OCREngineEnum.PADDLEOCR,
        paddleocr_config: dict = None,
        mistral_ocr_config: dict = None,
        pii_removal_enabled: bool = True,
        **kwargs,
    ) -> OCRConfigurationDB:
        config = OCRConfigurationDB(
            selected_engine=selected_engine,
            paddleocr_config=paddleocr_config,
            mistral_ocr_config=mistral_ocr_config,
            pii_removal_enabled=pii_removal_enabled,
            **kwargs,
        )
        db_session.add(config)
        db_session.commit()
        db_session.refresh(config)
        return config

    return _create


@pytest.fixture
def create_document_class(db_session):
    """
    Factory for creating document class test data.

    Usage:
        doc_class = create_document_class(class_key="ARZTBRIEF")
    """

    def _create(
        class_key: str = "TEST_DOCUMENT",
        display_name: str = "Test Document",
        description: str = "Test document class",
        icon: str = "📄",
        examples: list = None,
        strong_indicators: list = None,
        weak_indicators: list = None,
        is_enabled: bool = True,
        is_system_class: bool = False,
        **kwargs,
    ) -> DocumentClassDB:
        doc_class = DocumentClassDB(
            class_key=class_key,
            display_name=display_name,
            description=description,
            icon=icon,
            examples=examples,
            strong_indicators=strong_indicators,
            weak_indicators=weak_indicators,
            is_enabled=is_enabled,
            is_system_class=is_system_class,
            **kwargs,
        )
        db_session.add(doc_class)
        db_session.commit()
        db_session.refresh(doc_class)
        return doc_class

    return _create


@pytest.fixture
def create_available_model(db_session):
    """
    Factory for creating available model test data.

    Usage:
        model = create_available_model(name="Meta-Llama-3_3-70B-Instruct")
    """

    def _create(
        name: str = "Test-Model",
        display_name: str = "Test Model",
        provider: ModelProvider = ModelProvider.OVH,
        description: str = "Test AI model",
        max_tokens: int = 4096,
        supports_vision: bool = False,
        price_input_per_1m_tokens: float = 0.54,
        price_output_per_1m_tokens: float = 0.81,
        model_config: dict = None,
        is_enabled: bool = True,
        **kwargs,
    ) -> AvailableModelDB:
        model = AvailableModelDB(
            name=name,
            display_name=display_name,
            provider=provider,
            description=description,
            max_tokens=max_tokens,
            supports_vision=supports_vision,
            price_input_per_1m_tokens=price_input_per_1m_tokens,
            price_output_per_1m_tokens=price_output_per_1m_tokens,
            model_config=model_config,
            is_enabled=is_enabled,
            **kwargs,
        )
        db_session.add(model)
        db_session.commit()
        db_session.refresh(model)
        return model

    return _create


@pytest.fixture
def create_pipeline_step(db_session):
    """
    Factory for creating pipeline step test data.

    Usage:
        step = create_pipeline_step(name="Medical Validation", order=1)
    """

    def _create(
        name: str = "Test Step",
        description: str = "Test pipeline step",
        order: int = 1,
        enabled: bool = True,
        document_class_id: int = None,
        is_branching_step: bool = False,
        branching_field: str = None,
        post_branching: bool = False,
        prompt_template: str = "Test prompt",
        selected_model_id: int = 1,
        temperature: float = 0.7,
        max_tokens: int = None,
        retry_on_failure: bool = True,
        max_retries: int = 3,
        input_from_previous_step: bool = True,
        output_format: str = "text",
        stop_conditions: dict = None,
        required_context_variables: list = None,
        **kwargs,
    ) -> DynamicPipelineStepDB:
        step = DynamicPipelineStepDB(
            name=name,
            description=description,
            order=order,
            enabled=enabled,
            document_class_id=document_class_id,
            is_branching_step=is_branching_step,
            branching_field=branching_field,
            post_branching=post_branching,
            prompt_template=prompt_template,
            selected_model_id=selected_model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            retry_on_failure=retry_on_failure,
            max_retries=max_retries,
            input_from_previous_step=input_from_previous_step,
            output_format=output_format,
            stop_conditions=stop_conditions,
            required_context_variables=required_context_variables,
            **kwargs,
        )
        db_session.add(step)
        db_session.commit()
        db_session.refresh(step)
        return step

    return _create


@pytest.fixture
def create_pipeline_job(db_session):
    """
    Factory for creating pipeline job test data.

    Usage:
        job = create_pipeline_job(job_id="test-job-123")
    """

    def _create(
        job_id: str = "test-job-id",
        processing_id: str = "test-processing-id",
        filename: str = "test.pdf",
        file_type: str = "pdf",
        file_size: int = 1024,
        file_content: bytes = b"test content",
        status: StepExecutionStatus = StepExecutionStatus.PENDING,
        current_step_id: int = None,
        progress_percent: int = 0,
        pipeline_config: dict = None,
        ocr_config: dict = None,
        processing_options: dict = None,
        error_message: str = None,
        **kwargs,
    ) -> PipelineJobDB:
        if pipeline_config is None:
            pipeline_config = {"steps": []}
        if ocr_config is None:
            ocr_config = {"engine": "PADDLEOCR"}
        if processing_options is None:
            processing_options = {}

        job = PipelineJobDB(
            job_id=job_id,
            processing_id=processing_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_content=file_content,
            status=status,
            current_step_id=current_step_id,
            progress_percent=progress_percent,
            pipeline_config=pipeline_config,
            ocr_config=ocr_config,
            processing_options=processing_options,
            error_message=error_message,
            **kwargs,
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    return _create


@pytest.fixture
def create_pipeline_step_execution(db_session):
    """
    Factory for creating pipeline step execution test data.

    Usage:
        execution = create_pipeline_step_execution(job_id="test-job-123")
    """

    def _create(
        job_id: str = "test-job-id",
        step_id: int = 1,
        step_name: str = "Test Step",
        step_order: int = 1,
        status: StepExecutionStatus = StepExecutionStatus.PENDING,
        input_text: str = None,
        output_text: str = None,
        model_used: str = None,
        prompt_used: str = None,
        confidence_score: float = None,
        token_count_input: int = None,
        token_count_output: int = None,
        error_message: str = None,
        retry_count: int = 0,
        step_metadata: dict = None,
        **kwargs,
    ) -> PipelineStepExecutionDB:
        execution = PipelineStepExecutionDB(
            job_id=job_id,
            step_id=step_id,
            step_name=step_name,
            step_order=step_order,
            status=status,
            input_text=input_text,
            output_text=output_text,
            model_used=model_used,
            prompt_used=prompt_used,
            confidence_score=confidence_score,
            token_count_input=token_count_input,
            token_count_output=token_count_output,
            error_message=error_message,
            retry_count=retry_count,
            step_metadata=step_metadata,
            **kwargs,
        )
        db_session.add(execution)
        db_session.commit()
        db_session.refresh(execution)
        return execution

    return _create


# ==================== SAMPLE DATA FIXTURES ====================


@pytest.fixture
def sample_arztbrief_document_class(create_document_class):
    """
    Create sample ARZTBRIEF document class for testing.
    """
    return create_document_class(
        class_key="ARZTBRIEF",
        display_name="Arztbrief",
        description="Doctor's letters and discharge summaries",
        icon="📨",
        strong_indicators=["Arztbrief", "Entlassungsbericht"],
        is_system_class=True,
    )


@pytest.fixture
def sample_llama_model(create_available_model):
    """
    Create sample Llama 3.3 70B model for testing.
    """
    return create_available_model(
        name="Meta-Llama-3_3-70B-Instruct",
        display_name="Llama 3.3 70B (Main Model)",
        provider=ModelProvider.OVH,
        description="Primary model for medical translation",
        max_tokens=8192,
        supports_vision=False,
        price_input_per_1m_tokens=0.54,
        price_output_per_1m_tokens=0.81,
        is_enabled=True,
    )


@pytest.fixture
def sample_pipeline_with_steps(
    db_session, sample_llama_model, sample_arztbrief_document_class, create_pipeline_step
):
    """
    Create a complete sample pipeline with multiple steps for testing.
    """
    steps = []

    # Universal step: Medical Validation
    steps.append(
        create_pipeline_step(
            name="Medical Validation",
            description="Validate medical content",
            order=1,
            prompt_template="Validate if this is medical content: {input}",
            selected_model_id=sample_llama_model.id,
            enabled=True,
        )
    )

    # Branching step: Classification
    steps.append(
        create_pipeline_step(
            name="Classification",
            description="Classify document type",
            order=2,
            is_branching_step=True,
            branching_field="document_type",
            prompt_template="Classify this document: {input}",
            selected_model_id=sample_llama_model.id,
            enabled=True,
        )
    )

    # Document-specific step: ARZTBRIEF Translation
    steps.append(
        create_pipeline_step(
            name="Arztbrief Translation",
            description="Translate ARZTBRIEF documents",
            order=3,
            document_class_id=sample_arztbrief_document_class.id,
            prompt_template="Translate this Arztbrief: {input}",
            selected_model_id=sample_llama_model.id,
            enabled=True,
        )
    )

    # Post-branching step: Final Check
    steps.append(
        create_pipeline_step(
            name="Final Check",
            description="Quality assurance check",
            order=4,
            post_branching=True,
            prompt_template="Perform final check: {input}",
            selected_model_id=sample_llama_model.id,
            enabled=True,
        )
    )

    return steps


# ==================== MOCK FIXTURES ====================


@pytest.fixture
def mock_ovh_ai_client(monkeypatch):
    """
    Mock OVH AI client for testing without external API calls.

    Usage:
        def test_something(mock_ovh_ai_client):
            # OVH AI calls will be mocked
            response = ai_client.generate("test prompt")
    """

    class MockOVHResponse:
        def __init__(self, content: str = "Mocked AI response"):
            self.content = content
            self.usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}

    def mock_generate(*args, **kwargs):
        return MockOVHResponse()

    # This is a placeholder - actual mocking will be done in service tests
    return mock_generate


@pytest.fixture
def mock_redis_client(monkeypatch):
    """
    Mock Redis client for testing without Redis dependency.

    Usage:
        def test_something(mock_redis_client):
            # Redis calls will be mocked
    """

    class MockRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value

        def delete(self, key):
            self.data.pop(key, None)

    return MockRedis()


# ==================== CLEANUP FIXTURES ====================


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Automatically cleanup after each test.

    This fixture runs after every test to ensure clean state.
    """
    yield
    # Cleanup code here if needed
    pass
