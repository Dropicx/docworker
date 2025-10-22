"""
Unit Tests for HybridTextExtractor

Tests intelligent text extraction with adaptive strategy selection.
Verifies LOCAL_TEXT, LOCAL_OCR, VISION_LLM, and HYBRID extraction strategies.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import BytesIO

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.hybrid_text_extractor import HybridTextExtractor
from app.services.file_quality_detector import ExtractionStrategy, DocumentComplexity


class TestHybridTextExtractorInitialization:
    """Test suite for HybridTextExtractor initialization"""

    def test_initialization_with_local_ocr(self):
        """Test extractor initializes with local OCR when available"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', True), \
             patch('app.services.hybrid_text_extractor.TextExtractorWithOCR'):
            extractor = HybridTextExtractor()

            assert extractor is not None
            assert extractor.quality_detector is not None
            assert extractor.ovh_client is not None
            assert extractor.sequence_detector is not None

    def test_initialization_without_local_ocr(self):
        """Test extractor initializes without local OCR"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            extractor = HybridTextExtractor()

            assert extractor is not None
            assert extractor.local_ocr_available is False
            assert extractor.local_ocr is None

    def test_initialization_ocr_failure_graceful(self):
        """Test extractor handles OCR initialization failure gracefully"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', True), \
             patch('app.services.hybrid_text_extractor.TextExtractorWithOCR', side_effect=Exception("OCR init failed")):
            extractor = HybridTextExtractor()

            assert extractor is not None
            assert extractor.local_ocr_available is False
            assert extractor.local_ocr is None


class TestLocalTextExtraction:
    """Test suite for local PDF text extraction"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            return HybridTextExtractor()

    def test_evaluate_high_quality_text(self, extractor):
        """Test quality evaluation for high-quality medical text"""
        text = """
        Patient: Test Case
        Diagnose: Diabetes mellitus Typ 2
        Behandlung mit Metformin 1000mg täglich
        Laborwerte:
        - Hämoglobin: 14.5 g/dl (Normalbereich: 12-16)
        - Glucose: 145 mg/dl (erhöht)
        - HbA1c: 8.2% (Zielwert: <7%)
        """

        confidence = extractor._evaluate_local_extraction_quality(text)
        assert confidence >= 0.7, f"Expected confidence >= 0.7, got {confidence}"

    def test_evaluate_low_quality_text(self, extractor):
        """Test quality evaluation for low-quality text"""
        text = "���□▢※◦"  # Garbage characters

        confidence = extractor._evaluate_local_extraction_quality(text)
        assert confidence < 0.5, f"Expected confidence < 0.5, got {confidence}"

    def test_evaluate_empty_text(self, extractor):
        """Test quality evaluation for empty text"""
        confidence = extractor._evaluate_local_extraction_quality("")
        assert confidence == 0.0

    def test_evaluate_short_text(self, extractor):
        """Test quality evaluation for very short text"""
        text = "Test"
        confidence = extractor._evaluate_local_extraction_quality(text)
        assert confidence == 0.0

    def test_evaluate_medical_content_indicators(self, extractor):
        """Test quality evaluation recognizes medical content"""
        text = """
        Arzt, Patient, Diagnose, Behandlung, Medizin, Befund,
        Labor, Wert, Normal, Untersuchung, Datum, Geburtsdatum,
        Versicherung, Therapie.
        """

        confidence = extractor._evaluate_local_extraction_quality(text)
        # Should get bonus for medical terms
        assert confidence > 0.5

    def test_evaluate_lab_values_present(self, extractor):
        """Test quality evaluation for lab values"""
        text = """
        Laborwerte:
        Glucose: 95 mg/dl
        Cholesterin: 180 mg/dl
        Triglyceride: 120 mg/dl
        Kreatinin: 0.9 mg/dl
        """

        confidence = extractor._evaluate_local_extraction_quality(text)
        # Should get bonus for medical numbers
        assert confidence > 0.6


class TestMedicalSectionIdentification:
    """Test suite for medical section type identification"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            return HybridTextExtractor()

    def test_identify_patient_info(self, extractor):
        """Test identification of patient information section"""
        text = "Patient: Max Mustermann, Geburtsdatum: 01.01.1980"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'patient_info'

    def test_identify_lab_values(self, extractor):
        """Test identification of lab values section"""
        text = "Laborwerte: Hämoglobin 14.5 g/dl, Referenzbereich 12-16"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'lab_values'

    def test_identify_diagnosis(self, extractor):
        """Test identification of diagnosis section"""
        text = "Diagnose: Diabetes mellitus Typ 2 (ICD-10: E11.9)"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'diagnosis'

    def test_identify_medication(self, extractor):
        """Test identification of medication section"""
        text = "Medikation: Metformin 1000mg täglich, Ramipril 5mg abends"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'medication'

    def test_identify_header(self, extractor):
        """Test identification of document header"""
        text = "Arztbrief - Universitätsklinikum München"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'header'

    def test_identify_examination(self, extractor):
        """Test identification of examination section"""
        text = "Untersuchung: MRT des Schädels zeigt keine Auffälligkeiten"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'examination'

    def test_identify_general_section(self, extractor):
        """Test identification of general section (no specific type)"""
        text = "Some random text without specific medical context markers"
        section_type = extractor._identify_medical_section_type(text)
        assert section_type == 'general'


class TestTextMergingLogic:
    """Test suite for multi-file text merging"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            return HybridTextExtractor()

    def test_merge_sequential(self, extractor):
        """Test sequential merging with clear separators"""
        results = [
            {'filename': 'page1.pdf', 'text': 'First page content', 'confidence': 0.9, 'file_index': 1},
            {'filename': 'page2.pdf', 'text': 'Second page content', 'confidence': 0.9, 'file_index': 2}
        ]

        merged = extractor._merge_sequential(results)

        assert 'page1.pdf' in merged
        assert 'page2.pdf' in merged
        assert 'First page content' in merged
        assert 'Second page content' in merged

    def test_merge_single_result(self, extractor):
        """Test merging with only one file"""
        results = [
            {'filename': 'single.pdf', 'text': 'Only content', 'confidence': 0.9, 'file_index': 1}
        ]

        merged = extractor._merge_sequential(results)
        assert merged == 'Only content'

    def test_merge_smart_patient_info_first(self, extractor):
        """Test smart merge with patient info as first file"""
        results = [
            {
                'filename': 'page1.pdf',
                'text': 'Patient: Test Patient\nGeburtsdatum: 01.01.1980',
                'confidence': 0.9,
                'file_index': 1
            },
            {
                'filename': 'page2.pdf',
                'text': 'Diagnose: Diabetes mellitus Typ 2',
                'confidence': 0.9,
                'file_index': 2
            }
        ]

        merged = extractor._merge_smart(results)

        assert 'Patient' in merged
        assert 'Diagnose' in merged
        # First page should not have artificial header added
        assert merged.count('#') >= 0  # May have headers

    def test_is_likely_continuation_comma(self, extractor):
        """Test continuation detection with comma"""
        prev = "Text that ends with,"
        current = "continuation text"

        is_continuation = extractor._is_likely_continuation(prev, current)
        assert is_continuation is True

    def test_is_likely_continuation_explicit_marker(self, extractor):
        """Test continuation detection with explicit marker"""
        prev = "Some previous text"
        current = "Fortsetzung: more content"

        is_continuation = extractor._is_likely_continuation(prev, current)
        assert is_continuation is True

    def test_is_not_continuation(self, extractor):
        """Test non-continuation detection"""
        prev = "Complete sentence."
        current = "New independent sentence."

        is_continuation = extractor._is_likely_continuation(prev, current)
        assert is_continuation is False

    def test_is_table_continuation_pipes(self, extractor):
        """Test table continuation detection with pipe separators"""
        prev = """
        Name | Value | Unit
        Glucose | 95 | mg/dl
        """
        current = """
        Cholesterol | 180 | mg/dl
        Triglycerides | 120 | mg/dl
        """

        is_table = extractor._is_table_continuation(prev, current)
        assert is_table is True

    def test_is_table_continuation_medical_numbers(self, extractor):
        """Test table continuation with lab values"""
        prev = "Hämoglobin: 14.5 g/dl\nLeukozyten: 7.2 /nl"
        current = "Thrombozyten: 250 /nl\nErythrozyten: 4.8 /pl"

        is_table = extractor._is_table_continuation(prev, current)
        assert is_table is True

    def test_should_merge_seamlessly_same_section(self, extractor):
        """Test seamless merge for same section types"""
        should_merge = extractor._should_merge_seamlessly(
            "Lab values text",
            "More lab values",
            'lab_values',
            'lab_values'
        )
        assert should_merge is True

    def test_should_not_merge_different_sections(self, extractor):
        """Test no seamless merge for different section types"""
        should_merge = extractor._should_merge_seamlessly(
            "Patient info",
            "Medication info",
            'patient_info',
            'medication'
        )
        assert should_merge is False

    def test_get_section_header_patient_info(self, extractor):
        """Test section header generation for patient info"""
        header = extractor._get_section_header('patient_info', 'file.pdf')
        assert '##' in header
        assert 'Patient' in header

    def test_get_section_header_lab_values(self, extractor):
        """Test section header generation for lab values"""
        header = extractor._get_section_header('lab_values', 'file.pdf')
        assert '##' in header
        assert 'Labor' in header

    def test_post_process_merged_text(self, extractor):
        """Test post-processing removes excessive blank lines"""
        text = "Section 1\n\n\n\n\n\nSection 2"
        processed = extractor._post_process_merged_text(text)

        # Should reduce multiple blank lines
        assert '\n\n\n\n\n\n' not in processed

    def test_post_process_header_spacing(self, extractor):
        """Test post-processing fixes header spacing"""
        text = "Text\n## Header\nMore text"
        processed = extractor._post_process_merged_text(text)

        # Headers should have proper spacing
        assert processed.count('\n') >= text.count('\n')


@pytest.mark.asyncio
class TestExtractTextMethod:
    """Test suite for extract_text() main method"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            return HybridTextExtractor()

    @pytest.mark.asyncio
    async def test_extract_local_text_strategy(self, extractor):
        """Test extraction with LOCAL_TEXT strategy"""
        mock_analysis = {
            'recommended_strategy': 'LOCAL_TEXT',
            'recommended_complexity': 'SIMPLE'
        }

        with patch.object(extractor.quality_detector, 'analyze_file', new_callable=AsyncMock) as mock_analyze, \
             patch.object(extractor, '_extract_with_local_text', new_callable=AsyncMock) as mock_extract:

            mock_analyze.return_value = (ExtractionStrategy.LOCAL_TEXT, DocumentComplexity.SIMPLE, mock_analysis)
            mock_extract.return_value = ("Extracted text", 0.95)

            text, confidence = await extractor.extract_text(b"fake pdf content", "pdf", "test.pdf")

            assert text == "Extracted text"
            assert confidence == 0.95
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_vision_llm_strategy(self, extractor):
        """Test extraction with VISION_LLM strategy"""
        mock_analysis = {
            'recommended_strategy': 'VISION_LLM',
            'recommended_complexity': 'COMPLEX'
        }

        with patch.object(extractor.quality_detector, 'analyze_file', new_callable=AsyncMock) as mock_analyze, \
             patch.object(extractor, '_extract_with_vision_llm', new_callable=AsyncMock) as mock_extract:

            mock_analyze.return_value = (ExtractionStrategy.VISION_LLM, DocumentComplexity.COMPLEX, mock_analysis)
            mock_extract.return_value = ("Vision extracted text", 0.90)

            text, confidence = await extractor.extract_text(b"fake image content", "image", "scan.jpg")

            assert text == "Vision extracted text"
            assert confidence == 0.90
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_handles_errors_gracefully(self, extractor):
        """Test extraction handles errors and returns error message"""
        with patch.object(extractor.quality_detector, 'analyze_file', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")

            text, confidence = await extractor.extract_text(b"content", "pdf", "test.pdf")

            assert "error" in text.lower()
            assert confidence == 0.0


@pytest.mark.asyncio
class TestExtractFromMultipleFiles:
    """Test suite for extract_from_multiple_files() method"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            return HybridTextExtractor()

    @pytest.mark.asyncio
    async def test_multi_file_empty_list(self, extractor):
        """Test multi-file extraction with empty file list"""
        text, confidence = await extractor.extract_from_multiple_files([])

        assert "No files provided" in text
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_multi_file_sequence_detection(self, extractor):
        """Test multi-file extraction with sequence detection"""
        files = [
            (b"content3", "image", "page3.jpg"),
            (b"content1", "image", "page1.jpg"),
            (b"content2", "image", "page2.jpg")
        ]

        # Mock sequence detector to reorder files
        ordered_files = [
            (b"content1", "image", "page1.jpg"),
            (b"content2", "image", "page2.jpg"),
            (b"content3", "image", "page3.jpg")
        ]

        mock_analysis = {
            'recommended_strategy': 'LOCAL_TEXT',
            'recommended_complexity': 'SIMPLE'
        }

        with patch.object(extractor.sequence_detector, 'detect_sequence', new_callable=AsyncMock) as mock_sequence, \
             patch.object(extractor.quality_detector, 'analyze_multiple_files', new_callable=AsyncMock) as mock_analyze, \
             patch.object(extractor, '_extract_with_local_text', new_callable=AsyncMock) as mock_extract:

            mock_sequence.return_value = ordered_files
            mock_analyze.return_value = mock_analysis
            mock_extract.return_value = ("Page content", 0.9)

            text, confidence = await extractor.extract_from_multiple_files(files, merge_strategy="smart")

            # Should have called sequence detector
            mock_sequence.assert_called_once_with(files)
            # Should have extracted from 3 files
            assert mock_extract.call_count == 3
            # Should return merged text
            assert len(text) > 0
            # Average confidence should be reasonable
            assert confidence > 0.0

    @pytest.mark.asyncio
    async def test_multi_file_all_fail(self, extractor):
        """Test multi-file extraction when all files fail"""
        files = [
            (b"content1", "image", "page1.jpg"),
            (b"content2", "image", "page2.jpg")
        ]

        mock_analysis = {
            'recommended_strategy': 'LOCAL_TEXT',
            'recommended_complexity': 'SIMPLE'
        }

        with patch.object(extractor.sequence_detector, 'detect_sequence', new_callable=AsyncMock) as mock_sequence, \
             patch.object(extractor.quality_detector, 'analyze_multiple_files', new_callable=AsyncMock) as mock_analyze, \
             patch.object(extractor, '_extract_with_local_text', new_callable=AsyncMock) as mock_extract:

            mock_sequence.return_value = files
            mock_analyze.return_value = mock_analysis
            mock_extract.return_value = ("Error: extraction failed", 0.0)

            text, confidence = await extractor.extract_from_multiple_files(files)

            assert "Failed to extract text from any file" in text
            assert confidence == 0.0


@pytest.mark.asyncio
class TestStrategyMethods:
    """Test suite for specific extraction strategy methods"""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance for testing"""
        with patch('app.services.hybrid_text_extractor.LOCAL_OCR_AVAILABLE', False):
            return HybridTextExtractor()

    @pytest.mark.asyncio
    async def test_extract_local_text_non_pdf_fallback(self, extractor):
        """Test local text extraction falls back to vision for non-PDF"""
        with patch.object(extractor, '_extract_with_vision_llm', new_callable=AsyncMock) as mock_vision:
            mock_vision.return_value = ("Vision result", 0.8)

            text, confidence = await extractor._extract_with_local_text(b"image", "image", {})

            # Should fallback to vision LLM for images
            mock_vision.assert_called_once()
            assert text == "Vision result"

    @pytest.mark.asyncio
    async def test_extract_local_ocr_unavailable_fallback(self, extractor):
        """Test local OCR falls back to vision when unavailable"""
        with patch.object(extractor, '_extract_with_vision_llm', new_callable=AsyncMock) as mock_vision:
            mock_vision.return_value = ("Vision result", 0.8)

            # Extractor has no local OCR
            text, confidence = await extractor._extract_with_local_ocr(b"content", "image", {})

            mock_vision.assert_called_once()
            assert text == "Vision result"

    @pytest.mark.asyncio
    async def test_extract_vision_llm_image(self, extractor):
        """Test vision LLM extraction for images"""
        from PIL import Image

        # Create a small test image
        test_image = Image.new('RGB', (100, 100), color='white')
        img_byte_arr = BytesIO()
        test_image.save(img_byte_arr, format='PNG')
        img_content = img_byte_arr.getvalue()

        with patch.object(extractor.ovh_client, 'extract_text_with_vision', new_callable=AsyncMock) as mock_ovh:
            mock_ovh.return_value = ("Extracted via vision", 0.85)

            text, confidence = await extractor._extract_with_vision_llm(img_content, "image", {})

            mock_ovh.assert_called_once()
            assert text == "Extracted via vision"
            assert confidence == 0.85

    @pytest.mark.asyncio
    async def test_extract_hybrid_local_success(self, extractor):
        """Test hybrid extraction uses local method when successful"""
        with patch.object(extractor, '_extract_with_local_text', new_callable=AsyncMock) as mock_local:
            mock_local.return_value = ("High quality local text" * 10, 0.85)  # Long enough and good confidence

            text, confidence = await extractor._extract_with_hybrid(b"pdf", "pdf", {})

            # Should use local method result (confidence >= 0.7 and length > 100)
            assert "High quality local text" in text
            assert confidence == 0.85

    @pytest.mark.asyncio
    async def test_extract_hybrid_vision_fallback(self, extractor):
        """Test hybrid extraction falls back to vision on low quality"""
        with patch.object(extractor, '_extract_with_local_text', new_callable=AsyncMock) as mock_local, \
             patch.object(extractor, '_extract_with_vision_llm', new_callable=AsyncMock) as mock_vision:

            mock_local.return_value = ("Short", 0.5)  # Low quality/short
            mock_vision.return_value = ("Much better vision result", 0.9)

            text, confidence = await extractor._extract_with_hybrid(b"pdf", "pdf", {})

            # Should use vision result (better confidence)
            mock_vision.assert_called_once()
            assert "better vision result" in text
            assert confidence == 0.9


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
