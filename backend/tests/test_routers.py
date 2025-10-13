"""
Router/API Tests for DocTranslator

Tests FastAPI router endpoints using TestClient.
Mocks database and external services for fast,  isolated testing.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.database.modular_pipeline_models import StepExecutionStatus, PipelineJobDB


@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return Mock()


class TestHealthEndpoint:
    """Test suite for health check endpoint"""

    def test_health_check(self, client):
        """Test health endpoint returns 200"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestUploadEndpoints:
    """Test suite for upload router endpoints"""

    def test_upload_limits_endpoint(self, client):
        """Test getting upload limits"""
        response = client.get("/api/upload/limits")

        assert response.status_code == 200
        data = response.json()

        assert "max_file_size_mb" in data
        assert "allowed_formats" in data
        assert "rate_limit" in data
        assert data["max_file_size_mb"] == 50
        assert "PDF" in data["allowed_formats"]

    def test_upload_health_endpoint(self, client):
        """Test upload health check"""
        response = client.get("/api/upload/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "active_uploads" in data
        assert "memory_usage" in data

    @patch('app.routers.upload.FileValidator')
    @patch('app.routers.upload.check_workers_available')
    @patch('app.routers.upload.ModularPipelineExecutor')
    def test_upload_document_success(self, mock_executor, mock_workers, mock_validator, client):
        """Test successful document upload"""
        # Mock file validation
        mock_validator.validate_file = AsyncMock(return_value=(True, None))
        mock_validator.get_file_type = Mock(return_value="pdf")

        # Mock worker check
        mock_workers.return_value = {"available": True, "worker_count": 1}

        # Mock executor
        mock_executor_instance = Mock()
        mock_executor_instance.load_pipeline_steps.return_value = []
        mock_executor_instance.load_ocr_configuration.return_value = None
        mock_executor.return_value = mock_executor_instance

        # Create test file
        file_content = b"%PDF-1.4\nTest PDF"
        files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}

        with patch('app.routers.upload.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_session.refresh = Mock()
            mock_get_session.return_value = iter([mock_session])

            response = client.post("/api/upload", files=files)

            assert response.status_code == 200
            data = response.json()

            assert "processing_id" in data
            assert "filename" in data
            assert data["filename"] == "test.pdf"
            assert data["status"] == "PENDING"

    @patch('app.routers.upload.FileValidator')
    def test_upload_document_invalid_file(self, mock_validator, client):
        """Test upload with invalid file"""
        # Mock file validation to fail
        mock_validator.validate_file = AsyncMock(return_value=(False, "Invalid file type"))

        files = {"file": ("test.txt", BytesIO(b"text content"), "text/plain")}

        response = client.post("/api/upload", files=files)

        assert response.status_code == 400
        assert "Dateivalidierung fehlgeschlagen" in response.json()["detail"]


class TestProcessEndpoints:
    """Test suite for process router endpoints"""

    def test_get_available_models(self, client):
        """Test getting available AI models"""
        response = client.get("/api/process/models")

        assert response.status_code == 200
        data = response.json()

        assert "connected" in data
        assert "models" in data
        assert isinstance(data["models"], list)
        assert "api_mode" in data
        assert data["api_mode"] == "OVH AI Endpoints"

    def test_get_available_languages(self, client):
        """Test getting available translation languages"""
        response = client.get("/api/process/languages")

        assert response.status_code == 200
        data = response.json()

        assert "languages" in data
        assert "total_count" in data
        assert isinstance(data["languages"], list)
        assert len(data["languages"]) > 0

        # Check language structure
        first_lang = data["languages"][0]
        assert "code" in first_lang
        assert "name" in first_lang
        assert "quality" in first_lang

    @patch('app.routers.process.get_session')
    @patch('app.routers.process.enqueue_document_processing')
    def test_start_processing(self, mock_enqueue, mock_get_session, client):
        """Test starting document processing"""
        # Mock database session
        mock_session = Mock()
        mock_job = Mock(spec=PipelineJobDB)
        mock_job.processing_id = "test-123"
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        mock_get_session.return_value = iter([mock_session])

        # Mock enqueueing
        mock_enqueue.return_value = "task-id-123"

        processing_id = "test-123"
        request_data = {"target_language": "EN"}

        response = client.post(
            f"/api/process/{processing_id}",
            json=request_data
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "processing_id" in data
        assert "task_id" in data
        assert data["task_id"] == "task-id-123"

    @patch('app.routers.process.get_session')
    def test_start_processing_not_found(self, mock_get_session, client):
        """Test starting processing for non-existent job"""
        # Mock database session returning None
        mock_session = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value = iter([mock_session])

        processing_id = "non-existent"

        response = client.post(f"/api/process/{processing_id}")

        assert response.status_code == 404
        assert "nicht gefunden" in response.json()["detail"]

    @patch('app.routers.process.get_session')
    def test_get_processing_status(self, mock_get_session, client):
        """Test getting processing status"""
        # Mock database session
        mock_session = Mock()
        mock_job = Mock(spec=PipelineJobDB)
        mock_job.processing_id = "test-123"
        mock_job.status = StepExecutionStatus.RUNNING
        mock_job.progress_percent = 50
        mock_job.error_message = None
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        mock_get_session.return_value = iter([mock_session])

        processing_id = "test-123"

        response = client.get(f"/api/process/{processing_id}/status")

        assert response.status_code == 200
        data = response.json()

        assert "processing_id" in data
        assert "status" in data
        assert "progress_percent" in data
        assert data["progress_percent"] == 50

    @patch('app.routers.process.get_session')
    def test_get_processing_result(self, mock_get_session, client):
        """Test getting processing result"""
        # Mock database session
        mock_session = Mock()
        mock_job = Mock(spec=PipelineJobDB)
        mock_job.processing_id = "test-123"
        mock_job.status = StepExecutionStatus.COMPLETED
        mock_job.result_data = {
            "processing_id": "test-123",
            "translated_text": "Translated content",
            "document_type": "ARZTBRIEF"
        }
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        mock_get_session.return_value = iter([mock_session])

        processing_id = "test-123"

        response = client.get(f"/api/process/{processing_id}/result")

        assert response.status_code == 200
        data = response.json()

        assert "translated_text" in data
        assert data["translated_text"] == "Translated content"

    @patch('app.routers.process.get_session')
    def test_get_processing_result_not_completed(self, mock_get_session, client):
        """Test getting result for incomplete processing"""
        # Mock database session
        mock_session = Mock()
        mock_job = Mock(spec=PipelineJobDB)
        mock_job.status = StepExecutionStatus.RUNNING
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_job
        mock_get_session.return_value = iter([mock_session])

        processing_id = "test-123"

        response = client.get(f"/api/process/{processing_id}/result")

        assert response.status_code == 409  # Conflict
        assert "nicht abgeschlossen" in response.json()["detail"]

    def test_get_active_processes(self, client):
        """Test getting active processes"""
        response = client.get("/api/process/active")

        assert response.status_code == 200
        data = response.json()

        assert "active_count" in data
        assert "processes" in data
        assert isinstance(data["processes"], list)

    def test_clear_pipeline_cache(self, client):
        """Test clearing pipeline cache"""
        response = client.post("/api/process/clear-cache")

        assert response.status_code == 200
        data = response.json()

        assert "success" in data or "message" in data

    def test_get_performance_comparison(self, client):
        """Test getting performance comparison"""
        response = client.get("/api/process/performance-comparison")

        assert response.status_code == 200
        data = response.json()

        assert "optimized_pipeline" in data
        assert "legacy_pipeline" in data
        assert "recommendation" in data


class TestRateLimiting:
    """Test suite for rate limiting"""

    def test_upload_rate_limit(self, client):
        """Test that upload endpoint has rate limiting"""
        # Note: Rate limiting may not work in test mode without Redis
        # This test just verifies the endpoint exists and returns reasonable response
        files = {"file": ("test.pdf", BytesIO(b"content"), "application/pdf")}

        # First request should work (or fail for other reasons, but not rate limit)
        response = client.post("/api/upload", files=files)

        # Should get a response (even if 400/500, not 429 on first try)
        assert response.status_code != 429  # Not rate limited on first request


class TestErrorHandling:
    """Test suite for error handling"""

    def test_404_endpoint(self, client):
        """Test non-existent endpoint returns 404"""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404

    @patch('app.routers.process.get_session')
    def test_database_error_handling(self, mock_get_session, client):
        """Test that database errors are handled gracefully"""
        # Mock database to raise exception
        mock_session = Mock()
        mock_session.query.side_effect = Exception("Database connection failed")
        mock_get_session.return_value = iter([mock_session])

        response = client.get("/api/process/test-123/status")

        # Should return 500 or similar error, not crash
        assert response.status_code >= 400


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v"])
