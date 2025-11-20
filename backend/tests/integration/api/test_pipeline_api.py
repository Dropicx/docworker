"""
API Integration Tests for Pipeline Endpoints

Tests FastAPI endpoints with TestClient, mocked auth, and real database.
"""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Import ALL models to register them with Base.metadata before create_all()
from app.database import auth_models, modular_pipeline_models, unified_models  # noqa: F401
from app.database.connection import get_session
from app.database.modular_pipeline_models import (
    AvailableModelDB,
    DocumentClassDB,
    DynamicPipelineStepDB,
    OCRConfigurationDB,
    OCREngineEnum,
)
from app.database.unified_models import Base
from app.main import app


@pytest.fixture(scope="function")
def test_db():
    """Create test database session

    Uses StaticPool to ensure all connections share the same in-memory database.
    Without this, each connection would get its own separate in-memory database.
    """
    from app.database.auth_models import Base as AuthBase

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all tables from all bases
    Base.metadata.create_all(engine)
    AuthBase.metadata.create_all(engine)

    session_local = sessionmaker(bind=engine)
    session = session_local()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
    AuthBase.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with mocked database"""

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
def mock_auth(test_db):
    """Mock authentication for protected endpoints using FastAPI dependency override"""
    from app.core.permissions import get_current_user_required
    from app.database.auth_models import UserDB, UserRole

    # Create a mock user
    mock_user = UserDB(
        email="test@example.com",
        full_name="Test User",
        role=UserRole.ADMIN,
        is_active=True,
        password_hash="test_hash",
    )
    test_db.add(mock_user)
    test_db.commit()

    # Create a mock dependency that returns the mock user
    async def mock_get_current_user() -> UserDB:
        return mock_user

    # Override the dependency in the FastAPI app
    app.dependency_overrides[get_current_user_required] = mock_get_current_user

    yield

    # Clean up after test
    if get_current_user_required in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_required]


@pytest.fixture
def seed_test_data(test_db):
    """Seed database with test data"""
    # Add OCR config
    ocr_config = OCRConfigurationDB(
        selected_engine=OCREngineEnum.PADDLEOCR,
        pii_removal_enabled=True,
    )
    test_db.add(ocr_config)

    # Add models
    model = AvailableModelDB(
        name="Meta-Llama-3_3-70B-Instruct",
        display_name="Llama 3.3 70B",
        provider="OVH",
        max_tokens=8192,
        is_enabled=True,
        supports_vision=False,
    )
    test_db.add(model)

    # Add document class
    doc_class = DocumentClassDB(
        class_key="ARZTBRIEF",
        display_name="Arztbrief",
        description="Doctor's letter",
        icon="📄",
        is_enabled=True,
        is_system_class=True,
    )
    test_db.add(doc_class)

    # Add pipeline step
    step = DynamicPipelineStepDB(
        name="Test Step",
        order=1,
        prompt_template="Process: {input_text}",
        selected_model_id=1,
        temperature=0.7,
        max_tokens=1000,
        enabled=True,
        input_from_previous_step=True,
        retry_on_failure=True,
        max_retries=3,
    )
    test_db.add(step)

    test_db.commit()


# ==================== OCR Configuration Tests ====================


def test_get_ocr_config(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/ocr-config"""
    response = client.get("/api/pipeline/ocr-config")

    assert response.status_code == 200
    data = response.json()
    assert data["selected_engine"] == "PADDLEOCR"
    assert data["pii_removal_enabled"] is True


def test_update_ocr_config(client, mock_auth, seed_test_data):
    """Test PUT /api/pipeline/ocr-config"""
    response = client.put(
        "/api/pipeline/ocr-config",
        json={
            "selected_engine": "HYBRID",
            "pii_removal_enabled": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["selected_engine"] == "HYBRID"
    assert data["pii_removal_enabled"] is False


def test_get_available_engines(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/ocr-engines"""
    # Mock PaddleOCR health check to simulate service availability
    from unittest.mock import patch

    with patch(
        "app.services.ocr_engine_manager.OCREngineManager._check_paddleocr_health_sync"
    ) as mock_health:
        mock_health.return_value = True

        response = client.get("/api/pipeline/ocr-engines")

        assert response.status_code == 200
        data = response.json()
        assert "PADDLEOCR" in data
        assert "HYBRID" in data
        assert data["PADDLEOCR"]["available"] is True


# ==================== Pipeline Steps Tests ====================


def test_get_all_steps(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/steps"""
    response = client.get("/api/pipeline/steps")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Test Step"


def test_get_single_step(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/steps/{step_id}"""
    response = client.get("/api/pipeline/steps/1")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Step"
    assert data["order"] == 1


def test_create_step(client, mock_auth, seed_test_data):
    """Test POST /api/pipeline/steps"""
    new_step = {
        "name": "New Test Step",
        "description": "A new test step",
        "order": 2,
        "enabled": True,
        "prompt_template": "New prompt: {input_text}",
        "selected_model_id": 1,
        "temperature": 0.5,
        "max_tokens": 500,
        "retry_on_failure": True,
        "max_retries": 2,
        "input_from_previous_step": True,
        "output_format": "text",
    }

    response = client.post("/api/pipeline/steps", json=new_step)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Test Step"
    assert data["order"] == 2


def test_update_step(client, mock_auth, seed_test_data):
    """Test PUT /api/pipeline/steps/{step_id}"""
    updated_step = {
        "name": "Updated Test Step",
        "order": 1,
        "enabled": False,
        "prompt_template": "Updated: {input_text}",
        "selected_model_id": 1,
        "temperature": 0.8,
        "max_tokens": 2000,
        "retry_on_failure": False,
        "max_retries": 1,
        "input_from_previous_step": True,
        "output_format": "json",
    }

    response = client.put("/api/pipeline/steps/1", json=updated_step)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Test Step"
    assert data["enabled"] is False


def test_delete_step(client, mock_auth, seed_test_data):
    """Test DELETE /api/pipeline/steps/{step_id}"""
    response = client.delete("/api/pipeline/steps/1")

    assert response.status_code == 204

    # Verify deletion
    response = client.get("/api/pipeline/steps/1")
    assert response.status_code == 404


def test_reorder_steps(client, mock_auth, seed_test_data):
    """Test POST /api/pipeline/steps/reorder"""
    # Create second step
    client.post(
        "/api/pipeline/steps",
        json={
            "name": "Second Step",
            "order": 2,
            "enabled": True,
            "prompt_template": "Test: {input_text}",
            "selected_model_id": 1,
            "temperature": 0.7,
            "max_tokens": 1000,
            "retry_on_failure": True,
            "max_retries": 3,
            "input_from_previous_step": True,
        },
    )

    response = client.post("/api/pipeline/steps/reorder", json={"step_ids": [2, 1]})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


# ==================== AI Models Tests ====================


def test_get_available_models(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/models"""
    response = client.get("/api/pipeline/models")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["name"] == "Meta-Llama-3_3-70B-Instruct"


def test_get_single_model(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/models/{model_id}"""
    response = client.get("/api/pipeline/models/1")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Meta-Llama-3_3-70B-Instruct"
    assert data["provider"] == "OVH"


# ==================== Document Classes Tests ====================


def test_get_all_document_classes(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/document-classes"""
    response = client.get("/api/pipeline/document-classes")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["class_key"] == "ARZTBRIEF"


def test_get_single_document_class(client, mock_auth, seed_test_data):
    """Test GET /api/pipeline/document-classes/{class_id}"""
    response = client.get("/api/pipeline/document-classes/1")

    assert response.status_code == 200
    data = response.json()
    assert data["class_key"] == "ARZTBRIEF"
    assert data["display_name"] == "Arztbrief"


def test_create_document_class(client, mock_auth, seed_test_data):
    """Test POST /api/pipeline/document-classes"""
    new_class = {
        "class_key": "THERAPIEPLAN",
        "display_name": "Therapieplan",
        "description": "Treatment plan",
        "icon": "💊",
        "is_enabled": True,
        "examples": ["Therapie", "Behandlung"],
        "strong_indicators": ["Therapieplan"],
        "weak_indicators": ["Medikament"],
    }

    response = client.post("/api/pipeline/document-classes", json=new_class)

    assert response.status_code == 201
    data = response.json()
    assert data["class_key"] == "THERAPIEPLAN"
    assert data["is_system_class"] is False


def test_update_document_class(client, mock_auth, seed_test_data):
    """Test PUT /api/pipeline/document-classes/{class_id}"""
    updated_class = {
        "class_key": "ARZTBRIEF",
        "display_name": "Updated Arztbrief",
        "description": "Updated description",
        "icon": "📄",
        "is_enabled": True,
    }

    response = client.put("/api/pipeline/document-classes/1", json=updated_class)

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Updated Arztbrief"


def test_cannot_delete_system_class(client, mock_auth, seed_test_data):
    """Test that system classes cannot be deleted"""
    response = client.delete("/api/pipeline/document-classes/1")

    assert response.status_code == 400
    data = response.json()
    assert "system" in data["error"]["message"].lower()


# ==================== Validation Tests ====================


def test_create_step_missing_required_fields(client, mock_auth, seed_test_data):
    """Test validation error when creating step without required fields"""
    incomplete_step = {"name": "Incomplete Step"}

    response = client.post("/api/pipeline/steps", json=incomplete_step)

    assert response.status_code == 422
    data = response.json()
    assert "validation_errors" in data["error"]["details"]


def test_create_step_invalid_max_tokens(client, mock_auth, seed_test_data):
    """Test validation error for invalid max_tokens"""
    invalid_step = {
        "name": "Invalid Step",
        "order": 1,
        "enabled": True,
        "prompt_template": "Test: {input_text}",
        "selected_model_id": 1,
        "temperature": 0.7,
        "max_tokens": 50,  # Too low (min is 100)
        "retry_on_failure": True,
        "max_retries": 3,
        "input_from_previous_step": True,
    }

    response = client.post("/api/pipeline/steps", json=invalid_step)

    assert response.status_code == 422


def test_create_step_prompt_without_input_text(client, mock_auth, seed_test_data):
    """Test validation error when prompt doesn't contain {input_text}"""
    invalid_step = {
        "name": "Invalid Prompt Step",
        "order": 1,
        "enabled": True,
        "prompt_template": "This prompt is missing the required placeholder",
        "selected_model_id": 1,
        "temperature": 0.7,
        "max_tokens": 1000,
        "retry_on_failure": True,
        "max_retries": 3,
        "input_from_previous_step": True,
    }

    response = client.post("/api/pipeline/steps", json=invalid_step)

    assert response.status_code == 422


# ==================== Authentication Tests ====================


def test_unauthorized_access_without_token(client, seed_test_data):
    """Test that endpoints require authentication"""
    from app.routers.settings_auth import verify_session_token

    # Override dependency to return False (not authenticated)
    def mock_verify_token_false(authorization: str | None = None) -> bool:
        return False

    app.dependency_overrides[verify_session_token] = mock_verify_token_false

    try:
        response = client.get("/api/pipeline/steps")
        assert response.status_code == 401
    finally:
        # Clean up
        if verify_session_token in app.dependency_overrides:
            del app.dependency_overrides[verify_session_token]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
