"""
Unit tests for MedicalTermVerifier.

Tests the medical term verification that prevents false positive PII removal.
"""

import pytest
import sys
import os

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from medical_term_verifier import MedicalTermVerifier, MEDIALPY_AVAILABLE


class TestMedicalTermVerifier:
    """Test suite for MedicalTermVerifier."""

    @pytest.fixture
    def verifier(self):
        """Create a fresh verifier instance for each test."""
        v = MedicalTermVerifier()
        v.clear_cache()  # Ensure clean cache state
        return v

    # =========================================================================
    # German Temporal Terms (commonly misclassified as LOC)
    # =========================================================================

    def test_german_temporal_terms(self, verifier):
        """Test German temporal/frequency medical adjectives."""
        temporal_terms = [
            "Nachtliche",
            "nachtlichen",
            "Paroxysmal",
            "paroxysmale",
            "Intermittierend",
            "Persistierend",
            "Rezidivierend",
            "Progredient",
        ]

        for term in temporal_terms:
            is_medical, reason = verifier.is_medical_term(term)
            assert is_medical, f"'{term}' should be recognized as medical (got: {reason})"
            assert "german_temporal" in reason or "german_" in reason

    # =========================================================================
    # German Medical Suffixes
    # =========================================================================

    def test_german_medical_suffixes(self, verifier):
        """Test terms with German medical suffixes."""
        suffix_terms = [
            ("Kardiopulmonal", "pulmonal"),
            ("Kardiopulmonale", "pulmonale"),
            ("Hepatorenal", "renal"),
            ("Zerebral", "zerebral"),
            ("Intestinal", "intestinal"),
            ("Bronchitis", "itis"),
            ("Stenose", "stenose"),
            ("Insuffizienz", "insuffizienz"),
        ]

        for term, expected_suffix in suffix_terms:
            is_medical, reason = verifier.is_medical_term(term)
            assert is_medical, f"'{term}' should be recognized as medical (got: {reason})"

    # =========================================================================
    # ECG Compound Terms (commonly misclassified as ORG)
    # =========================================================================

    def test_ecg_compound_terms(self, verifier):
        """Test ECG/EKG compound terms that are often misclassified as ORG."""
        ecg_terms = [
            "ST-Strecke",
            "ST-Strecken-Veranderungen",
            "ST-Hebung",
            "ST-Senkung",
            "T-Welle",
            "P-Welle",
            "QRS-Komplex",
            "QT-Zeit",
            "PQ-Intervall",
        ]

        for term in ecg_terms:
            is_medical, reason = verifier.is_medical_term(term)
            assert is_medical, f"'{term}' should be recognized as medical (got: {reason})"
            assert "compound" in reason or "german_" in reason

    # =========================================================================
    # Medical Roots
    # =========================================================================

    def test_german_medical_roots(self, verifier):
        """Test terms containing German medical roots."""
        root_terms = [
            ("Kardiomyopathie", "kardio"),
            ("Pulmonologie", "pulmono"),
            ("Hepatomegalie", "hepato"),
            ("Nephrologie", "nephro"),
            ("Neurologie", "neuro"),
            ("Gastroenteritis", "gastro"),
            ("Dermatologie", "dermato"),
            ("Onkologie", "onko"),
            ("Hamatologie", "hamat"),
            ("Endokrinologie", "endo"),
        ]

        for term, expected_root in root_terms:
            is_medical, reason = verifier.is_medical_term(term)
            assert is_medical, f"'{term}' should be recognized as medical (got: {reason})"

    # =========================================================================
    # MEDIALpy Abbreviations (if available)
    # =========================================================================

    @pytest.mark.skipif(not MEDIALPY_AVAILABLE, reason="MEDIALpy not installed")
    def test_english_abbreviations(self, verifier):
        """Test English medical abbreviations via MEDIALpy."""
        abbreviations = [
            "NYHA",
            "BNP",
            "ECG",
            "MRI",
            "CT",
            "BMI",
            "CPR",
        ]

        for abbr in abbreviations:
            is_medical, reason = verifier.is_medical_term(abbr)
            assert is_medical, f"'{abbr}' should be recognized as medical (got: {reason})"
            assert "abbreviation" in reason

    # =========================================================================
    # Real Names (should NOT be preserved)
    # =========================================================================

    def test_real_names_not_preserved(self, verifier):
        """Test that real names are NOT identified as medical terms."""
        real_names = [
            "Muller",
            "Schmidt",
            "Meier",
            "Weber",
            "Fischer",
            "Wagner",
            "Becker",
            "Schulz",
            "Hans",
            "Maria",
            "Thomas",
            "Berlin",
            "Hamburg",
            "Munchen",
        ]

        for name in real_names:
            is_medical, reason = verifier.is_medical_term(name)
            assert not is_medical, f"'{name}' should NOT be recognized as medical (got: {reason})"

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_empty_and_short_terms(self, verifier):
        """Test handling of empty and very short terms."""
        assert verifier.is_medical_term("")[0] is False
        assert verifier.is_medical_term("a")[0] is False
        assert verifier.is_medical_term("ab")[0] is False

    def test_verify_before_removal_preserves_medical(self, verifier):
        """Test the convenience method for verification."""
        # Medical terms should return True (preserve)
        assert verifier.verify_before_removal("Kardiopulmonal", "PERSON") is True
        assert verifier.verify_before_removal("Nachtliche", "LOCATION") is True
        assert verifier.verify_before_removal("ST-Strecke", "ORGANIZATION") is True

        # Real names should return False (do not preserve)
        assert verifier.verify_before_removal("Muller", "PERSON") is False
        assert verifier.verify_before_removal("Berlin", "LOCATION") is False

    def test_cache_functionality(self, verifier):
        """Test that caching works correctly."""
        # First call
        result1 = verifier.is_medical_term("Kardiopulmonal")

        # Get cache stats
        stats = verifier.get_cache_stats()
        assert stats["misses"] >= 1

        # Second call (should hit cache)
        result2 = verifier.is_medical_term("Kardiopulmonal")

        # Results should be identical
        assert result1 == result2

        # Cache should have recorded a hit
        stats_after = verifier.get_cache_stats()
        assert stats_after["hits"] >= 1

    def test_cache_clear(self, verifier):
        """Test cache clearing."""
        # Populate cache
        verifier.is_medical_term("Kardiopulmonal")

        stats_before = verifier.get_cache_stats()
        assert stats_before["size"] >= 1

        # Clear cache
        verifier.clear_cache()

        stats_after = verifier.get_cache_stats()
        assert stats_after["size"] == 0

    # =========================================================================
    # Case Sensitivity
    # =========================================================================

    def test_case_insensitivity(self, verifier):
        """Test that verification is case-insensitive."""
        test_cases = [
            ("KARDIOPULMONAL", True),
            ("kardiopulmonal", True),
            ("Kardiopulmonal", True),
            ("NACHTLICHE", True),
            ("nachtliche", True),
            ("Nachtliche", True),
        ]

        for term, expected in test_cases:
            verifier.clear_cache()  # Clear cache between tests
            is_medical, reason = verifier.is_medical_term(term)
            assert is_medical == expected, f"'{term}' expected {expected}, got {is_medical} ({reason})"


class TestMedicalVerifierIntegration:
    """Integration tests that don't require MEDIALpy."""

    def test_verifier_initialization(self):
        """Test that verifier initializes without errors."""
        verifier = MedicalTermVerifier()
        assert verifier is not None
        assert hasattr(verifier, 'german_suffixes')
        assert hasattr(verifier, 'german_prefixes')
        assert hasattr(verifier, 'german_temporal_terms')
        assert hasattr(verifier, 'compound_regex')

    def test_specific_false_positive_cases(self):
        """Test specific cases that were causing false positives."""
        verifier = MedicalTermVerifier()

        # These specific terms were incorrectly being removed
        false_positive_cases = [
            ("Nachtliche", "LOCATION", True),       # "Nocturnal" - misclassified as location
            ("Kardiopulmonal", "NAME", True),       # "Cardiopulmonary" - misclassified as name
            ("ST-Strecken-Veranderungen", "ORGANIZATION", True),  # ECG term - misclassified as org
            ("Paroxysmal", "LOCATION", True),       # Medical frequency term
            ("Hepatorenal", "PERSON", True),        # Compound organ adjective
        ]

        for term, detected_as, should_preserve in false_positive_cases:
            verifier.clear_cache()
            result = verifier.verify_before_removal(term, detected_as)
            assert result == should_preserve, \
                f"'{term}' detected as {detected_as}: expected preserve={should_preserve}, got {result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
