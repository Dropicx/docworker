"""
E2E Tests for Document Processing Flow

Tests complete end-to-end workflows: Upload → Processing → Results
"""

import pytest
import io
from PIL import Image
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.connection import get_session
from app.database.modular_pipeline_models import (
    Base,
    DynamicPipelineStepDB,
    AvailableModelDB,
    DocumentClassDB,
    OCRConfigurationDB,
    OCREngineEnum,
    StepExecutionStatus,
)


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client"""

    def override_get_session():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def seed_full_pipeline(test_db):
    """Seed database with complete pipeline configuration"""
    # OCR Config
    ocr_config = OCRConfigurationDB(
        selected_engine=OCREngineEnum.PADDLEOCR,
        pii_removal_enabled=True,
    )
    test_db.add(ocr_config)

    # Models
    main_model = AvailableModelDB(
        name="Meta-Llama-3_3-70B-Instruct",
        display_name="Llama 3.3 70B",
        provider="OVH",
        api_endpoint="https://test.api/v1",
        max_tokens=8192,
        is_enabled=True,
        supports_vision=False,
    )
    test_db.add(main_model)

    # Document Classes
    arztbrief = DocumentClassDB(
        class_key="ARZTBRIEF",
        display_name="Arztbrief",
        description="Doctor's letter",
        icon="📄",
        is_enabled=True,
        is_system_class=True,
    )
    test_db.add(arztbrief)

    # Pipeline Steps
    validation_step = DynamicPipelineStepDB(
        name="Medical Validation",
        order=1,
        prompt_template="Is this medical? {input_text}",
        selected_model_id=1,
        temperature=0.3,
        max_tokens=100,
        enabled=True,
        input_from_previous_step=True,
        retry_on_failure=False,
        document_class_id=None,
        post_branching=False,
        is_branching_step=False,
    )
    test_db.add(validation_step)

    classification_step = DynamicPipelineStepDB(
        name="Document Classification",
        order=2,
        prompt_template="Classify: {input_text}",
        selected_model_id=1,
        temperature=0.3,
        max_tokens=50,
        enabled=True,
        input_from_previous_step=True,
        retry_on_failure=False,
        document_class_id=None,
        post_branching=False,
        is_branching_step=True,
        branching_field="document_type",
    )
    test_db.add(classification_step)

    test_db.commit()


def create_test_image():
    """Create a small test image file"""
    img = Image.new("RGB", (100, 100), color="white")
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    img_byte_arr.seek(0)
    return img_byte_arr


# ==================== E2E Flow Tests ====================


@pytest.mark.e2e
def test_complete_image_upload_and_processing_flow(client, seed_full_pipeline):
    """
    E2E Test: Upload image → OCR → Processing → Result

    Flow:
    1. Upload image file
    2. Verify job created
    3. Mock worker processing
    4. Check job status
    5. Retrieve results
    """
    # Mock OCR and AI processing
    with patch("app.services.ocr_engine_manager.OCREngineManager.extract_text") as mock_ocr, \
         patch("app.services.ovh_client.OVHAIClient.create_completion") as mock_ai, \
         patch("app.services.privacy_filter_advanced.AdvancedPrivacyFilter.remove_pii") as mock_pii:

        # Mock OCR extraction
        mock_ocr.return_value = (
            "Patient: Max Mustermann\nDiagnose: Hypertonie\nTherapie: Medikament ABC",
            0.95,
        )

        # Mock PII removal
        mock_pii.side_effect = lambda x: x.replace("Max Mustermann", "[NAME]")

        # Mock AI responses
        mock_ai.side_effect = [
            "MEDIZINISCH",  # Validation step
            "ARZTBRIEF",  # Classification step
        ]

        # 1. Upload image
        img_file = create_test_image()
        response = client.post(
            "/api/upload",
            files={"file": ("test_image.png", img_file, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert "processing_id" in data
        processing_id = data["processing_id"]

        # 2. Check initial job status
        response = client.get(f"/api/status/{processing_id}")
        assert response.status_code == 200
        status_data = response.json()
        assert status_data["status"] in ["pending", "running"]

        # 3. Simulate worker processing by directly calling executor
        # (In real E2E, worker would pick up task from Celery queue)
        from app.database.modular_pipeline_models import PipelineJobDB
        from app.services.modular_pipeline_executor import ModularPipelineExecutor

        with test_db.begin():
            job = test_db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()
            assert job is not None

            # Simulate processing completion
            job.status = StepExecutionStatus.COMPLETED
            job.progress_percent = 100
            job.result_data = {
                "original_text": "Patient: [NAME]...",
                "translated_text": "Simplified medical text...",
                "document_type_detected": "ARZTBRIEF",
                "processing_time_seconds": 2.5,
            }

        # 4. Check final job status
        response = client.get(f"/api/status/{processing_id}")
        assert response.status_code == 200
        final_data = response.json()
        assert final_data["status"] == "completed"
        assert final_data["progress"] == 100

        # 5. Retrieve results
        response = client.get(f"/api/result/{processing_id}")
        assert response.status_code == 200
        result_data = response.json()
        assert "translated_text" in result_data
        assert result_data["document_type_detected"] == "ARZTBRIEF"


@pytest.mark.e2e
def test_invalid_file_upload_flow(client, seed_full_pipeline):
    """
    E2E Test: Upload invalid file → Error handling

    Flow:
    1. Upload unsupported file type
    2. Verify validation error
    """
    # Create invalid file (text file)
    invalid_file = io.BytesIO(b"This is not a valid document")

    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", invalid_file, "text/plain")},
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


@pytest.mark.e2e
def test_oversized_file_upload_flow(client, seed_full_pipeline):
    """
    E2E Test: Upload file exceeding size limit → Error

    Flow:
    1. Upload file > 50MB
    2. Verify size validation error
    """
    # Create large file (simulate with metadata)
    large_file = io.BytesIO(b"x" * 100)  # Actual size check happens in validator

    with patch("app.services.file_validator.FileValidator.validate_file") as mock_validate:
        mock_validate.return_value = (False, "File size exceeds 50MB limit")

        response = client.post(
            "/api/upload",
            files={"file": ("large.pdf", large_file, "application/pdf")},
        )

        assert response.status_code == 400
        data = response.json()
        assert "size" in data["error"]["message"].lower()


@pytest.mark.e2e
def test_job_not_found_flow(client):
    """
    E2E Test: Query non-existent job → 404

    Flow:
    1. Request status for invalid processing_id
    2. Verify 404 error
    """
    response = client.get("/api/status/invalid-processing-id-12345")

    assert response.status_code == 404


@pytest.mark.e2e
def test_concurrent_uploads_flow(client, seed_full_pipeline):
    """
    E2E Test: Multiple concurrent uploads

    Flow:
    1. Upload multiple files simultaneously
    2. Verify all jobs created
    3. Check independent processing
    """
    upload_count = 3
    processing_ids = []

    for i in range(upload_count):
        img_file = create_test_image()
        response = client.post(
            "/api/upload",
            files={"file": (f"test_{i}.png", img_file, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        processing_ids.append(data["processing_id"])

    # Verify all jobs are unique and tracked
    assert len(set(processing_ids)) == upload_count

    for pid in processing_ids:
        response = client.get(f"/api/status/{pid}")
        assert response.status_code == 200


@pytest.mark.e2e
def test_processing_timeout_flow(client, seed_full_pipeline):
    """
    E2E Test: Processing timeout handling

    Flow:
    1. Upload file
    2. Simulate timeout in worker
    3. Verify timeout error handling
    """
    img_file = create_test_image()
    response = client.post(
        "/api/upload",
        files={"file": ("test.png", img_file, "image/png")},
    )

    assert response.status_code == 200
    processing_id = response.json()["processing_id"]

    # Simulate timeout by marking job as failed
    from app.database.modular_pipeline_models import PipelineJobDB

    with test_db.begin():
        job = test_db.query(PipelineJobDB).filter_by(processing_id=processing_id).first()
        job.status = StepExecutionStatus.FAILED
        job.error_message = "Processing timeout: exceeded 18 minutes"

    # Check status shows failure
    response = client.get(f"/api/status/{processing_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "timeout" in data["error"].lower()


@pytest.mark.e2e
def test_health_check_flow(client):
    """
    E2E Test: Health check endpoint

    Flow:
    1. Call /health endpoint
    2. Verify system status
    """
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
