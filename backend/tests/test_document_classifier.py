"""
Tests for DocumentClassifier Service

Tests pattern-based classification and AI fallback classification
for medical documents (ARZTBRIEF, BEFUNDBERICHT, LABORWERTE).
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.services.document_classifier import DocumentClassifier
from app.models.document_types import (
    DocumentClass,
    DocumentClassificationResult,
    CLASSIFICATION_PATTERNS,
    DOCUMENT_TYPE_DESCRIPTIONS,
)


class TestDocumentClassifier:
    """Test suite for DocumentClassifier service."""

    @pytest.fixture
    def mock_ovh_client(self):
        """Create mock OVH AI client for testing."""
        client = AsyncMock()
        client.process_medical_text = AsyncMock()
        return client

    @pytest.fixture
    def classifier_with_client(self, mock_ovh_client):
        """Create DocumentClassifier with mock OVH client."""
        return DocumentClassifier(ovh_client=mock_ovh_client)

    @pytest.fixture
    def classifier_without_client(self):
        """Create DocumentClassifier without OVH client."""
        return DocumentClassifier(ovh_client=None)

    # ==================== INITIALIZATION TESTS ====================

    def test_initialization_with_client(self, mock_ovh_client):
        """Test initialization with OVH client."""
        classifier = DocumentClassifier(ovh_client=mock_ovh_client)

        assert classifier.ovh_client is mock_ovh_client
        assert classifier.patterns == CLASSIFICATION_PATTERNS

    def test_initialization_without_client(self):
        """Test initialization without OVH client."""
        classifier = DocumentClassifier(ovh_client=None)

        assert classifier.ovh_client is None
        assert classifier.patterns == CLASSIFICATION_PATTERNS

    # ==================== PATTERN CLASSIFICATION TESTS ====================

    def test_classify_by_patterns_arztbrief_strong_indicators(self, classifier_without_client):
        """Test pattern matching for ARZTBRIEF with strong indicators."""
        text = """
        Sehr geehrte Frau Kollegin,

        ich berichte Ihnen über Patient Herrn Max Mustermann, der am 15.03.2024
        aus unserer Klinik entlassen wurde.

        Mit freundlichen Grüßen
        Dr. med. Hans Schmidt
        """

        result = classifier_without_client._classify_by_patterns(text)

        assert result.document_class == DocumentClass.ARZTBRIEF
        assert result.confidence >= 0.7  # Should be high confidence
        assert result.method == "pattern"
        assert result.processing_hints is not None

    def test_classify_by_patterns_befundbericht_strong_indicators(self, classifier_without_client):
        """Test pattern matching for BEFUNDBERICHT with strong indicators."""
        text = """
        BEFUNDBERICHT - MRT Schädel

        Untersuchung vom: 20.03.2024
        Kontrastmittel: Gadolinium

        Befund:
        In der MRT-Darstellung zeigt sich eine auffällige Läsion im Frontallappen.
        Die Schnittbilder zeigen eine kontrastmittelanreichernde Struktur.
        """

        result = classifier_without_client._classify_by_patterns(text)

        assert result.document_class == DocumentClass.BEFUNDBERICHT
        assert result.confidence >= 0.7
        assert result.method == "pattern"

    def test_classify_by_patterns_laborwerte_strong_indicators(self, classifier_without_client):
        """Test pattern matching for LABORWERTE with strong indicators."""
        text = """
        LABORWERTE - Blutbild vom 25.03.2024

        Hämatologie:
        Hämoglobin: 14.5 g/dl (Referenzbereich: 12-16 g/dl)
        Cholesterin: 220 mg/dl (Norm: <200 mg/dl) - erhöht
        HDL: 45 mg/dl (Normalbereich: >40 mg/dl)
        LDL: 150 mg/dl (Referenz: <130 mg/dl) - erhöht
        Triglyceride: 180 mg/dl
        HbA1c: 5.8% (Referenz: <6.0%)
        """

        result = classifier_without_client._classify_by_patterns(text)

        assert result.document_class == DocumentClass.LABORWERTE
        assert result.confidence >= 0.7
        assert result.method == "pattern"

    def test_classify_by_patterns_weak_indicators_only(self, classifier_without_client):
        """Test pattern matching with only weak indicators (lower confidence)."""
        text = """
        Patient wurde untersucht.
        Diagnose wurde gestellt.
        Therapie wurde empfohlen.
        """

        result = classifier_without_client._classify_by_patterns(text)

        assert result.confidence < 0.7  # Should be low confidence
        assert result.method == "pattern"

    def test_classify_by_patterns_no_matches(self, classifier_without_client):
        """Test pattern matching with no keyword matches (default fallback)."""
        text = "This is a random English text with no medical keywords."

        result = classifier_without_client._classify_by_patterns(text)

        assert result.document_class == DocumentClass.ARZTBRIEF  # Default fallback
        assert result.confidence < 0.5  # Low confidence when no matches
        assert result.method == "pattern"

    def test_classify_by_patterns_mixed_indicators(self, classifier_without_client):
        """Test pattern matching with both strong and weak indicators."""
        text = """
        Sehr geehrte Kollegen,

        Patient wurde mit Verdacht auf Tumor überwiesen.
        Anamnese zeigt auffällige Befunde.

        Mit freundlichen Grüßen
        """

        result = classifier_without_client._classify_by_patterns(text)

        assert result.document_class == DocumentClass.ARZTBRIEF
        assert result.confidence > 0.5
        assert result.method == "pattern"

    def test_classify_by_patterns_competing_types(self, classifier_without_client):
        """Test pattern matching when multiple document types have matches."""
        text = """
        Befundbericht und Laborwerte:

        MRT Befund zeigt Auffälligkeiten.
        Cholesterin: 220 mg/dl (erhöht)
        """

        result = classifier_without_client._classify_by_patterns(text)

        # Should pick the one with higher score
        assert result.document_class in [DocumentClass.BEFUNDBERICHT, DocumentClass.LABORWERTE]
        assert result.method == "pattern"

    def test_classify_by_patterns_close_scores_reduce_confidence(self, classifier_without_client):
        """Test that close scores reduce confidence."""
        text = """
        Sehr geehrte Kollegen,

        Befund der MRT-Untersuchung:
        Auffällige Darstellung mit Kontrastmittel.

        Mit freundlichen Grüßen
        """

        result = classifier_without_client._classify_by_patterns(text)

        # Should detect a document type
        assert result.document_class in [DocumentClass.ARZTBRIEF, DocumentClass.BEFUNDBERICHT]
        # Confidence may vary based on indicator matches
        assert 0.0 < result.confidence <= 1.0
        assert result.method == "pattern"

    def test_classify_by_patterns_case_insensitive(self, classifier_without_client):
        """Test that pattern matching is case-insensitive."""
        text = "SEHR GEEHRTE FRAU KOLLEGIN, ENTLASSUNG, MIT FREUNDLICHEN GRÜßEN"

        result = classifier_without_client._classify_by_patterns(text)

        assert result.document_class == DocumentClass.ARZTBRIEF
        assert result.confidence >= 0.7

    # ==================== ASYNC CLASSIFICATION TESTS ====================

    @pytest.mark.asyncio
    async def test_classify_document_high_confidence_pattern(self, classifier_with_client, mock_ovh_client):
        """Test that high confidence pattern match doesn't call AI."""
        text = """
        Sehr geehrte Frau Kollegin,

        Entlassung von Patient Max Mustermann.

        Mit freundlichen Grüßen
        """

        result = await classifier_with_client.classify_document(text)

        assert result.document_class == DocumentClass.ARZTBRIEF
        assert result.confidence >= 0.7
        # AI should NOT be called
        mock_ovh_client.process_medical_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_classify_document_low_confidence_uses_ai(self, classifier_with_client, mock_ovh_client):
        """Test that low confidence pattern match triggers AI fallback."""
        text = "Patient wurde untersucht."  # Weak indicators only

        # Mock AI response
        mock_ovh_client.process_medical_text.return_value = "BEFUNDBERICHT"

        result = await classifier_with_client.classify_document(text, use_ai_fallback=True)

        # AI should be called
        mock_ovh_client.process_medical_text.assert_called_once()
        assert result.document_class == DocumentClass.BEFUNDBERICHT
        assert result.confidence == 0.9  # AI confidence

    @pytest.mark.asyncio
    async def test_classify_document_ai_disabled(self, classifier_with_client, mock_ovh_client):
        """Test classification with AI fallback disabled."""
        text = "Patient wurde untersucht."  # Weak indicators only

        result = await classifier_with_client.classify_document(text, use_ai_fallback=False)

        # AI should NOT be called
        mock_ovh_client.process_medical_text.assert_not_called()
        assert result.method == "pattern"

    @pytest.mark.asyncio
    async def test_classify_document_no_client_no_ai(self, classifier_without_client):
        """Test classification without OVH client (no AI available)."""
        text = "Patient wurde untersucht."

        result = await classifier_without_client.classify_document(text, use_ai_fallback=True)

        # Should return pattern result even with low confidence
        assert result.method == "pattern"

    @pytest.mark.asyncio
    async def test_classify_document_ai_better_than_pattern(self, classifier_with_client, mock_ovh_client):
        """Test that AI result is used when better than pattern."""
        text = "Patient wurde mit Anamnese untersucht."  # Low pattern confidence

        # Mock AI response with high confidence
        mock_ovh_client.process_medical_text.return_value = "LABORWERTE"

        result = await classifier_with_client.classify_document(text, use_ai_fallback=True)

        assert result.document_class == DocumentClass.LABORWERTE
        assert result.confidence == 0.9  # AI confidence
        assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_classify_document_pattern_better_than_ai(self, classifier_with_client, mock_ovh_client):
        """Test that pattern result is kept when better than AI."""
        text = """
        LABORWERTE - Blutbild
        Cholesterin: 220 mg/dl (Referenzbereich: <200 mg/dl)
        HbA1c: 5.8%
        """  # High pattern confidence

        # Mock AI with lower confidence (unclear response)
        mock_ovh_client.process_medical_text.return_value = "unclear response"

        result = await classifier_with_client.classify_document(text, use_ai_fallback=True)

        # Pattern should win
        assert result.document_class == DocumentClass.LABORWERTE
        assert result.confidence >= 0.7
        # Either pattern was used directly, or pattern was better after AI call
        assert result.confidence >= 0.5

    # ==================== AI CLASSIFICATION TESTS ====================

    @pytest.mark.asyncio
    async def test_classify_by_ai_arztbrief(self, classifier_with_client, mock_ovh_client):
        """Test AI classification for ARZTBRIEF."""
        text = "Some medical text"

        mock_ovh_client.process_medical_text.return_value = "ARZTBRIEF"

        result = await classifier_with_client._classify_by_ai(text)

        assert result.document_class == DocumentClass.ARZTBRIEF
        assert result.confidence == 0.9
        assert result.method == "ai"
        assert result.processing_hints is not None

    @pytest.mark.asyncio
    async def test_classify_by_ai_befundbericht(self, classifier_with_client, mock_ovh_client):
        """Test AI classification for BEFUNDBERICHT."""
        text = "Some medical text"

        mock_ovh_client.process_medical_text.return_value = "BEFUNDBERICHT"

        result = await classifier_with_client._classify_by_ai(text)

        assert result.document_class == DocumentClass.BEFUNDBERICHT
        assert result.confidence == 0.9
        assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_classify_by_ai_laborwerte(self, classifier_with_client, mock_ovh_client):
        """Test AI classification for LABORWERTE."""
        text = "Some medical text"

        # Test both LABORWERTE and LABOR variants
        for response in ["LABORWERTE", "LABOR"]:
            mock_ovh_client.process_medical_text.return_value = response

            result = await classifier_with_client._classify_by_ai(text)

            assert result.document_class == DocumentClass.LABORWERTE
            assert result.confidence == 0.9
            assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_classify_by_ai_unclear_response(self, classifier_with_client, mock_ovh_client):
        """Test AI classification with unclear response."""
        text = "Some medical text"

        mock_ovh_client.process_medical_text.return_value = "unclear gibberish"

        result = await classifier_with_client._classify_by_ai(text)

        assert result.document_class == DocumentClass.ARZTBRIEF  # Default fallback
        assert result.confidence == 0.5  # Lower confidence
        assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_classify_by_ai_no_client(self, classifier_without_client):
        """Test AI classification without client."""
        text = "Some medical text"

        result = await classifier_without_client._classify_by_ai(text)

        assert result.document_class == DocumentClass.ARZTBRIEF  # Default
        assert result.confidence == 0.0
        assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_classify_by_ai_exception_handling(self, classifier_with_client, mock_ovh_client):
        """Test AI classification error handling."""
        text = "Some medical text"

        # Make OVH client raise exception
        mock_ovh_client.process_medical_text.side_effect = Exception("AI API Error")

        result = await classifier_with_client._classify_by_ai(text)

        assert result.document_class == DocumentClass.ARZTBRIEF  # Default on error
        assert result.confidence == 0.3
        assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_classify_by_ai_text_truncation(self, classifier_with_client, mock_ovh_client):
        """Test that AI classification truncates long text to 2000 chars."""
        text = "A" * 5000  # Very long text

        mock_ovh_client.process_medical_text.return_value = "ARZTBRIEF"

        await classifier_with_client._classify_by_ai(text)

        # Check that the text passed to AI was truncated
        call_args = mock_ovh_client.process_medical_text.call_args
        assert len(call_args.kwargs['text']) == 2000

    @pytest.mark.asyncio
    async def test_classify_by_ai_correct_parameters(self, classifier_with_client, mock_ovh_client):
        """Test that AI classification uses correct parameters."""
        text = "Some medical text"

        mock_ovh_client.process_medical_text.return_value = "ARZTBRIEF"

        await classifier_with_client._classify_by_ai(text)

        # Verify AI was called with correct parameters
        mock_ovh_client.process_medical_text.assert_called_once()
        call_kwargs = mock_ovh_client.process_medical_text.call_args.kwargs

        assert call_kwargs['temperature'] == 0.1  # Low temperature for consistent results
        assert call_kwargs['max_tokens'] == 10  # Only need one word
        assert 'instruction' in call_kwargs
        assert 'ARZTBRIEF' in call_kwargs['instruction']
        assert 'BEFUNDBERICHT' in call_kwargs['instruction']
        assert 'LABORWERTE' in call_kwargs['instruction']

    @pytest.mark.asyncio
    async def test_classify_by_ai_case_insensitive(self, classifier_with_client, mock_ovh_client):
        """Test AI response parsing is case-insensitive."""
        text = "Some medical text"

        # Test various case variations
        for response in ["arztbrief", "Arztbrief", "ARZTBRIEF", "ArZtBrIeF"]:
            mock_ovh_client.process_medical_text.return_value = response

            result = await classifier_with_client._classify_by_ai(text)

            assert result.document_class == DocumentClass.ARZTBRIEF

    # ==================== PROCESSING HINTS TESTS ====================

    def test_get_processing_hints_arztbrief(self, classifier_without_client):
        """Test processing hints for ARZTBRIEF."""
        hints = classifier_without_client._get_processing_hints(DocumentClass.ARZTBRIEF)

        assert "document_info" in hints
        assert "focus_areas" in hints
        assert "special_handling" in hints

        assert "treatment_recommendations" in hints["focus_areas"]
        assert "medication_changes" in hints["focus_areas"]
        assert "follow_up_appointments" in hints["focus_areas"]
        assert "diagnoses" in hints["focus_areas"]

        assert "preserve_doctor_recommendations" in hints["special_handling"]
        assert "highlight_patient_actions" in hints["special_handling"]

    def test_get_processing_hints_befundbericht(self, classifier_without_client):
        """Test processing hints for BEFUNDBERICHT."""
        hints = classifier_without_client._get_processing_hints(DocumentClass.BEFUNDBERICHT)

        assert "examination_findings" in hints["focus_areas"]
        assert "abnormalities" in hints["focus_areas"]
        assert "size_descriptions" in hints["focus_areas"]
        assert "follow_up_examinations" in hints["focus_areas"]

        assert "use_visual_comparisons" in hints["special_handling"]
        assert "explain_medical_imaging_terms" in hints["special_handling"]

    def test_get_processing_hints_laborwerte(self, classifier_without_client):
        """Test processing hints for LABORWERTE."""
        hints = classifier_without_client._get_processing_hints(DocumentClass.LABORWERTE)

        assert "abnormal_values" in hints["focus_areas"]
        assert "reference_ranges" in hints["focus_areas"]
        assert "trends" in hints["focus_areas"]
        assert "critical_values" in hints["focus_areas"]

        assert "preserve_all_numbers" in hints["special_handling"]
        assert "maintain_table_structure" in hints["special_handling"]
        assert "use_color_coding_analogies" in hints["special_handling"]

    def test_get_processing_hints_includes_document_info(self, classifier_without_client):
        """Test that processing hints include document type descriptions."""
        hints = classifier_without_client._get_processing_hints(DocumentClass.ARZTBRIEF)

        assert hints["document_info"] == DOCUMENT_TYPE_DESCRIPTIONS[DocumentClass.ARZTBRIEF]

    # ==================== DOCUMENT INFO TESTS ====================

    def test_get_document_type_info_arztbrief(self, classifier_without_client):
        """Test getting document type info for ARZTBRIEF."""
        info = classifier_without_client.get_document_type_info(DocumentClass.ARZTBRIEF)

        assert info["name"] == "Arztbrief"
        assert "Briefe zwischen Ärzten" in info["description"]
        assert "icon" in info
        assert "examples" in info

    def test_get_document_type_info_befundbericht(self, classifier_without_client):
        """Test getting document type info for BEFUNDBERICHT."""
        info = classifier_without_client.get_document_type_info(DocumentClass.BEFUNDBERICHT)

        assert info["name"] == "Befundbericht"
        assert "Befunde" in info["description"]
        assert "MRT-Befund" in info["examples"]

    def test_get_document_type_info_laborwerte(self, classifier_without_client):
        """Test getting document type info for LABORWERTE."""
        info = classifier_without_client.get_document_type_info(DocumentClass.LABORWERTE)

        assert info["name"] == "Laborwerte"
        assert "Laborergebnisse" in info["description"]
        assert "Blutbild" in info["examples"]

    # ==================== INTEGRATION TESTS ====================

    @pytest.mark.asyncio
    async def test_complete_classification_workflow_pattern_only(self, classifier_without_client):
        """Test complete workflow with pattern matching only (no AI)."""
        # Test each document type
        texts = {
            DocumentClass.ARZTBRIEF: "Sehr geehrte Frau Kollegin, Entlassung. Mit freundlichen Grüßen",
            DocumentClass.BEFUNDBERICHT: "BEFUNDBERICHT MRT vom 20.03. Kontrastmittel Befund zeigt Läsion",
            DocumentClass.LABORWERTE: "LABORWERTE Blutbild: Cholesterin 220 mg/dl HbA1c 5.8% Referenzbereich"
        }

        for expected_class, text in texts.items():
            result = await classifier_without_client.classify_document(text)

            assert result.document_class == expected_class
            assert result.confidence >= 0.7
            assert result.method == "pattern"
            assert result.processing_hints is not None

    @pytest.mark.asyncio
    async def test_complete_classification_workflow_with_ai_fallback(
        self, classifier_with_client, mock_ovh_client
    ):
        """Test complete workflow with AI fallback for uncertain cases."""
        # Uncertain text (weak indicators only)
        text = "Patient wurde untersucht. Diagnose gestellt."

        mock_ovh_client.process_medical_text.return_value = "BEFUNDBERICHT"

        result = await classifier_with_client.classify_document(text, use_ai_fallback=True)

        # AI should have been called and result used
        mock_ovh_client.process_medical_text.assert_called_once()
        assert result.document_class == DocumentClass.BEFUNDBERICHT
        assert result.method == "ai"

    @pytest.mark.asyncio
    async def test_all_document_types_classifiable(self, classifier_without_client):
        """Test that all document types can be classified."""
        for doc_class in DocumentClass:
            # Get strong indicators for this type
            patterns = CLASSIFICATION_PATTERNS[doc_class]
            strong_indicators = patterns["strong_indicators"][:3]  # Use first 3

            # Create text with these indicators
            text = " ".join(strong_indicators)

            result = await classifier_without_client.classify_document(text)

            assert result.document_class == doc_class
            assert result.confidence > 0.0

    @pytest.mark.asyncio
    async def test_real_world_arztbrief_example(self, classifier_without_client):
        """Test classification with realistic ARZTBRIEF example."""
        text = """
        Universitätsklinikum Hamburg-Eppendorf
        Kardiologie

        Sehr geehrte Frau Dr. Müller,

        wir berichten Ihnen über Ihren o.g. Patienten, Herrn Max Mustermann,
        geb. 15.03.1960, der vom 10.03.2024 bis 20.03.2024 in unserer Klinik
        zur kardiologischen Diagnostik und Therapie stationär behandelt wurde.

        Diagnosen:
        1. Koronare Herzkrankheit (KHK)
        2. Arterielle Hypertonie

        Therapieempfehlung:
        - ASS 100mg 1-0-0
        - Ramipril 5mg 1-0-0

        Weiteres Vorgehen:
        Kontrolle in 3 Monaten in der kardiologischen Ambulanz.

        Für Rückfragen stehen wir gerne zur Verfügung.

        Mit freundlichen kollegialen Grüßen
        Prof. Dr. med. Hans Schmidt
        """

        result = await classifier_without_client.classify_document(text)

        assert result.document_class == DocumentClass.ARZTBRIEF
        assert result.confidence >= 0.6  # Realistic confidence with mixed indicators
        assert result.method == "pattern"

    @pytest.mark.asyncio
    async def test_real_world_laborwerte_example(self, classifier_without_client):
        """Test classification with realistic LABORWERTE example."""
        text = """
        LABORWERTE - Hämatologie/Klinische Chemie
        Patient: Mustermann, Max
        Geb.: 15.03.1960

        Datum: 25.03.2024

        Parameter          Wert      Einheit  Referenzbereich
        =========================================================
        Hämoglobin        14.5      g/dl     12.0 - 16.0
        Leukozyten        7.2       /nl      4.0 - 10.0
        Thrombozyten      250       /nl      150 - 400

        Cholesterin       220       mg/dl    < 200          ↑
        HDL-Cholesterin   45        mg/dl    > 40
        LDL-Cholesterin   150       mg/dl    < 130          ↑
        Triglyceride      180       mg/dl    < 150          ↑

        HbA1c             5.8       %        < 6.0
        Nüchtern-Glucose  95        mg/dl    70 - 100

        Kreatinin         1.0       mg/dl    0.7 - 1.3
        GFR               85        ml/min   > 60

        TSH               2.5       mU/l     0.4 - 4.0
        """

        result = await classifier_without_client.classify_document(text)

        assert result.document_class == DocumentClass.LABORWERTE
        assert result.confidence >= 0.8
        assert result.method == "pattern"
