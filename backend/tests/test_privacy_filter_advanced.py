"""
Unit Tests for AdvancedPrivacyFilter

Tests GDPR-compliant PII removal while preserving medical content.
Verifies that the consolidated privacy filter maintains all functionality.
"""

import pytest
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.privacy_filter_advanced import AdvancedPrivacyFilter


class TestAdvancedPrivacyFilter:
    """Test suite for AdvancedPrivacyFilter"""

    @pytest.fixture
    def filter(self):
        """Create filter instance for testing"""
        return AdvancedPrivacyFilter()

    def test_initialization(self, filter):
        """Test filter initializes correctly"""
        assert filter is not None
        assert filter.medical_terms is not None
        assert filter.protected_abbreviations is not None
        assert filter.patterns is not None
        assert len(filter.medical_terms) >= 140  # Should have 146+ terms
        assert len(filter.protected_abbreviations) >= 200  # Should have 210+ abbreviations

    def test_remove_patient_names(self, filter):
        """Test removal of patient names"""
        text = """
        Patient: Müller, Hans
        Geburtsdatum: 15.05.1965
        """
        result = filter.remove_pii(text)

        assert "Müller" not in result
        assert "Hans" not in result
        assert "15.05.1965" not in result

    def test_remove_birthdates(self, filter):
        """Test removal of birthdates"""
        text = "Patient geb. 01.01.1980 wurde untersucht"
        result = filter.remove_pii(text)

        assert "01.01.1980" not in result
        assert "untersucht" in result

    def test_remove_addresses(self, filter):
        """Test removal of street addresses and PLZ"""
        text = """
        Musterstraße 123, 12345 Berlin
        Hauptstraße 42
        """
        result = filter.remove_pii(text)

        assert "Musterstraße" not in result
        assert "12345 Berlin" not in result or "PLZ/ORT ENTFERNT" in result
        assert "Hauptstraße" not in result

    def test_remove_contact_information(self, filter):
        """Test removal of phone and email"""
        text = """
        Telefon: +49 30 12345678
        Email: patient@example.com
        """
        result = filter.remove_pii(text)

        assert "+49 30 12345678" not in result
        assert "patient@example.com" not in result

    def test_remove_insurance_numbers(self, filter):
        """Test removal of insurance identifiers"""
        text = """
        Versichertennummer: A123456789
        Patientennummer: 98765
        """
        result = filter.remove_pii(text)

        assert "A123456789" not in result
        assert "98765" not in result

    def test_preserve_medical_terms(self, filter):
        """Test that medical terminology is preserved"""
        text = """
        Diagnose: Diabetes mellitus Typ 2
        Behandlung mit Metformin 1000mg
        Laborwerte: Hämoglobin 14.5 g/dl
        """
        result = filter.remove_pii(text)

        # Medical terms must be preserved
        assert "Diabetes" in result or "diabetes" in result.lower()
        assert "Metformin" in result or "metformin" in result.lower()
        assert "Hämoglobin" in result or "hämoglobin" in result.lower()
        assert "14.5" in result  # Lab value

    def test_preserve_medical_abbreviations(self, filter):
        """Test preservation of medical abbreviations"""
        text = """
        HbA1c: 8.2%
        TSH: 2.1 mU/l
        CRP: 5 mg/l
        eGFR: 90 ml/min
        """
        result = filter.remove_pii(text)

        # All abbreviations should be preserved
        assert "HbA1c" in result or "hba1c" in result.lower()
        assert "TSH" in result or "tsh" in result.lower()
        assert "CRP" in result or "crp" in result.lower()
        assert "eGFR" in result or "egfr" in result.lower()
        # Values should be preserved
        assert "8.2" in result
        assert "2.1" in result
        assert "90" in result

    def test_preserve_lab_values(self, filter):
        """Test preservation of laboratory values and measurements"""
        text = """
        Laborwerte vom 15.01.2024:
        - Hämoglobin: 14.5 g/dl
        - Leukozyten: 7.2 /nl
        - Thrombozyten: 250 /nl
        - Glucose: 95 mg/dl
        """
        result = filter.remove_pii(text)

        # Lab values must be preserved
        assert "14.5" in result
        assert "7.2" in result
        assert "250" in result
        assert "95" in result

    def test_preserve_vitamin_d3(self, filter):
        """Test preservation of Vitamin D3 and similar vitamins"""
        text = """
        Vitamin D3: 25 ng/ml (Mangel)
        Vitamin B12: 350 pg/ml
        25-OH-D3: 15 ng/ml
        """
        result = filter.remove_pii(text)

        # Vitamin names should be preserved
        assert "Vitamin D3" in result or "D3" in result
        assert "Vitamin B12" in result or "B12" in result
        assert "25" in result  # Value
        assert "350" in result  # Value

    def test_complex_medical_document(self, filter):
        """Test with realistic doctor's letter"""
        text = """
        Universitätsklinikum München

        Arztbrief

        Patient: Mustermann, Max
        Geb.: 15.05.1965
        Adresse: Hauptstraße 42, 80331 München

        Diagnosen:
        1. Diabetes mellitus Typ 2 (E11.9)
        2. Arterielle Hypertonie (I10.00)

        Befunde:
        - HbA1c: 8.2% (erhöht)
        - Nüchtern-Glucose: 145 mg/dl
        - RR: 145/90 mmHg
        - BMI: 28.5 kg/m²

        Therapie:
        - Metformin 1000mg 1-0-1
        - Ramipril 5mg 0-0-1

        Mit freundlichen Grüßen
        Dr. med. Schmidt
        """
        result = filter.remove_pii(text)

        # PII should be removed
        assert "Mustermann" not in result
        assert "15.05.1965" not in result
        assert "Hauptstraße" not in result
        assert "80331" not in result or "PLZ/ORT ENTFERNT" in result
        assert "Schmidt" not in result

        # Medical content preserved
        assert "Diabetes" in result
        assert "Hypertonie" in result
        assert "HbA1c" in result or "hba1c" in result.lower()
        assert "8.2" in result
        assert "145" in result  # Glucose/RR value
        assert "28.5" in result  # BMI
        assert "Metformin" in result or "metformin" in result.lower()
        assert "Ramipril" in result or "ramipril" in result.lower()

    def test_validate_medical_content_preservation(self, filter):
        """Test medical content validation method"""
        original = """
        Patient: Test Patient
        Diagnose: Diabetes mellitus
        Laborwerte: Hämoglobin 14.5 g/dl, HbA1c 5.8%
        Medikament: Metformin 1000mg
        """
        cleaned = filter.remove_pii(original)

        # Validation should pass (medical terms preserved)
        is_valid = filter.validate_medical_content(original, cleaned)
        assert is_valid is True, "Medical content validation failed"

    def test_empty_text_handling(self, filter):
        """Test handling of empty or None text"""
        assert filter.remove_pii("") == ""
        assert filter.remove_pii(None) is None

    def test_text_without_pii(self, filter):
        """Test text that has no PII (should be mostly unchanged)"""
        text = """
        Laborwerte:
        Hämoglobin: 14.5 g/dl
        Leukozyten: 7.2 /nl
        Glucose: 95 mg/dl
        """
        result = filter.remove_pii(text)

        # Should contain all original content
        assert "Hämoglobin" in result or "hämoglobin" in result.lower()
        assert "14.5" in result
        assert "7.2" in result
        assert "95" in result

    def test_gdpr_compliance_markers(self, filter):
        """Test that PII is replaced with GDPR-compliant markers"""
        text = """
        Patient: Müller, Hans
        Geb.: 01.01.1980
        Tel: +49 30 12345678
        """
        result = filter.remove_pii(text)

        # Should have replacement markers
        assert "[NAME ENTFERNT]" in result or "NAME ENTFERNT" in result.upper()
        assert "[GEBURTSDATUM ENTFERNT]" in result or "GEBURTSDATUM ENTFERNT" in result.upper()
        assert "[TELEFON ENTFERNT]" in result or "TELEFON ENTFERNT" in result.upper()

    def test_spacy_availability(self, filter):
        """Test that filter works with or without spaCy"""
        # Filter should work regardless of spaCy availability
        text = "Patient: Max Mustermann"
        result = filter.remove_pii(text)
        assert "Mustermann" not in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
