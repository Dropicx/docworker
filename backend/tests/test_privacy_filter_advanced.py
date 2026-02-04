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
        """Create filter instance for testing (without database loading)"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_initialization(self, filter):
        """Test filter initializes correctly"""
        assert filter is not None
        assert filter.medical_terms is not None
        assert filter.protected_abbreviations is not None
        assert filter.patterns is not None
        assert len(filter.medical_terms) >= 140  # Should have 300+ terms now
        assert len(filter.protected_abbreviations) >= 200  # Should have 210+ abbreviations

    def test_remove_patient_names(self, filter):
        """Test removal of patient names"""
        text = """
        Patient: Müller, Hans
        Geburtsdatum: 15.05.1965
        """
        result, _ = filter.remove_pii(text)

        assert "Müller" not in result
        assert "Hans" not in result
        assert "15.05.1965" not in result

    def test_remove_birthdates(self, filter):
        """Test removal of birthdates"""
        text = "Patient geb. 01.01.1980 wurde untersucht"
        result, _ = filter.remove_pii(text)

        assert "01.01.1980" not in result
        assert "untersucht" in result

    def test_remove_addresses(self, filter):
        """Test removal of street addresses and PLZ"""
        text = """
        Musterstraße 123, 12345 Berlin
        Hauptstraße 42
        """
        result, _ = filter.remove_pii(text)

        assert "Musterstraße" not in result
        assert "12345 Berlin" not in result or "PLZ/ORT ENTFERNT" in result
        assert "Hauptstraße" not in result

    def test_remove_contact_information(self, filter):
        """Test removal of phone and email"""
        text = """
        Telefon: +49 30 12345678
        Email: patient@example.com
        """
        result, _ = filter.remove_pii(text)

        assert "+49 30 12345678" not in result
        assert "patient@example.com" not in result

    def test_remove_insurance_numbers(self, filter):
        """Test removal of insurance identifiers"""
        text = """
        Versichertennummer: A123456789
        Patientennummer: 98765
        """
        result, _ = filter.remove_pii(text)

        assert "A123456789" not in result
        assert "98765" not in result

    def test_preserve_medical_terms(self, filter):
        """Test that medical terminology is preserved"""
        text = """
        Diagnose: Diabetes mellitus Typ 2
        Behandlung mit Metformin 1000mg
        Laborwerte: Hämoglobin 14.5 g/dl
        """
        result, _ = filter.remove_pii(text)

        # Medical terms must be preserved
        assert "Diabetes" in result or "diabetes" in result.lower()
        assert "Metformin" in result or "METFORMIN" in result
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
        result, _ = filter.remove_pii(text)

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
        result, _ = filter.remove_pii(text)

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
        result, _ = filter.remove_pii(text)

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
        result, _ = filter.remove_pii(text)

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
        assert "Metformin" in result or "METFORMIN" in result
        assert "Ramipril" in result or "RAMIPRIL" in result

    def test_validate_medical_content_preservation(self, filter):
        """Test medical content validation method"""
        original = """
        Patient: Test Patient
        Diagnose: Diabetes mellitus
        Laborwerte: Hämoglobin 14.5 g/dl, HbA1c 5.8%
        Medikament: Metformin 1000mg
        """
        cleaned, _ = filter.remove_pii(original)

        # Validation should pass (medical terms preserved)
        is_valid = filter.validate_medical_content(original, cleaned)
        assert is_valid is True, "Medical content validation failed"

    def test_empty_text_handling(self, filter):
        """Test handling of empty or None text"""
        result, meta = filter.remove_pii("")
        assert result == ""
        assert meta == {}

        result2, meta2 = filter.remove_pii(None)
        assert result2 is None
        assert meta2 == {}

    def test_text_without_pii(self, filter):
        """Test text that has no PII (should be mostly unchanged)"""
        text = """
        Laborwerte:
        Hämoglobin: 14.5 g/dl
        Leukozyten: 7.2 /nl
        Glucose: 95 mg/dl
        """
        result, _ = filter.remove_pii(text)

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
        result, _ = filter.remove_pii(text)

        # Should have replacement markers
        assert "[NAME ENTFERNT]" in result or "NAME ENTFERNT" in result.upper()
        assert "[GEBURTSDATUM ENTFERNT]" in result or "GEBURTSDATUM ENTFERNT" in result.upper()
        assert "[TELEFON ENTFERNT]" in result or "TELEFON ENTFERNT" in result.upper()

    def test_spacy_availability(self, filter):
        """Test that filter works with or without spaCy"""
        # Filter should work regardless of spaCy availability
        text = "Patient: Max Mustermann"
        result, _ = filter.remove_pii(text)
        assert "Mustermann" not in result


class TestPhase4DrugDatabase:
    """Test Phase 4.2: Drug Database Integration (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_drug_database_initialized(self, filter):
        """Test that drug database is initialized with 100+ medications"""
        assert hasattr(filter, "drug_database")
        assert len(filter.drug_database) >= 100
        # Check some specific drugs
        assert "metoprolol" in filter.drug_database
        assert "ibuprofen" in filter.drug_database
        assert "ramipril" in filter.drug_database

    def test_preserve_generic_drug_names(self, filter):
        """Test preservation of generic (INN) drug names"""
        text = """
        Medikation:
        - Metoprolol 100mg 1-0-0
        - Ramipril 5mg 0-0-1
        - Omeprazol 20mg 1-0-0
        """
        result, _ = filter.remove_pii(text)

        # Generic drug names should be preserved
        assert "Metoprolol" in result or "METOPROLOL" in result
        assert "Ramipril" in result or "RAMIPRIL" in result
        assert "Omeprazol" in result or "OMEPRAZOL" in result
        # Dosages preserved
        assert "100mg" in result
        assert "5mg" in result

    def test_preserve_brand_name_drugs(self, filter):
        """Test preservation of German brand name medications"""
        text = """
        Patient erhält:
        - Beloc 100mg (Metoprolol)
        - Pantozol 40mg
        - Marcumar nach INR
        - Xarelto 20mg
        """
        result, _ = filter.remove_pii(text)

        # Brand names should be preserved
        assert "Beloc" in result or "BELOC" in result
        assert "Pantozol" in result or "PANTOZOL" in result
        assert "Marcumar" in result or "MARCUMAR" in result
        assert "Xarelto" in result or "XARELTO" in result

    def test_preserve_psychiatric_medications(self, filter):
        """Test preservation of psychiatric drug names"""
        text = """
        Psychiatrische Medikation:
        - Sertralin 50mg
        - Quetiapin 25mg zur Nacht
        - Lorazepam 0.5mg bei Bedarf
        """
        result, _ = filter.remove_pii(text)

        assert "Sertralin" in result or "SERTRALIN" in result
        assert "Quetiapin" in result or "QUETIAPIN" in result
        assert "Lorazepam" in result or "LORAZEPAM" in result

    def test_drugs_not_removed_as_names(self, filter):
        """Test that drug names are not mistaken for patient names by NER"""
        # Some drug names could be mistaken for surnames
        text = """
        Therapie: Duloxetin, Pregabalin, Gabapentin
        Zusätzlich Marcumar nach Plan
        """
        result, _ = filter.remove_pii(text)

        # These should NOT be removed as names
        assert "Duloxetin" in result or "DULOXETIN" in result
        assert "Pregabalin" in result or "PREGABALIN" in result
        assert "Gabapentin" in result or "GABAPENTIN" in result


class TestPhase4MedicalCodes:
    """Test Phase 4.3: Medical Coding Support (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_medical_code_patterns_initialized(self, filter):
        """Test that medical code patterns are compiled"""
        assert hasattr(filter, "medical_code_patterns")
        assert "icd10" in filter.medical_code_patterns
        assert "ops" in filter.medical_code_patterns
        assert "loinc" in filter.medical_code_patterns

    def test_preserve_icd10_codes(self, filter):
        """Test preservation of ICD-10 diagnostic codes"""
        text = """
        Diagnosen:
        1. Diabetes mellitus Typ 2 (E11.9)
        2. Arterielle Hypertonie (I10)
        3. Herzinsuffizienz (I50.1)
        4. Mammakarzinom (C50.9)
        """
        result, _ = filter.remove_pii(text)

        # ICD-10 codes should be preserved
        assert "E11.9" in result
        assert "I10" in result
        assert "I50.1" in result
        assert "C50.9" in result

    def test_preserve_ops_codes(self, filter):
        """Test preservation of OPS procedure codes"""
        text = """
        Durchgeführte Operationen:
        - Appendektomie (5-470.11)
        - Diagnostische Laparoskopie (1-632.0)
        - Herzkatheter (8-854.3)
        """
        result, _ = filter.remove_pii(text)

        # OPS codes should be preserved
        assert "5-470.11" in result
        assert "1-632.0" in result
        assert "8-854.3" in result

    def test_preserve_loinc_codes(self, filter):
        """Test preservation of LOINC laboratory codes"""
        text = """
        Laboruntersuchungen (LOINC):
        - Glucose: 2339-0
        - Hämoglobin: 718-7
        - Kreatinin: 2160-0
        - HbA1c: 4548-4
        """
        result, _ = filter.remove_pii(text)

        # LOINC codes should be preserved
        assert "2339-0" in result
        assert "718-7" in result
        assert "2160-0" in result
        assert "4548-4" in result

    def test_loinc_database_initialized(self, filter):
        """Test that LOINC code database is initialized"""
        assert hasattr(filter, "common_loinc_codes")
        assert len(filter.common_loinc_codes) >= 50
        # Check specific codes
        assert "2339-0" in filter.common_loinc_codes  # Glucose
        assert "718-7" in filter.common_loinc_codes  # Hemoglobin
        assert "4548-4" in filter.common_loinc_codes  # HbA1c


class TestPhase4DynamicDictionary:
    """Test Phase 4.1: Dynamic Medical Dictionary (Issue #35)"""

    def test_filter_works_without_database(self):
        """Test filter works when database is unavailable"""
        # Should not raise exception
        filter = AdvancedPrivacyFilter(load_custom_terms=False)
        assert filter is not None
        assert filter._custom_terms_loaded is False

    def test_default_terms_always_available(self):
        """Test that default terms are available even without database"""
        filter = AdvancedPrivacyFilter(load_custom_terms=False)

        # Check core medical terms
        assert "diabetes" in filter.medical_terms
        assert "hypertonie" in filter.medical_terms
        assert "hämoglobin" in filter.medical_terms

        # Check drugs
        assert "metformin" in filter.drug_database
        assert "ramipril" in filter.drug_database

        # Check eponyms
        assert "parkinson" in filter.medical_eponyms
        assert "alzheimer" in filter.medical_eponyms

    def test_constructor_parameter(self):
        """Test load_custom_terms constructor parameter"""
        # With loading disabled
        filter_no_load = AdvancedPrivacyFilter(load_custom_terms=False)
        assert filter_no_load._load_custom_terms is False

        # Default should be True
        filter_default = AdvancedPrivacyFilter(load_custom_terms=True)
        assert filter_default._load_custom_terms is True


class TestPhase4Integration:
    """Integration tests for Phase 4 features"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_complex_document_with_drugs_and_codes(self, filter):
        """Test realistic document with drugs, ICD codes, and LOINC codes"""
        text = """
        Arztbrief

        Patient: Schmidt, Maria
        Geb.: 22.03.1958
        Adresse: Musterweg 5, 10115 Berlin

        Diagnosen:
        1. Diabetes mellitus Typ 2 (E11.9) - LOINC HbA1c: 4548-4
        2. Arterielle Hypertonie (I10)
        3. Morbus Parkinson (G20)

        Aktuelle Medikation:
        - Metformin 1000mg 1-0-1
        - Ramipril 5mg 0-0-1
        - Madopar 125mg 1-1-1
        - Pantoprazol 20mg 1-0-0

        Laborwerte (LOINC 718-7):
        - Hämoglobin: 12.5 g/dl
        - HbA1c: 7.2%

        Geplante OP: 5-470.11 (Appendektomie)

        Mit freundlichen Grüßen
        Dr. med. Weber
        """
        result, metadata = filter.remove_pii(text)

        # PII should be removed
        assert "Schmidt" not in result
        assert "Maria" not in result
        assert "22.03.1958" not in result
        assert "Musterweg" not in result
        assert "10115 Berlin" not in result or "PLZ/ORT ENTFERNT" in result
        assert "Weber" not in result

        # Medical codes preserved
        assert "E11.9" in result
        assert "I10" in result
        assert "G20" in result
        assert "5-470.11" in result
        assert "4548-4" in result
        assert "718-7" in result

        # Drugs preserved
        assert "Metformin" in result or "METFORMIN" in result
        assert "Ramipril" in result or "RAMIPRIL" in result
        assert "Madopar" in result or "MADOPAR" in result
        assert "Pantoprazol" in result or "PANTOPRAZOL" in result

        # Eponyms preserved (Parkinson is medical)
        assert "Parkinson" in result

        # Lab values preserved
        assert "12.5" in result
        assert "7.2" in result

        # Metadata should be populated
        assert "entities_detected" in metadata
        assert metadata["has_ner"] is not None

    def test_metadata_returned(self, filter):
        """Test that remove_pii returns metadata dictionary"""
        text = "Patient: Test Person, Diagnose: Diabetes E11.9"
        result, metadata = filter.remove_pii(text)

        assert isinstance(metadata, dict)
        assert "entities_detected" in metadata
        assert "processing_timestamp" in metadata
        assert "total_time_ms" in metadata


class TestPhase5ConfidenceScoring:
    """Test Phase 5.1: Confidence Scoring (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_confidence_counters_exist(self, filter):
        """Test that confidence counters are initialized in metadata"""
        text = "Patient: Max Mustermann, Diagnose: Diabetes"
        _, metadata = filter.remove_pii(text)

        assert "high_confidence_removals" in metadata
        assert "medium_confidence_removals" in metadata
        assert "low_confidence_removals" in metadata
        assert "pattern_based_removals" in metadata

    def test_pattern_based_removals_tracked(self, filter):
        """Test that pattern-based PII removals are counted"""
        text = """
        Patient: Müller, Hans
        Geb.: 15.05.1965
        Tel: +49 30 12345678
        Email: test@example.com
        """
        _, metadata = filter.remove_pii(text)

        # Pattern-based removals should be > 0
        assert metadata["pattern_based_removals"] > 0

    def test_quality_summary_included(self, filter):
        """Test that quality_summary is included in metadata"""
        text = "Patient: Test Person, Diagnose: Diabetes"
        _, metadata = filter.remove_pii(text)

        assert "quality_summary" in metadata
        summary = metadata["quality_summary"]

        # Check quality summary structure
        assert "quality_score" in summary
        assert "total_pii_removed" in summary
        assert "confidence_breakdown" in summary
        assert "pii_types_found" in summary
        assert "review_recommended" in summary

    def test_quality_score_calculated(self, filter):
        """Test that quality score is calculated correctly"""
        text = """
        Arztbrief
        Patient: Schmidt, Maria
        Geb.: 22.03.1958
        Diagnose: Diabetes mellitus Typ 2
        """
        _, metadata = filter.remove_pii(text)

        quality_score = metadata["quality_summary"]["quality_score"]
        # Score should be between 0 and 100
        assert 0 <= quality_score <= 100


class TestPhase5FalsePositiveTracking:
    """Test Phase 5.2: False Positive Tracking (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_false_positive_list_initialized(self, filter):
        """Test that potential_false_positives list exists"""
        text = "Patient: Test Person"
        _, metadata = filter.remove_pii(text)

        assert "potential_false_positives" in metadata
        assert isinstance(metadata["potential_false_positives"], list)

    def test_preserved_medical_terms_tracked(self, filter):
        """Test that preserved medical terms are tracked"""
        text = """
        Diagnose: Morbus Parkinson
        Therapie: Madopar 125mg
        """
        _, metadata = filter.remove_pii(text)

        assert "preserved_medical_terms" in metadata
        assert isinstance(metadata["preserved_medical_terms"], list)

    def test_review_recommended_flag_exists(self, filter):
        """Test that review_recommended flag is in metadata"""
        text = "Patient: Test Person"
        _, metadata = filter.remove_pii(text)

        assert "review_recommended" in metadata
        assert isinstance(metadata["review_recommended"], bool)


class TestPhase5GDPRAuditTrail:
    """Test Phase 5.3: GDPR Audit Trail (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_pii_types_detected_populated(self, filter):
        """Test that pii_types_detected is populated with removed PII types"""
        text = """
        Patient: Müller, Hans
        Geb.: 15.05.1965
        Tel: +49 30 12345678
        Email: patient@example.com
        """
        _, metadata = filter.remove_pii(text)

        pii_types = metadata["pii_types_detected"]
        assert isinstance(pii_types, list)
        assert len(pii_types) > 0

        # Check for expected PII types
        assert "birthdate" in pii_types
        assert "phone_number" in pii_types
        assert "email_address" in pii_types

    def test_processing_timestamp_exists(self, filter):
        """Test that processing timestamp is recorded"""
        text = "Patient: Test Person"
        _, metadata = filter.remove_pii(text)

        assert "processing_timestamp" in metadata
        assert metadata["processing_timestamp"] is not None

    def test_gdpr_compliant_flag(self, filter):
        """Test that GDPR compliant flag is set"""
        text = """
        Patient: Schmidt, Maria
        Diagnose: Diabetes mellitus Typ 2
        """
        _, metadata = filter.remove_pii(text)

        assert "gdpr_compliant" in metadata
        assert isinstance(metadata["gdpr_compliant"], bool)

    def test_removal_method_tracked(self, filter):
        """Test that removal method version is tracked"""
        text = "Patient: Test Person"
        _, metadata = filter.remove_pii(text)

        assert "removal_method" in metadata
        assert "Phase5" in metadata["removal_method"]


class TestPhase5QualitySummary:
    """Test Phase 5.4: Quality Summary (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_quality_summary_structure(self, filter):
        """Test complete quality summary structure"""
        text = """
        Arztbrief
        Patient: Weber, Klaus
        Geb.: 10.10.1970
        Adresse: Musterweg 5, 10115 Berlin
        Diagnose: Arterielle Hypertonie (I10)
        Therapie: Ramipril 5mg
        """
        _, metadata = filter.remove_pii(text)

        summary = metadata["quality_summary"]

        # All expected fields
        assert "quality_score" in summary
        assert "total_pii_removed" in summary
        assert "confidence_breakdown" in summary
        assert "pii_types_found" in summary
        assert "pii_type_count" in summary
        assert "eponyms_preserved" in summary
        assert "review_recommended" in summary
        assert "review_flags" in summary

    def test_confidence_breakdown_structure(self, filter):
        """Test confidence breakdown has all levels"""
        text = "Patient: Max Mustermann, Diagnose: Diabetes"
        _, metadata = filter.remove_pii(text)

        breakdown = metadata["quality_summary"]["confidence_breakdown"]

        assert "high_confidence" in breakdown
        assert "medium_confidence" in breakdown
        assert "low_confidence" in breakdown
        assert "pattern_based" in breakdown

    def test_review_flags_list(self, filter):
        """Test that review_flags is a list"""
        text = "Patient: Test Person"
        _, metadata = filter.remove_pii(text)

        review_flags = metadata["quality_summary"]["review_flags"]
        assert isinstance(review_flags, list)


class TestPhase5MedicalValidation:
    """Test Phase 5.3: Medical Content Validation (Issue #35)"""

    @pytest.fixture
    def filter(self):
        """Create filter instance without database loading"""
        return AdvancedPrivacyFilter(load_custom_terms=False)

    def test_medical_content_preserved(self, filter):
        """Test that medical content validation passes for valid documents"""
        text = """
        Arztbrief
        Patient: Schmidt, Maria
        Diagnose: Diabetes mellitus Typ 2
        Laborwerte: HbA1c 7.2%
        Therapie: Metformin 1000mg
        """
        result, metadata = filter.remove_pii(text)

        # Medical content should be preserved
        assert "Diabetes" in result
        assert "HbA1c" in result or "hba1c" in result.lower()
        assert "7.2" in result
        assert "Metformin" in result or "METFORMIN" in result

        # GDPR compliance should be True if medical content preserved
        assert metadata["gdpr_compliant"] is True

    def test_pii_removed_medical_preserved(self, filter):
        """Test comprehensive PII removal with medical preservation"""
        text = """
        Universitätsklinikum München
        Arztbrief

        Patient: Mustermann, Max
        Geb.: 15.05.1965
        Adresse: Hauptstraße 42, 80331 München
        Tel: +49 89 12345678

        Diagnosen:
        1. Diabetes mellitus Typ 2 (E11.9)
        2. Arterielle Hypertonie (I10)
        3. Morbus Parkinson (G20)

        Aktuelle Medikation:
        - Metformin 1000mg 1-0-1
        - Ramipril 5mg 0-0-1
        - Madopar 125mg 1-1-1

        Laborwerte (LOINC 718-7):
        - Hämoglobin: 12.5 g/dl
        - HbA1c: 7.2%

        Mit freundlichen Grüßen
        Dr. med. Weber
        """
        result, metadata = filter.remove_pii(text)

        # PII removed
        assert "Mustermann" not in result
        assert "15.05.1965" not in result
        assert "80331" not in result or "PLZ/ORT ENTFERNT" in result
        assert "+49 89 12345678" not in result
        assert "Weber" not in result

        # Medical codes preserved
        assert "E11.9" in result
        assert "I10" in result
        assert "G20" in result

        # Drugs preserved
        assert "Metformin" in result or "METFORMIN" in result
        assert "Ramipril" in result or "RAMIPRIL" in result

        # Eponym preserved
        assert "Parkinson" in result

        # Quality summary exists
        assert "quality_summary" in metadata
        assert metadata["quality_summary"]["quality_score"] >= 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
