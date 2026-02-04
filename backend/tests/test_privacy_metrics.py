"""
Tests for Privacy Filter Metrics API (Issue #35 Phase 6.3)

Tests the /api/privacy/* endpoints for monitoring and metrics.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Mock worker responses for CI (no Celery worker available)
MOCK_WORKER_STATUS = {
    "filter_capabilities": {
        "has_ner": True,
        "spacy_model": "de_core_news_lg",
        "removal_method": "AdvancedPrivacyFilter_Phase5",
        "custom_terms_loaded": True,
    },
    "detection_stats": {
        "pii_types_supported": [
            "birthdate",
            "patient_name",
            "street_address",
            "phone_number",
            "email_address",
            "tax_id",
            "patient_id",
            "insurance_number",
            "iban",
            "date_general",
            "zip_city",
            "doctor_name",
            "clinic_name",
            "age_reference",
            "relative_reference",
            "nationality",
            "religion",
        ],
        "pii_types_count": 17,
        "medical_terms_count": 350,
        "drug_database_count": 120,
        "abbreviations_count": 210,
        "loinc_codes_count": 60,
        "eponyms_count": 55,
    },
}


def _mock_test_privacy_filter(text, timeout=30):
    """Mock privacy filter test for CI."""
    return {
        "input_length": len(text),
        "output_length": max(1, len(text) - 20),
        "cleaned_text": "[NAME ENTFERNT] test result",
        "processing_time_ms": 15.5,
        "pii_types_detected": ["patient_name", "birthdate", "street_address", "phone_number"],
        "entities_detected": 4,
        "quality_score": 85.0,
        "review_recommended": False,
        "passes_performance_target": True,
    }


@pytest.fixture(autouse=True)
def mock_celery_workers():
    """Mock Celery worker calls for all privacy metrics tests."""
    with (
        patch(
            "app.routers.privacy_metrics.get_privacy_filter_status_via_worker",
            return_value=MOCK_WORKER_STATUS,
        ),
        patch(
            "app.routers.privacy_metrics.test_privacy_filter_via_worker",
            side_effect=_mock_test_privacy_filter,
        ),
    ):
        yield


class TestPrivacyMetricsEndpoints:
    """Test privacy metrics API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app

        return TestClient(app)

    def test_get_metrics(self, client):
        """Test GET /api/privacy/metrics returns expected structure."""
        response = client.get("/api/privacy/metrics")

        assert response.status_code == 200
        data = response.json()

        # Check top-level structure
        assert "timestamp" in data
        assert "filter_capabilities" in data
        assert "detection_stats" in data
        assert "performance_target_ms" in data

        # Check filter capabilities
        caps = data["filter_capabilities"]
        assert "has_ner" in caps
        assert "spacy_model" in caps
        assert "removal_method" in caps
        assert isinstance(caps["has_ner"], bool)

        # Check detection stats
        stats = data["detection_stats"]
        assert "pii_types_supported" in stats
        assert "pii_types_count" in stats
        assert "medical_terms_count" in stats
        assert "drug_database_count" in stats
        assert stats["pii_types_count"] >= 17
        assert stats["medical_terms_count"] >= 300
        assert stats["drug_database_count"] >= 100

    def test_get_pii_types(self, client):
        """Test GET /api/privacy/pii-types returns all PII types."""
        response = client.get("/api/privacy/pii-types")

        assert response.status_code == 200
        data = response.json()

        assert "pii_types" in data
        assert "total_count" in data
        assert data["total_count"] >= 17

        # Check structure of each PII type
        for pii_type in data["pii_types"]:
            assert "type" in pii_type
            assert "description" in pii_type
            assert "marker" in pii_type

    def test_privacy_health(self, client):
        """Test GET /api/privacy/health returns health status."""
        response = client.get("/api/privacy/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "filter_ready" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"
        assert data["filter_ready"] is True

    def test_live_test_basic(self, client):
        """Test POST /api/privacy/test with basic text."""
        response = client.post(
            "/api/privacy/test", json={"text": "Patient: Müller, Hans\nGeb.: 15.05.1965"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "input_length" in data
        assert "output_length" in data
        assert "processing_time_ms" in data
        assert "pii_types_detected" in data
        assert "quality_score" in data
        assert "review_recommended" in data
        assert "passes_performance_target" in data

        # Verify PII was detected
        assert len(data["pii_types_detected"]) > 0
        assert "birthdate" in data["pii_types_detected"]

        # Verify performance
        assert data["processing_time_ms"] > 0
        assert isinstance(data["quality_score"], (int, float))

    def test_live_test_empty_text(self, client):
        """Test POST /api/privacy/test with empty text."""
        response = client.post("/api/privacy/test", json={"text": ""})

        assert response.status_code == 400

    def test_live_test_medical_preservation(self, client):
        """Test that medical content is preserved in live test."""
        response = client.post(
            "/api/privacy/test",
            json={"text": "Diagnose: Diabetes mellitus Typ 2 (E11.9)\nTherapie: Metformin 1000mg"},
        )

        assert response.status_code == 200
        data = response.json()

        # Should have minimal PII detected (no patient info)
        assert data["input_length"] > 0
        assert data["output_length"] > 0
        # Medical content preserved, so output should be similar length
        assert data["output_length"] >= data["input_length"] * 0.9

    def test_live_test_performance_target(self, client):
        """Test that processing time is reasonable."""
        response = client.post(
            "/api/privacy/test",
            json={"text": "Patient: Test Person, Geb.: 01.01.1980, Diagnose: Diabetes"},
        )

        assert response.status_code == 200
        data = response.json()

        # Short text should process quickly
        assert data["processing_time_ms"] < 200  # Allow some margin


class TestPrivacyMetricsDataQuality:
    """Test data quality of metrics responses."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app

        return TestClient(app)

    def test_metrics_pii_types_complete(self, client):
        """Verify all expected PII types are listed."""
        response = client.get("/api/privacy/pii-types")
        data = response.json()

        expected_types = [
            "birthdate",
            "patient_name",
            "street_address",
            "phone_number",
            "email_address",
            "tax_id",
            "patient_id",
        ]

        actual_types = [t["type"] for t in data["pii_types"]]
        for expected in expected_types:
            assert expected in actual_types, f"Missing PII type: {expected}"

    def test_metrics_counts_reasonable(self, client):
        """Verify metrics counts are within expected ranges."""
        response = client.get("/api/privacy/metrics")
        data = response.json()
        stats = data["detection_stats"]

        # These are minimum counts based on Phase 4 implementation
        assert stats["medical_terms_count"] >= 300
        assert stats["drug_database_count"] >= 100
        assert stats["abbreviations_count"] >= 200
        assert stats["loinc_codes_count"] >= 50
        assert stats["eponyms_count"] >= 50


class TestPrivacyFilterIntegration:
    """Integration tests for privacy filter via API."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from app.main import app

        return TestClient(app)

    def test_full_document_processing(self, client):
        """Test processing a full medical document."""
        document = """
        Universitätsklinikum München
        Arztbrief

        Patient: Mustermann, Max
        Geb.: 22.03.1958
        Adresse: Hauptstraße 42, 80331 München
        Tel: +49 89 12345678

        Diagnosen:
        1. Diabetes mellitus Typ 2 (E11.9)
        2. Arterielle Hypertonie (I10)

        Medikation:
        - Metformin 1000mg 1-0-1
        - Ramipril 5mg 0-0-1

        Laborwerte:
        - HbA1c: 7.2%
        - Kreatinin: 1.1 mg/dl

        Mit freundlichen Grüßen
        Dr. med. Weber
        """

        response = client.post("/api/privacy/test", json={"text": document})

        assert response.status_code == 200
        data = response.json()

        # Should detect multiple PII types
        assert len(data["pii_types_detected"]) >= 3

        # Should preserve medical content (output not drastically shorter)
        assert data["output_length"] > data["input_length"] * 0.5

        # Quality score should be reasonable
        assert data["quality_score"] >= 50

    def test_text_too_long_rejected(self, client):
        """Test that very long text is rejected."""
        long_text = "A" * 60000  # Over 50000 char limit

        response = client.post("/api/privacy/test", json={"text": long_text})

        assert response.status_code == 400
        assert "too long" in response.json()["detail"].lower()
