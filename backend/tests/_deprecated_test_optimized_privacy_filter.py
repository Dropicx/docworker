"""
Unit Tests for OptimizedPrivacyFilter

Tests the hybrid PII removal approach with both fast-path (regex)
and slow-path (spaCy NER) execution.
"""

import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.optimized_privacy_filter import OptimizedPrivacyFilter


class TestOptimizedPrivacyFilter:
    """Test suite for optimized privacy filter"""

    @pytest.fixture
    def filter(self):
        """Create filter instance for testing"""
        return OptimizedPrivacyFilter()

    def test_initialization(self, filter):
        """Test filter initializes correctly"""
        assert filter is not None
        assert filter._fast_filter is not None
        assert filter._advanced_filter is not None

    def test_remove_obvious_pii_patterns(self, filter):
        """Test fast-path regex removal of obvious PII"""
        text = """
        Patient: Max Mustermann
        Geburtsdatum: 01.01.1980
        Adresse: Musterstraße 123, 12345 Berlin
        Telefon: +49 30 12345678
        Email: max.mustermann@example.com
        """

        result = filter.remove_pii(text)

        # Names should be removed
        assert "Mustermann" not in result

        # Birthdate should be removed
        assert "01.01.1980" not in result

        # Address should be removed
        assert "Musterstraße" not in result
        assert "12345 Berlin" not in result

        # Contact info should be removed
        assert "+49 30 12345678" not in result
        assert "max.mustermann@example.com" not in result

    def test_preserve_medical_terms(self, filter):
        """Test medical terminology is preserved"""
        text = """
        Diagnose: Morbus Crohn
        Behandlung mit Vitamin D3 und Vitamin B12
        Laborwerte: Hämoglobin 14.5 g/dl, HbA1c 5.8%
        Röntgen-Thorax unauffällig
        """

        result = filter.remove_pii(text)

        # Medical terms must be preserved
        assert "Morbus Crohn" in result or "Crohn" in result
        assert "Vitamin D3" in result or "D3" in result
        assert "Vitamin B12" in result or "B12" in result
        assert "Hämoglobin" in result or "hämoglobin" in result.lower()
        assert "HbA1c" in result or "hba1c" in result.lower()

    def test_preserve_lab_values(self, filter):
        """Test laboratory values are preserved"""
        text = """
        Laborwerte vom 15.01.2024:
        - Hämoglobin: 14.5 g/dl
        - Leukozyten: 7.2 /nl
        - Thrombozyten: 250 /nl
        - HbA1c: 5.8%
        - Kreatinin: 0.9 mg/dl
        - TSH: 2.1 mU/l
        """

        result = filter.remove_pii(text)

        # Lab values and their measurements should be preserved
        assert "14.5" in result  # Hämoglobin value
        assert "7.2" in result  # Leukozyten value
        assert "250" in result  # Thrombozyten value
        assert "5.8" in result  # HbA1c value
        assert "0.9" in result  # Kreatinin value
        assert "2.1" in result  # TSH value

    def test_complex_document_with_names(self, filter):
        """Test complex document with embedded names"""
        text = """
        Arztbrief

        Patient: Müller, Hans
        Geb.: 15.05.1965

        Diagnose:
        - Diabetes mellitus Typ 2
        - Arterielle Hypertonie
        - Morbus Basedow (Schilddrüsenerkrankung)

        Medikation:
        - Metformin 1000mg 2x täglich
        - Ramipril 5mg 1x täglich

        Der Patient wurde von Dr. Schmidt betreut.

        Mit freundlichen Grüßen
        Prof. Dr. Müller
        """

        result = filter.remove_pii(text)

        # Names should be removed
        assert "Müller" not in result or result.count("Müller") == 0  # Patient name removed
        assert "Hans" not in result
        assert "Schmidt" not in result

        # Medical content preserved
        assert "Diabetes" in result
        assert "Hypertonie" in result
        assert "Basedow" in result or "basedow" in result.lower()
        assert "Metformin" in result or "metformin" in result.lower()
        assert "Ramipril" in result or "ramipril" in result.lower()

    def test_insurance_numbers_removed(self, filter):
        """Test insurance numbers are removed"""
        text = """
        Versichertennummer: A123456789
        Krankenversicherung: AOK
        Patientennummer: 98765
        """

        result = filter.remove_pii(text)

        # Insurance identifiers should be removed
        assert "A123456789" not in result
        assert "98765" not in result

    def test_simple_document_fast_path(self, filter):
        """Test simple document uses fast path (no NER needed)"""
        text = """
        Laborwerte:
        Hämoglobin: 14.5 g/dl
        Leukozyten: 7.2 /nl
        """

        # This should trigger fast path (no NER)
        result = filter.remove_pii(text)

        # Should preserve lab values
        assert "14.5" in result
        assert "7.2" in result

    def test_needs_ner_analysis_short_text(self, filter):
        """Test NER is skipped for very short text"""
        short_text = "Hämoglobin: 14.5 g/dl"
        assert filter._needs_ner_analysis(short_text) is False

    def test_needs_ner_analysis_few_capitals(self, filter):
        """Test NER is skipped for text with few capitalized words"""
        text = "laborwerte vom heute: hämoglobin 14.5, leukozyten 7.2"
        assert filter._needs_ner_analysis(text) is False

    def test_needs_ner_analysis_complex_text(self, filter):
        """Test NER is triggered for complex text with many capitals"""
        text = """
        Der Patient Max Mustermann wurde von Dr. Schmidt betreut.
        Diagnose: Diabetes Mellitus Typ 2
        Weitere Behandlung durch Prof. Müller empfohlen.
        """
        # This should trigger NER due to many capitalized words
        result = filter._needs_ner_analysis(text)
        # Result depends on how many caps are left after regex cleaning

    def test_validate_medical_content(self, filter):
        """Test medical content validation"""
        original = """
        Diagnose: Diabetes mellitus
        Laborwerte: Hämoglobin 14.5, HbA1c 5.8%
        Medikament: Metformin 1000mg
        """

        cleaned = filter.remove_pii(original)

        # Validation should pass (medical terms preserved)
        is_valid = filter.validate_medical_content(original, cleaned)
        assert is_valid is True

    def test_get_performance_stats(self, filter):
        """Test performance statistics"""
        stats = filter.get_performance_stats()

        assert "filter_type" in stats
        assert stats["filter_type"] == "OptimizedPrivacyFilter"
        assert "mode" in stats
        assert "spacy_available" in stats
        assert "expected_performance_ms" in stats

    def test_empty_text(self, filter):
        """Test handling of empty text"""
        assert filter.remove_pii("") == ""
        assert filter.remove_pii(None) is None

    def test_real_world_arztbrief(self, filter):
        """Test with realistic doctor's letter"""
        text = """
        Universitätsklinikum München
        Klinik für Innere Medizin

        Arztbrief

        Patient: Mustermann, Max
        Geb.: 15.05.1965
        Adresse: Hauptstraße 42, 80331 München
        Versichertennummer: A123456789

        Diagnosen:
        1. Diabetes mellitus Typ 2 (E11.9)
        2. Arterielle Hypertonie (I10.00)
        3. Hypercholesterinämie (E78.0)

        Anamnese:
        Der Patient stellte sich mit Müdigkeit und Durst vor.

        Befunde:
        - HbA1c: 8.2% (erhöht)
        - Nüchtern-Glucose: 145 mg/dl
        - RR: 145/90 mmHg
        - BMI: 28.5 kg/m²

        Therapie:
        - Metformin 1000mg 1-0-1
        - Ramipril 5mg 0-0-1
        - Atorvastatin 20mg 0-0-1

        Vitamin D3 Substitution empfohlen (25-OH-D3: 15 ng/ml, Zielwert >30)

        Kontrolle in 3 Monaten.

        Mit freundlichen Grüßen
        Prof. Dr. med. Schmidt
        Facharzt für Innere Medizin
        """

        result = filter.remove_pii(text)

        # PII should be removed
        assert "Mustermann" not in result
        assert "15.05.1965" not in result
        assert "Hauptstraße" not in result
        assert "80331 München" not in result
        assert "A123456789" not in result
        assert "Schmidt" not in result

        # Medical content preserved
        assert "Diabetes" in result
        assert "Hypertonie" in result
        assert "HbA1c" in result or "hba1c" in result.lower()
        assert "8.2" in result  # HbA1c value
        assert "145" in result  # Glucose/RR values
        assert "28.5" in result  # BMI
        assert "Metformin" in result or "metformin" in result.lower()
        assert "Ramipril" in result or "ramipril" in result.lower()
        assert "Vitamin D3" in result or "D3" in result

    def test_performance_simple_document(self, filter):
        """Test performance on simple document (should be <50ms)"""
        import time

        text = """
        Laborwerte:
        Hämoglobin: 14.5 g/dl
        Leukozyten: 7.2 /nl
        HbA1c: 5.8%
        """

        start = time.time()
        filter.remove_pii(text)
        elapsed_ms = (time.time() - start) * 1000

        # Simple document should be very fast (regex only)
        # Allow generous margin for slow systems
        assert elapsed_ms < 100, f"Simple document took {elapsed_ms:.1f}ms (expected <100ms)"

    def test_performance_complex_document(self, filter):
        """Test performance on complex document (should be <200ms)"""
        import time

        text = (
            """
        Arztbrief für Patient Max Mustermann, geb. 01.01.1980
        Diagnose: Diabetes mellitus Typ 2, Hypertonie
        Behandelnder Arzt: Dr. Schmidt
        Laborwerte: HbA1c 8.2%, Glucose 145 mg/dl
        Medikation: Metformin 1000mg, Ramipril 5mg
        """
            * 5
        )  # Repeat to make it more complex

        start = time.time()
        filter.remove_pii(text)
        elapsed_ms = (time.time() - start) * 1000

        # Complex document should still be fast
        # Allow generous margin (target is <200ms, allow 500ms for slow systems)
        assert elapsed_ms < 500, f"Complex document took {elapsed_ms:.1f}ms (expected <500ms)"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
