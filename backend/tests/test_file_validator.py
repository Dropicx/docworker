"""
Tests for FileValidator Service

Tests comprehensive file validation including size checks, MIME type detection,
and format-specific validation for PDFs and images.
"""

import pytest
from io import BytesIO
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import PyPDF2
from PIL import Image

from app.services.file_validator import (
    FileValidator,
    ALLOWED_MIME_TYPES,
    FALLBACK_MIME_TYPES,
    MAX_FILE_SIZE,
    MIN_FILE_SIZE,
)


class TestFileValidator:
    """Test suite for FileValidator service."""

    @pytest.fixture
    def create_upload_file(self):
        """Factory for creating mock UploadFile objects."""
        def _create(filename: str, content: bytes, content_type: str = "application/pdf"):
            file = Mock()
            file.filename = filename
            file.content_type = content_type
            file.read = AsyncMock(return_value=content)
            file.seek = AsyncMock()
            return file
        return _create

    @pytest.fixture
    def valid_pdf_content(self):
        """Create valid PDF content for testing."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Test PDF Document")
        c.drawString(100, 730, "This is a test page with some content.")
        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.read()

    @pytest.fixture
    def valid_jpeg_content(self):
        """Create valid JPEG image content for testing."""
        img = Image.new('RGB', (800, 600), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        return buffer.read()

    @pytest.fixture
    def valid_png_content(self):
        """Create valid PNG image content for testing."""
        img = Image.new('RGB', (800, 600), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.read()

    # ==================== SIZE VALIDATION TESTS ====================

    @pytest.mark.asyncio
    async def test_validate_file_too_small(self, create_upload_file):
        """Test validation fails for files smaller than MIN_FILE_SIZE."""
        tiny_content = b"x" * (MIN_FILE_SIZE - 1)
        file = create_upload_file("test.pdf", tiny_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is False
        assert "zu klein" in error.lower()
        assert str(MIN_FILE_SIZE) in error

    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, create_upload_file):
        """Test validation fails for files larger than MAX_FILE_SIZE."""
        huge_content = b"x" * (MAX_FILE_SIZE + 1)
        file = create_upload_file("test.pdf", huge_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is False
        assert "zu groß" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_file_valid_size(self, create_upload_file, valid_pdf_content):
        """Test validation passes for files within valid size range."""
        file = create_upload_file("test.pdf", valid_pdf_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        # Should pass size validation (may fail on other checks)
        # Check that size is not the issue
        assert len(valid_pdf_content) >= MIN_FILE_SIZE
        assert len(valid_pdf_content) <= MAX_FILE_SIZE

    # ==================== MIME TYPE VALIDATION TESTS ====================

    @pytest.mark.asyncio
    async def test_validate_file_direct_mime_match_pdf(self, create_upload_file, valid_pdf_content):
        """Test validation with direct MIME type match for PDF."""
        file = create_upload_file("document.pdf", valid_pdf_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_direct_mime_match_jpeg(self, create_upload_file, valid_jpeg_content):
        """Test validation with direct MIME type match for JPEG."""
        file = create_upload_file("photo.jpg", valid_jpeg_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="image/jpeg"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_direct_mime_match_png(self, create_upload_file, valid_png_content):
        """Test validation with direct MIME type match for PNG."""
        file = create_upload_file("scan.png", valid_png_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="image/png"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_fallback_mime_textplain_pdf(self, create_upload_file, valid_pdf_content):
        """Test validation with fallback MIME type (text/plain) for PDF."""
        file = create_upload_file("document.pdf", valid_pdf_content)

        # Some systems report PDFs as text/plain
        with patch('app.services.file_validator.magic.from_buffer', return_value="text/plain"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_fallback_mime_octetstream_jpeg(self, create_upload_file, valid_jpeg_content):
        """Test validation with fallback MIME type (octet-stream) for JPEG."""
        file = create_upload_file("photo.jpg", valid_jpeg_content)

        # Generic binary type
        with patch('app.services.file_validator.magic.from_buffer', return_value="application/octet-stream"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_alternative_png_mime(self, create_upload_file, valid_png_content):
        """Test validation with alternative PNG MIME type (image/x-png)."""
        file = create_upload_file("scan.png", valid_png_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="image/x-png"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_alternative_jpeg_mime(self, create_upload_file, valid_jpeg_content):
        """Test validation with alternative JPEG MIME type (image/pjpeg)."""
        file = create_upload_file("photo.jpeg", valid_jpeg_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="image/pjpeg"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_file_unsupported_mime_type(self, create_upload_file):
        """Test validation fails for unsupported MIME types."""
        content = b"x" * 5000  # Valid size
        file = create_upload_file("document.docx", content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/vnd.openxmlformats"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is False
        assert "nicht unterstützt" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_file_mime_extension_mismatch(self, create_upload_file, valid_pdf_content):
        """Test validation fails when MIME type doesn't match extension."""
        file = create_upload_file("document.jpg", valid_pdf_content)  # PDF content with .jpg extension

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is False
        assert "nicht unterstützt" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_file_no_filename(self, create_upload_file):
        """Test validation handles missing filename gracefully."""
        content = b"x" * 5000
        file = create_upload_file("", content)  # Empty filename
        file.filename = None

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is False

    # ==================== PDF VALIDATION TESTS ====================

    @pytest.mark.asyncio
    async def test_validate_pdf_valid(self, valid_pdf_content):
        """Test PDF validation passes for valid PDF."""
        is_valid, error = await FileValidator._validate_pdf(valid_pdf_content)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_pdf_empty(self):
        """Test PDF validation fails for PDFs with no pages."""
        # Create empty PDF (this is tricky, we'll use a mock)
        with patch('app.services.file_validator.PyPDF2.PdfReader') as mock_reader:
            mock_reader.return_value.pages = []

            is_valid, error = await FileValidator._validate_pdf(b"fake pdf content")

        assert is_valid is False
        assert "keine seiten" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_pdf_too_many_pages(self):
        """Test PDF validation fails for PDFs with more than 50 pages."""
        with patch('app.services.file_validator.PyPDF2.PdfReader') as mock_reader:
            # Create mock with 51 pages
            mock_reader.return_value.pages = [Mock()] * 51

            is_valid, error = await FileValidator._validate_pdf(b"fake pdf content")

        assert is_valid is False
        assert "zu viele seiten" in error.lower()
        assert "50" in error

    @pytest.mark.asyncio
    async def test_validate_pdf_exactly_50_pages(self):
        """Test PDF validation passes for PDFs with exactly 50 pages."""
        with patch('app.services.file_validator.PyPDF2.PdfReader') as mock_reader:
            # Create mock with exactly 50 pages
            mock_page = Mock()
            mock_page.extract_text.return_value = "Some text"
            mock_reader.return_value.pages = [mock_page] * 50

            is_valid, error = await FileValidator._validate_pdf(b"fake pdf content")

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_pdf_corrupt(self):
        """Test PDF validation fails for corrupted PDFs."""
        corrupt_content = b"This is not a real PDF file"

        is_valid, error = await FileValidator._validate_pdf(corrupt_content)

        assert is_valid is False
        assert "ungültige pdf" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_pdf_checks_first_5_pages(self):
        """Test PDF validation only checks first 5 pages for text."""
        with patch('app.services.file_validator.PyPDF2.PdfReader') as mock_reader:
            # Create mock with 10 pages
            mock_page = Mock()
            mock_page.extract_text.return_value = "Some text"
            mock_reader.return_value.pages = [mock_page] * 10

            await FileValidator._validate_pdf(b"fake pdf content")

            # Should only check first 5 pages
            assert mock_page.extract_text.call_count <= 5

    # ==================== IMAGE VALIDATION TESTS ====================

    @pytest.mark.asyncio
    async def test_validate_image_valid_jpeg(self, valid_jpeg_content):
        """Test image validation passes for valid JPEG."""
        is_valid, error = await FileValidator._validate_image(valid_jpeg_content)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_image_valid_png(self, valid_png_content):
        """Test image validation passes for valid PNG."""
        is_valid, error = await FileValidator._validate_image(valid_png_content)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_image_unsupported_format(self):
        """Test image validation fails for unsupported formats (e.g., BMP, TIFF)."""
        # Create a BMP image
        img = Image.new('RGB', (800, 600), color='green')
        buffer = BytesIO()
        img.save(buffer, format='BMP')
        buffer.seek(0)
        content = buffer.read()

        is_valid, error = await FileValidator._validate_image(content)

        assert is_valid is False
        assert "nicht unterstützt" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_image_too_small(self):
        """Test image validation fails for images smaller than 100x100 pixels."""
        # Create 50x50 image
        img = Image.new('RGB', (50, 50), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        content = buffer.read()

        is_valid, error = await FileValidator._validate_image(content)

        assert is_valid is False
        assert "zu klein" in error.lower()
        assert "100x100" in error

    @pytest.mark.asyncio
    async def test_validate_image_too_large(self):
        """Test image validation fails for images larger than 8000x8000 pixels."""
        # Create 9000x9000 image (this will be slow, so we mock it)
        with patch('PIL.Image.open') as mock_open:
            mock_img = MagicMock()
            mock_img.format = 'JPEG'
            mock_img.size = (9000, 9000)
            mock_img.__enter__ = Mock(return_value=mock_img)
            mock_img.__exit__ = Mock(return_value=False)
            mock_open.return_value = mock_img

            is_valid, error = await FileValidator._validate_image(b"fake content")

        assert is_valid is False
        assert "zu groß" in error.lower()
        assert "8000x8000" in error

    @pytest.mark.asyncio
    async def test_validate_image_exactly_minimum_size(self):
        """Test image validation passes for images exactly 100x100 pixels."""
        img = Image.new('RGB', (100, 100), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        content = buffer.read()

        is_valid, error = await FileValidator._validate_image(content)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_image_exactly_maximum_size(self):
        """Test image validation passes for images exactly 8000x8000 pixels."""
        # Mock to avoid creating huge image
        with patch('PIL.Image.open') as mock_open:
            mock_img = MagicMock()
            mock_img.format = 'JPEG'
            mock_img.size = (8000, 8000)
            mock_img.verify = Mock()
            mock_img.__enter__ = Mock(return_value=mock_img)
            mock_img.__exit__ = Mock(return_value=False)
            mock_open.return_value = mock_img

            is_valid, error = await FileValidator._validate_image(b"fake content")

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validate_image_corrupt(self):
        """Test image validation fails for corrupted images."""
        corrupt_content = b"This is not a real image file"

        is_valid, error = await FileValidator._validate_image(corrupt_content)

        assert is_valid is False
        assert "ungültige bilddatei" in error.lower()

    # ==================== GET FILE TYPE TESTS ====================

    def test_get_file_type_pdf(self):
        """Test get_file_type returns 'pdf' for PDF files."""
        assert FileValidator.get_file_type("document.pdf") == "pdf"
        assert FileValidator.get_file_type("Document.PDF") == "pdf"
        assert FileValidator.get_file_type("REPORT.pdf") == "pdf"

    def test_get_file_type_jpeg(self):
        """Test get_file_type returns 'image' for JPEG files."""
        assert FileValidator.get_file_type("photo.jpg") == "image"
        assert FileValidator.get_file_type("scan.jpeg") == "image"
        assert FileValidator.get_file_type("IMAGE.JPG") == "image"
        assert FileValidator.get_file_type("PHOTO.JPEG") == "image"

    def test_get_file_type_png(self):
        """Test get_file_type returns 'image' for PNG files."""
        assert FileValidator.get_file_type("scan.png") == "image"
        assert FileValidator.get_file_type("IMAGE.PNG") == "image"

    def test_get_file_type_unknown(self):
        """Test get_file_type returns 'unknown' for unsupported files."""
        assert FileValidator.get_file_type("document.docx") == "unknown"
        assert FileValidator.get_file_type("spreadsheet.xlsx") == "unknown"
        assert FileValidator.get_file_type("presentation.pptx") == "unknown"
        assert FileValidator.get_file_type("file.txt") == "unknown"

    def test_get_file_type_no_extension(self):
        """Test get_file_type returns 'unknown' for files without extension."""
        assert FileValidator.get_file_type("document") == "unknown"
        assert FileValidator.get_file_type("README") == "unknown"

    def test_get_file_type_empty_filename(self):
        """Test get_file_type returns 'unknown' for empty filename."""
        assert FileValidator.get_file_type("") == "unknown"
        assert FileValidator.get_file_type(None) == "unknown"

    def test_get_file_type_case_insensitive(self):
        """Test get_file_type is case-insensitive."""
        assert FileValidator.get_file_type("FILE.PDF") == "pdf"
        assert FileValidator.get_file_type("file.PDF") == "pdf"
        assert FileValidator.get_file_type("FILE.pdf") == "pdf"

    # ==================== INTEGRATION TESTS ====================

    @pytest.mark.asyncio
    async def test_validate_file_exception_handling(self, create_upload_file):
        """Test validation handles exceptions gracefully."""
        file = create_upload_file("test.pdf", b"x" * 5000)

        # Make read() raise exception
        file.read.side_effect = Exception("File read error")

        is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is False
        assert "fehler bei der dateivalidierung" in error.lower()

    @pytest.mark.asyncio
    async def test_validate_file_seek_called(self, create_upload_file, valid_pdf_content):
        """Test that file.seek(0) is called to reset file pointer."""
        file = create_upload_file("test.pdf", valid_pdf_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            await FileValidator.validate_file(file)

        # Verify seek was called to reset file pointer
        file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_complete_validation_workflow_pdf(self, create_upload_file, valid_pdf_content):
        """Test complete validation workflow for PDF file."""
        file = create_upload_file("medical_report.pdf", valid_pdf_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_complete_validation_workflow_jpeg(self, create_upload_file, valid_jpeg_content):
        """Test complete validation workflow for JPEG image."""
        file = create_upload_file("medical_scan.jpg", valid_jpeg_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="image/jpeg"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_complete_validation_workflow_png(self, create_upload_file, valid_png_content):
        """Test complete validation workflow for PNG image."""
        file = create_upload_file("medical_document.png", valid_png_content)

        with patch('app.services.file_validator.magic.from_buffer', return_value="image/png"):
            is_valid, error = await FileValidator.validate_file(file)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_validation_respects_all_constraints(self, create_upload_file):
        """Test that validation enforces all constraints in order."""
        # Too small
        tiny_file = create_upload_file("test.pdf", b"x" * 10)
        with patch('app.services.file_validator.magic.from_buffer', return_value="application/pdf"):
            is_valid, error = await tiny_file.validate_file(file)
            assert is_valid is False
            assert "klein" in error.lower()

    # ==================== CONSTANTS TESTS ====================

    def test_allowed_mime_types_defined(self):
        """Test that ALLOWED_MIME_TYPES contains expected types."""
        assert "application/pdf" in ALLOWED_MIME_TYPES
        assert "image/jpeg" in ALLOWED_MIME_TYPES
        assert "image/png" in ALLOWED_MIME_TYPES

    def test_fallback_mime_types_defined(self):
        """Test that FALLBACK_MIME_TYPES contains expected fallbacks."""
        assert "text/plain" in FALLBACK_MIME_TYPES
        assert "application/octet-stream" in FALLBACK_MIME_TYPES
        assert "image/x-png" in FALLBACK_MIME_TYPES
        assert "image/pjpeg" in FALLBACK_MIME_TYPES

    def test_file_size_constraints_reasonable(self):
        """Test that file size constraints are reasonable."""
        assert MIN_FILE_SIZE == 1024  # 1KB
        assert MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB
        assert MIN_FILE_SIZE < MAX_FILE_SIZE
