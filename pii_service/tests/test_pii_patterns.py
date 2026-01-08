"""
Unit tests for PII filter patterns.

Tests German and English PII detection patterns including:
- Doctor names with titles
- Patient names with honorifics
- Insurance numbers
- Case references
- Dates with month names
- Email domains
"""

import pytest
import re
from app.pii_filter import PIIFilter


@pytest.fixture(scope="module")
def pii_filter():
    """Create PII filter instance for testing."""
    return PIIFilter()


# =============================================================================
# GERMAN PATTERN TESTS
# =============================================================================

class TestGermanDoctorNames:
    """Tests for German doctor/professional title patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Basic doctor names
        ("Dr. Schmidt untersucht", "[DOCTOR_NAME]"),
        ("Dr. med. Schmidt untersucht", "[DOCTOR_NAME]"),
        ("Dr. med. habil. Schmidt", "[DOCTOR_NAME]"),
        ("Prof. Weber empfiehlt", "[DOCTOR_NAME]"),
        ("Prof. Dr. Weber empfiehlt", "[DOCTOR_NAME]"),
        ("Prof. Dr. med. Weber", "[DOCTOR_NAME]"),

        # Medical titles
        ("Oberarzt Müller berichtet", "[DOCTOR_NAME]"),
        ("OA Müller berichtet", "[DOCTOR_NAME]"),
        ("Oberärztin Schmidt", "[DOCTOR_NAME]"),
        ("Chefarzt Fischer", "[DOCTOR_NAME]"),
        ("CA Meier", "[DOCTOR_NAME]"),
        ("Facharzt Braun", "[DOCTOR_NAME]"),

        # Compound names
        ("Dr. med. Müller-Schmidt", "[DOCTOR_NAME]"),
        ("Prof. Dr. von Weizäcker", "[DOCTOR_NAME]"),

        # Academic titles
        ("Dipl.-Med. Schneider", "[DOCTOR_NAME]"),
        ("Dipl. Med. Bauer", "[DOCTOR_NAME]"),
    ])
    def test_doctor_names_detected(self, pii_filter, input_text, expected_contains):
        """Test that doctor names with titles are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanHonorifics:
    """Tests for German honorific patterns (Herr, Frau, etc.)."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Basic honorifics
        ("Herr Müller wurde untersucht", "[NAME]"),
        ("Frau Schmidt ist Patientin", "[NAME]"),
        ("Fräulein Weber", "[NAME]"),

        # Abbreviated forms
        ("Hr. Meier kommt", "[NAME]"),
        ("Fr. Fischer geht", "[NAME]"),

        # Compound names
        ("Herr Müller-Meier", "[NAME]"),
        ("Frau von Habsburg", "[NAME]"),
    ])
    def test_honorific_names_detected(self, pii_filter, input_text, expected_contains):
        """Test that honorific names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanPatientNames:
    """Tests for German patient name patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Comma format (Nachname, Vorname)
        ("Name: Müller, Anna", "[PATIENT_NAME]"),
        ("Patient: Schmidt, Hans", "[PATIENT_NAME]"),
        ("Versicherte: Weber, Maria", "[PATIENT_NAME]"),

        # Labeled names
        ("Patient: Hans Schmidt", "[PATIENT_NAME]"),
        ("Patientin: Maria Weber", "[PATIENT_NAME]"),
        ("Versicherter: Peter Müller", "[PATIENT_NAME]"),
        ("Auftraggeber: Franz Bauer", "[PATIENT_NAME]"),
        ("Einsender: Klaus Fischer", "[PATIENT_NAME]"),
    ])
    def test_patient_names_detected(self, pii_filter, input_text, expected_contains):
        """Test that patient names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanInsuranceNumbers:
    """Tests for German insurance number patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Standard formats
        ("Versichertennummer: 123456789", "[INSURANCE_ID]"),
        ("Versicherten-Nr.: A123456789", "[INSURANCE_ID]"),
        ("Vers.-Nr.: 123456789012", "[INSURANCE_ID]"),
        ("VN: 123456789", "[INSURANCE_ID]"),
        ("KK-Nr.: 123456789", "[INSURANCE_ID]"),
        ("Krankenkassennummer: 123456789", "[INSURANCE_ID]"),
        ("Mitgliedsnummer: 123456789", "[INSURANCE_ID]"),

        # With insurance company names
        ("AOK Nordost, Nr. 123456789", "[INSURANCE_ID]"),
        ("TK Versicherten-Nr: 123456789", "[INSURANCE_ID]"),
        ("Barmer 123456789", "[INSURANCE_ID]"),
        ("DAK Nummer: 123456789", "[INSURANCE_ID]"),
    ])
    def test_insurance_numbers_detected(self, pii_filter, input_text, expected_contains):
        """Test that insurance numbers are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanCaseReferences:
    """Tests for German case/file reference patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Case references
        ("Aktenzeichen: 2024/12345", "[REFERENCE_ID]"),
        ("Fall-Nr.: 2024/0815", "[REFERENCE_ID]"),
        ("Dossier 2024/12345", "[REFERENCE_ID]"),
        ("Az.: 2024/54321", "[REFERENCE_ID]"),

        # Document references
        ("Unser Zeichen: DS/2024/0815", "[REFERENCE_ID]"),
        ("Ihr Zeichen: AB/2024/1234", "[REFERENCE_ID]"),
        ("Ref.: XY/2023/9876", "[REFERENCE_ID]"),
    ])
    def test_case_references_detected(self, pii_filter, input_text, expected_contains):
        """Test that case references are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanDatesWithMonthNames:
    """Tests for German dates with month names."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        ("15. März 2024", "[DATE]"),
        ("3. Januar 2025", "[DATE]"),
        ("20. Dezember 2023", "[DATE]"),
        ("1. Februar 2024", "[DATE]"),
        ("31. Juli 2023", "[DATE]"),
        ("Datum: 15. Oktober 2024", "[DATE]"),
    ])
    def test_german_month_dates_detected(self, pii_filter, input_text, expected_contains):
        """Test that German dates with month names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanEmailDomains:
    """Tests for German email domain patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Named domains
        ("dr-schmidt.de", "[EMAIL_DOMAIN]"),
        ("praxis-mueller.de", "[EMAIL_DOMAIN]"),
        ("dr.weber-praxis.de", "[EMAIL_DOMAIN]"),
        ("schmidt-klinik.de", "[EMAIL_DOMAIN]"),

        # Full emails
        ("info@dr-schmidt.de", "[EMAIL]"),
        ("kontakt@praxis-mueller.de", "[EMAIL]"),
    ])
    def test_email_domains_detected(self, pii_filter, input_text, expected_contains):
        """Test that email domains are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanAddresses:
    """Tests for German address patterns including strasse/straße variants."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Standard straße spelling
        ("Hauptstraße 15", "[ADDRESS]"),
        ("Berliner Straße 42a", "[ADDRESS]"),
        ("Goethestraße 7", "[ADDRESS]"),

        # Double-s strasse spelling
        ("Schirmerstrasse 80", "[ADDRESS]"),
        ("Bahnhofstrasse 12", "[ADDRESS]"),
        ("Friedrichstrasse 100", "[ADDRESS]"),

        # Other street types
        ("Lindenweg 5", "[ADDRESS]"),
        ("Marktplatz 1", "[ADDRESS]"),
        ("Rathausplatz 3", "[ADDRESS]"),
        ("Parkring 22", "[ADDRESS]"),
        ("Hafendamm 8", "[ADDRESS]"),
    ])
    def test_addresses_detected(self, pii_filter, input_text, expected_contains):
        """Test that German addresses are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestGermanFaxNumbers:
    """Tests for German fax number patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Standard fax formats
        ("Fax: 030/12345678", "[FAX]"),
        ("Fax 0211 - 860 40 313", "[FAX]"),
        ("Telefax: 089-123456", "[FAX]"),
        ("Fax: +49 30 12345678", "[FAX]"),
    ])
    def test_fax_numbers_detected(self, pii_filter, input_text, expected_contains):
        """Test that fax numbers are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


# =============================================================================
# ENGLISH PATTERN TESTS
# =============================================================================

class TestEnglishDoctorNames:
    """Tests for English doctor/professional title patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        # Basic titles
        ("Dr. Smith examined", "[DOCTOR_NAME]"),
        ("Dr Smith examined", "[DOCTOR_NAME]"),
        ("Prof. Johnson recommends", "[DOCTOR_NAME]"),
        ("Professor Williams", "[DOCTOR_NAME]"),

        # Medical credentials
        ("MD Smith reviewed", "[DOCTOR_NAME]"),
        ("M.D. Johnson", "[DOCTOR_NAME]"),
        ("PhD Williams", "[DOCTOR_NAME]"),
        ("Ph.D. Brown", "[DOCTOR_NAME]"),

        # Nursing titles
        ("RN Thompson", "[DOCTOR_NAME]"),
        ("NP Davis", "[DOCTOR_NAME]"),
    ])
    def test_english_doctor_names_detected(self, pii_filter, input_text, expected_contains):
        """Test that English doctor names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="en")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestEnglishHonorifics:
    """Tests for English honorific patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        ("Mr. Smith was admitted", "[NAME]"),
        ("Mr Smith was admitted", "[NAME]"),
        ("Mrs. Johnson is patient", "[NAME]"),
        ("Ms. Williams", "[NAME]"),
        ("Miss Davis", "[NAME]"),
        ("Sir Thompson", "[NAME]"),
    ])
    def test_english_honorific_names_detected(self, pii_filter, input_text, expected_contains):
        """Test that English honorific names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="en")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestEnglishPatientNames:
    """Tests for English patient name patterns."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        ("Patient: John Smith", "[PATIENT_NAME]"),
        ("Name: Anna Mueller", "[PATIENT_NAME]"),
        ("First Name: John", "[PATIENT_NAME]"),
        ("Last Name: Smith", "[PATIENT_NAME]"),
        ("Surname: Williams", "[PATIENT_NAME]"),
        ("Insured: Peter Brown", "[PATIENT_NAME]"),
    ])
    def test_english_patient_names_detected(self, pii_filter, input_text, expected_contains):
        """Test that English patient names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="en")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


class TestEnglishDatesWithMonthNames:
    """Tests for English dates with month names."""

    @pytest.mark.parametrize("input_text,expected_contains", [
        ("March 15, 2024", "[DATE]"),
        ("15 March 2024", "[DATE]"),
        ("January 3, 2025", "[DATE]"),
        ("December 25, 2023", "[DATE]"),
        ("July 4, 2024", "[DATE]"),
    ])
    def test_english_month_dates_detected(self, pii_filter, input_text, expected_contains):
        """Test that English dates with month names are properly detected."""
        result, _ = pii_filter.remove_pii(input_text, language="en")
        assert expected_contains in result, f"Expected {expected_contains} in '{result}'"


# =============================================================================
# FALSE POSITIVE TESTS (Medical terms should NOT be replaced)
# =============================================================================

class TestMedicalTermsPreserved:
    """Tests that medical terms are NOT replaced."""

    @pytest.mark.parametrize("input_text", [
        # German medical terms
        "Hypertonie diagnostiziert",
        "Ramipril verschrieben",
        "EKG durchgeführt",
        "Herzinsuffizienz festgestellt",
        "Metformin eingestellt",

        # English medical terms
        "Hypertension diagnosed",
        "Metformin prescribed",
        "ECG performed",

        # Medical eponyms (disease names from people)
        "Morbus Parkinson",
        "Alzheimer Demenz",
        "Morbus Crohn",
        "Down-Syndrom",
    ])
    def test_medical_terms_not_replaced(self, pii_filter, input_text):
        """Test that medical terms are preserved."""
        result, _ = pii_filter.remove_pii(input_text, language="de")
        # Should NOT contain any placeholder
        assert "[" not in result or "[NAME]" not in result, f"Medical term incorrectly replaced in '{result}'"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestFullDocumentProcessing:
    """Tests for processing complete document fragments."""

    def test_german_medical_document(self, pii_filter):
        """Test processing a German medical document excerpt."""
        input_text = """
        Praxis Dr. med. Schmidt
        Hauptstraße 15, 12345 Berlin
        Tel: 030/12345678
        E-Mail: info@dr-schmidt.de

        Patient: Müller, Anna
        Geburtsdatum: 15.03.1965
        Versicherten-Nr.: 123456789
        Unser Zeichen: DS/2024/0815

        Sehr geehrte Frau Müller,

        der Befund vom 15. März 2024 zeigt eine arterielle Hypertonie.
        """

        result, metadata = pii_filter.remove_pii(input_text, language="de")

        # Check that PII is removed
        assert "[DOCTOR_NAME]" in result
        assert "[ADDRESS]" in result or "[PLZ_CITY]" in result
        assert "[PHONE]" in result
        assert "[EMAIL]" in result or "[EMAIL_DOMAIN]" in result
        assert "[PATIENT_NAME]" in result
        assert "[BIRTHDATE]" in result or "[DATE]" in result
        assert "[INSURANCE_ID]" in result
        assert "[REFERENCE_ID]" in result
        assert "[NAME]" in result  # For "Frau Müller"

        # Check that medical terms are preserved
        assert "Hypertonie" in result
        assert "Befund" in result

        # Check metadata
        assert metadata["entities_detected"] > 0

    def test_english_medical_document(self, pii_filter):
        """Test processing an English medical document excerpt."""
        input_text = """
        Dr. Smith Medical Practice
        123 Main Street
        Phone: 555-123-4567
        Email: contact@smith-clinic.com

        Patient: John Williams
        DOB: 03/15/1965
        SSN: 123-45-6789

        Dear Mr. Williams,

        The examination on March 15, 2024 shows hypertension.
        """

        result, metadata = pii_filter.remove_pii(input_text, language="en")

        # Check that PII is removed
        assert "[DOCTOR_NAME]" in result
        assert "[PATIENT_NAME]" in result
        assert "[NAME]" in result  # For "Mr. Williams"
        assert "[DATE]" in result or "[BIRTHDATE]" in result

        # Check that medical terms are preserved
        assert "hypertension" in result
        assert "examination" in result

        # Check metadata
        assert metadata["entities_detected"] > 0


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_text(self, pii_filter):
        """Test handling of empty text."""
        result, metadata = pii_filter.remove_pii("", language="de")
        assert result == ""
        assert metadata.get("error") == "Empty text"

    def test_whitespace_only(self, pii_filter):
        """Test handling of whitespace-only text."""
        result, metadata = pii_filter.remove_pii("   \n\t  ", language="de")
        assert metadata.get("error") == "Empty text"

    def test_no_pii(self, pii_filter):
        """Test text without any PII."""
        input_text = "Die Untersuchung ergab keine Auffälligkeiten."
        result, metadata = pii_filter.remove_pii(input_text, language="de")
        assert result == input_text
        assert metadata["entities_detected"] == 0

    def test_custom_protection_terms(self, pii_filter):
        """Test custom protection terms."""
        input_text = "Der Patient Spezialmedikament nimmt täglich."
        custom_terms = ["Spezialmedikament"]
        result, _ = pii_filter.remove_pii(
            input_text,
            language="de",
            custom_protection_terms=custom_terms
        )
        # Custom term should be preserved (not replaced)
        assert "Spezialmedikament" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
